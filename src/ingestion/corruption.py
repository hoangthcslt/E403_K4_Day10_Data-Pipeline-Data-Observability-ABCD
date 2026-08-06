from __future__ import annotations

from datetime import timedelta

import pandas as pd

from core.utils import now_utc, write_json

_NOISE_SNIPPET = "[noise:9f3a][garbled-ocr-fragment][noise:9f3a]"
_STALE_YEARS = 3


def _rebuild_text_for_embedding(title: str, authors_joined: str, categories_joined: str, summary: str) -> str:
    parts = [
        f"Title: {title}",
        f"Authors: {authors_joined}" if authors_joined else "",
        f"Categories: {categories_joined}" if categories_joined else "",
        f"Summary: {summary}",
    ]
    return "\n".join(part for part in parts if part)


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhieu dang data corruption tren cleaned dataframe va ghi corruption log."""
    total = len(df)
    if total == 0:
        write_json(
            output_log_path,
            {"generated_at": now_utc().isoformat(), "original_rows": 0, "corrupted_rows": 0, "actions": []},
        )
        return df.copy()

    # `df` da duoc cleaning.build_clean_dataframe sort giam dan theo `published`, va
    # evaluation.testset.build_test_set lay cau hoi tu dung phan dau (cac paper moi nhat) cua
    # cung dataframe nay. Corruption phai nham vao vung dau do de tac dong len duoc retrieval/
    # answer metrics, khong chi len data quality checks.
    zone_size = min(total, max(4, round(total * 0.5)))
    zone = df.iloc[:zone_size].reset_index(drop=True)
    rest = df.iloc[zone_size:].reset_index(drop=True)

    n_drop = max(1, round(zone_size * 0.15))
    n_blank = max(1, round(zone_size * 0.20))
    n_noise = max(1, round(zone_size * 0.20))
    n_truncate = max(1, round(zone_size * 0.20))
    n_stale = max(1, round(zone_size * 0.20))

    offset = 0

    def _slice(n: int) -> pd.DataFrame:
        nonlocal offset
        start = offset
        end = min(offset + n, zone_size)
        offset = end
        return zone.iloc[start:end].copy()

    dropped = _slice(n_drop)
    blanked = _slice(n_blank)
    noised = _slice(n_noise)
    truncated = _slice(n_truncate)
    staled = _slice(n_stale)
    untouched_zone = zone.iloc[offset:].copy()

    # 1) Drop mot so latest records: gion gian bi loai khoi corrupted_zone o duoi.

    # 2) Blank summary.
    blanked["summary"] = ""
    blanked["summary_chars"] = 0
    blanked["text_for_embedding"] = blanked.apply(
        lambda row: _rebuild_text_for_embedding(row["title"], row["authors_joined"], row["categories_joined"], ""),
        axis=1,
    )

    # 3) Inject noise vao summary.
    noised["summary"] = noised["summary"].apply(lambda text: f"{_NOISE_SNIPPET} {text} {_NOISE_SNIPPET}")
    noised["summary_chars"] = noised["summary"].str.len()
    noised["text_for_embedding"] = noised.apply(
        lambda row: _rebuild_text_for_embedding(
            row["title"], row["authors_joined"], row["categories_joined"], row["summary"]
        ),
        axis=1,
    )

    # 4) Truncate title (pha vo exact-title lookup dung trong retrieval/qa.py).
    truncated["title"] = truncated["title"].apply(lambda title: " ".join(title.split(" ")[:2]))
    truncated["text_for_embedding"] = truncated.apply(
        lambda row: _rebuild_text_for_embedding(
            row["title"], row["authors_joined"], row["categories_joined"], row["summary"]
        ),
        axis=1,
    )

    # 5) Lam stale publication date (vuot nguong freshness).
    stale_date = (now_utc() - timedelta(days=365 * _STALE_YEARS)).date()
    staled["published"] = stale_date.isoformat()

    corrupted_zone = pd.concat([blanked, noised, truncated, staled, untouched_zone], ignore_index=True)
    combined = pd.concat([corrupted_zone, rest], ignore_index=True)

    # 6) Add duplicate rows: nhan ban tu cac dong con nguyen ven (uu tien ngoai vung da corrupt).
    n_duplicate = max(1, round(total * 0.08))
    duplicate_source_pool = rest if len(rest) > 0 else combined
    duplicate_source = duplicate_source_pool.head(min(n_duplicate, len(duplicate_source_pool))).copy()
    combined = pd.concat([combined, duplicate_source], ignore_index=True)

    # 7) age_days phai duoc tinh lai theo thoi diem corrupt (khac thoi diem baseline chay).
    run_date = now_utc().date()
    combined["age_days"] = combined["published"].apply(
        lambda value: max((run_date - pd.Timestamp(value).date()).days, 0)
    )
    combined = combined.sort_values("published", ascending=False).reset_index(drop=True)

    # 8) Ghi corruption log.
    actions = [
        {
            "type": "drop_latest_records",
            "description": "Remove the most recently published records entirely from the corpus.",
            "count": int(len(dropped)),
            "affected_paper_ids": dropped["paper_id"].tolist(),
        },
        {
            "type": "blank_summary",
            "description": "Blank out the summary field.",
            "count": int(len(blanked)),
            "affected_paper_ids": blanked["paper_id"].tolist(),
        },
        {
            "type": "inject_noise",
            "description": "Inject garbage text into the summary field.",
            "count": int(len(noised)),
            "affected_paper_ids": noised["paper_id"].tolist(),
        },
        {
            "type": "truncate_title",
            "description": "Truncate the title to its first two words, breaking exact-title lookup.",
            "count": int(len(truncated)),
            "affected_paper_ids": truncated["paper_id"].tolist(),
        },
        {
            "type": "stale_publication_date",
            "description": f"Set published date to {stale_date.isoformat()}, beyond the freshness threshold.",
            "count": int(len(staled)),
            "affected_paper_ids": staled["paper_id"].tolist(),
        },
        {
            "type": "duplicate_rows",
            "description": "Append exact duplicate rows for existing records.",
            "count": int(len(duplicate_source)),
            "affected_paper_ids": duplicate_source["paper_id"].tolist(),
        },
    ]
    write_json(
        output_log_path,
        {
            "generated_at": now_utc().isoformat(),
            "original_rows": total,
            "corrupted_rows": len(combined),
            "actions": actions,
        },
    )

    return combined
