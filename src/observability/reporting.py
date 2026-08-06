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


def _quality_summary_line(label: str, quality: dict[str, Any]) -> str:
    failed = quality.get("failed_checks") or []
    failed_text = ", ".join(failed) if failed else "none"
    return f"- {label} quality checks passed: **{quality.get('passed')}** (failed: {failed_text})"


def _freshness_summary_line(label: str, freshness: dict[str, Any]) -> str:
    return (
        f"- {label} freshness: is_fresh=**{freshness.get('is_fresh')}**, "
        f"stale_rows={freshness.get('stale_rows')}/{freshness.get('total_rows')}"
    )


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
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    metric_names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score", "samples"]
    lines = [
        "# Corruption / Repair Comparison Report",
        "",
        "## Metrics: baseline vs corrupted vs repaired",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | --- | --- | --- |",
    ]
    for name in metric_names:
        lines.append(
            f"| `{name}` | {baseline_metrics.get(name)} | {corrupted_metrics.get(name)} | {repaired_metrics.get(name)} |"
        )

    lines.extend(
        [
            "",
            "## Data quality & freshness",
            "",
            _quality_summary_line("Corrupted", corrupted_quality),
            _freshness_summary_line("Corrupted", corrupted_freshness),
            _quality_summary_line("Repaired", repaired_quality),
            _freshness_summary_line("Repaired", repaired_freshness),
            "",
            "## Metric deltas",
            "",
            "| Metric | Baseline -> Corrupted | Corrupted -> Repaired |",
            "| --- | --- | --- |",
        ]
    )
    for name in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        base = baseline_metrics.get(name)
        corrupted = corrupted_metrics.get(name)
        repaired = repaired_metrics.get(name)
        delta_corrupt = corrupted - base if isinstance(base, (int, float)) and isinstance(corrupted, (int, float)) else "n/a"
        delta_repair = (
            repaired - corrupted if isinstance(corrupted, (int, float)) and isinstance(repaired, (int, float)) else "n/a"
        )
        lines.append(f"| `{name}` | {delta_corrupt} | {delta_repair} |")
    lines.append("")

    write_text(report_path, "\n".join(lines))
