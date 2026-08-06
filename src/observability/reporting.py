from __future__ import annotations

from typing import Any

from core.utils import write_text


def _format_metrics_table(metrics: dict[str, Any]) -> str:
    rows = [
        ("retrieval_hit_rate", metrics.get("retrieval_hit_rate")),
        ("mean_token_f1", metrics.get("mean_token_f1")),
        ("judge_accuracy", metrics.get("judge_accuracy")),
        ("mean_judge_score", metrics.get("mean_judge_score")),
        ("samples", metrics.get("samples")),
    ]
    lines = ["| Metric | Value |", "| --- | --- |"]
    lines.extend(f"| `{name}` | {value} |" for name, value in rows)
    return "\n".join(lines)


def _format_quality_section(quality: dict[str, Any]) -> str:
    lines = ["| Check | Dimension | Passed | Detail |", "| --- | --- | --- | --- |"]
    for check in quality.get("checks", []):
        lines.append(f"| {check['name']} | {check['dimension']} | {check['passed']} | {check['detail']} |")
    lines.append("")
    lines.append(f"Overall passed: **{quality.get('passed')}**")
    if quality.get("failed_checks"):
        lines.append(f"Failed checks: {', '.join(quality['failed_checks'])}")
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase."""
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source",
        "",
        f"- API: {source_summary.get('source_api')}",
        f"- Query: {source_summary.get('source_query')}",
        f"- Filter: {source_summary.get('source_filter')}",
        f"- Raw records fetched: {source_summary.get('raw_record_count')}",
        f"- Clean records kept: {source_summary.get('clean_record_count')}",
        f"- Fetched at: {source_summary.get('fetched_at')}",
        "",
        "## Evaluation metrics",
        "",
        _format_metrics_table(metrics),
        "",
        "## Data quality",
        "",
        _format_quality_section(quality),
        "",
        "## Freshness",
        "",
        f"- Latest published: {freshness.get('latest_published')}",
        f"- Oldest published: {freshness.get('oldest_published')}",
        f"- Stale rows: {freshness.get('stale_rows')} / {freshness.get('total_rows')}",
        f"- Threshold (days): {freshness.get('threshold_days')}",
        f"- Is fresh: **{freshness.get('is_fresh')}**",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
