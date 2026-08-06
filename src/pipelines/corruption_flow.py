from __future__ import annotations

import json

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _require(path, message: str) -> None:
    if not path.exists():
        raise RuntimeError(message)


def main() -> None:
    settings = load_settings()

    _require(settings.paths.baseline_metrics, "Baseline metrics not found. Run script/run_phase1.py first.")
    _require(settings.paths.clean_json, "Baseline clean dataset not found. Run script/run_phase1.py first.")
    _require(settings.paths.raw_records_json, "Raw records not found. Run script/run_phase1.py first.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = pd.DataFrame(read_json(settings.paths.clean_json))
    print(f"[corruption] loaded baseline dataset: {len(baseline_df)} rows")

    # 1) Corrupt the baseline clean dataset.
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, json.loads(corrupted_df.to_json(orient="records")))
    print(f"[corruption] corrupted dataset: {len(corrupted_df)} rows (log: {settings.paths.corruption_log})")

    # 2) Rebuild index on corrupted data (separate collection/path, baseline untouched).
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    print(
        f"[corruption] built corrupted index '{corrupted_index.collection_name}' "
        f"with {len(corrupted_index.documents)} documents"
    )

    # 3) Evaluate corrupted data on the SAME test set used for baseline.
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"[corruption] corrupted metrics: {corrupted_bundle.summary}")

    # 4) Quality/freshness on corrupted data.
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    print(
        f"[corruption] corrupted quality passed={corrupted_quality['passed']} "
        f"freshness is_fresh={corrupted_freshness['is_fresh']}"
    )

    # 5) Repair: re-derive the clean dataset from the trusted raw source (not by patching corrupted rows).
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, json.loads(repaired_df.to_json(orient="records")))
    print(f"[corruption] repaired dataset: {len(repaired_df)} rows")

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    print(
        f"[corruption] built repaired index '{repaired_index.collection_name}' "
        f"with {len(repaired_index.documents)} documents"
    )

    # 6) Evaluate repaired data on the SAME test set again.
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"[corruption] repaired metrics: {repaired_bundle.summary}")

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)
    print(
        f"[corruption] repaired quality passed={repaired_quality['passed']} "
        f"freshness is_fresh={repaired_freshness['is_fresh']}"
    )

    # 7) Comparison report.
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print(f"[corruption] comparison report written to {settings.paths.comparison_report}")
