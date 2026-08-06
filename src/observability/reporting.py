from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

_MIN_SUMMARY_CHARS = 40


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks va ghi ket qua vao data/quality/."""
    total_rows = len(df)
    checks: list[dict[str, Any]] = [
        {
            "name": "row_count",
            "dimension": "completeness",
            "passed": total_rows > 0,
            "detail": {"total_rows": total_rows},
        }
    ]

    if total_rows == 0:
        result = {
            "report_name": report_name,
            "generated_at": now_utc().isoformat(),
            "total_rows": 0,
            "checks": checks,
            "passed": False,
            "failed_checks": ["row_count"],
        }
        write_json(settings.paths.quality_dir / f"{report_name}.json", result)
        return result

    null_or_blank_ids = int((df["paper_id"].isna() | (df["paper_id"].astype(str).str.strip() == "")).sum())
    duplicate_ids = int(df["paper_id"].duplicated().sum())
    checks.append(
        {
            "name": "paper_id_not_null_unique",
            "dimension": "uniqueness",
            "passed": null_or_blank_ids == 0 and duplicate_ids == 0,
            "detail": {"null_or_blank": null_or_blank_ids, "duplicates": duplicate_ids},
        }
    )

    blank_titles = int((df["title"].astype(str).str.strip() == "").sum())
    checks.append(
        {
            "name": "title_not_null",
            "dimension": "completeness",
            "passed": blank_titles == 0,
            "detail": {"blank_titles": blank_titles},
        }
    )

    short_summaries = int((df["summary"].astype(str).str.len() < _MIN_SUMMARY_CHARS).sum())
    checks.append(
        {
            "name": "summary_length",
            "dimension": "validity",
            "passed": short_summaries == 0,
            "detail": {"short_summaries": short_summaries, "min_chars": _MIN_SUMMARY_CHARS},
        }
    )

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    checks.append(
        {
            "name": "freshness",
            "dimension": "freshness",
            "passed": stale_rows == 0,
            "detail": {"stale_rows": stale_rows, "threshold_days": settings.freshness_threshold_days},
        }
    )

    failed_checks = [check["name"] for check in checks if not check["passed"]]
    result = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "total_rows": total_rows,
        "checks": checks,
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report tu cot `published`/`age_days`."""
    total_rows = len(df)

    if total_rows == 0:
        payload = {
            "generated_at": now_utc().isoformat(),
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
        }
        write_json(report_path, payload)
        return payload

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    payload = {
        "generated_at": now_utc().isoformat(),
        "latest_published": str(df["published"].max()),
        "oldest_published": str(df["published"].min()),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0,
    }
    write_json(report_path, payload)
    return payload
