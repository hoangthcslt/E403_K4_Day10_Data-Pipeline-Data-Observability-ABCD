from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

_MIN_SUMMARY_CHARS = 40


def _parse_published(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10])
    except ValueError:
        return None


def _build_text_for_embedding(title: str, authors_joined: str, categories_joined: str, summary: str) -> str:
    parts = [
        f"Title: {title}",
        f"Authors: {authors_joined}" if authors_joined else "",
        f"Categories: {categories_joined}" if categories_joined else "",
        f"Summary: {summary}",
    ]
    return "\n".join(part for part in parts if part)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    rows: list[dict] = []

    for record in records:
        paper_id = record.paper_id.strip()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)

        # Bo record thieu id/title hoac summary qua ngan de dam bao text_for_embedding co y nghia.
        if not paper_id or not title or len(summary) < _MIN_SUMMARY_CHARS:
            continue

        published_dt = _parse_published(record.published)
        if published_dt is None:
            continue

        authors_joined = compact_join(author.strip() for author in record.authors)
        categories_joined = compact_join(category.strip() for category in record.categories)
        age_days = max((run_date.date() - published_dt.date()).days, 0)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category or "Uncategorized",
                "published": published_dt.date().isoformat(),
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": _build_text_for_embedding(
                    title, authors_joined, categories_joined, summary
                ),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.sort_values("published", ascending=False).reset_index(drop=True)
    return df
