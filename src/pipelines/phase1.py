from __future__ import annotations

import json

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def _load_or_fetch_records(settings):
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        return fetch_source_records(settings)
    return load_raw_records(settings.paths.raw_records_json)


def _load_or_build_test_set(df, settings):
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        return build_test_set(df, settings.paths.eval_testset)
    return read_json(settings.paths.eval_testset)


def _demo_agent(settings, index, questions: list[str]) -> list[dict[str, str]]:
    agent = build_agent(settings, index)
    demo = [{"question": question, "answer": run_agent_question(agent, question)} for question in questions]
    write_json(settings.paths.demo_answers, demo)
    return demo


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    records = _load_or_fetch_records(settings)
    print(f"[phase1] loaded {len(records)} raw records")

    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError("Cleaning produced an empty dataset; check raw records and cleaning rules.")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, json.loads(df.to_json(orient="records")))
    print(f"[phase1] cleaned dataset: {len(df)} rows")

    index = LocalEmbeddingIndex.build(df, settings)
    print(f"[phase1] built embedding index '{index.collection_name}' with {len(index.documents)} documents")

    test_set = _load_or_build_test_set(df, settings)
    print(f"[phase1] evaluation set: {len(test_set)} questions")

    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"[phase1] baseline metrics: {bundle.summary}")

    quality = run_data_quality_checks(df, settings, "baseline_quality")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"[phase1] quality passed={quality['passed']} freshness is_fresh={freshness['is_fresh']}")

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_record_count": len(records),
        "clean_record_count": len(df),
        "fetched_at": run_date.isoformat(),
    }
    generate_phase1_report(settings.paths.baseline_report, source_summary, bundle.summary, quality, freshness)
    print(f"[phase1] report written to {settings.paths.baseline_report}")

    demo_questions = [item["question"] for item in test_set[:3]]
    if demo_questions:
        try:
            _demo_agent(settings, index, demo_questions)
            print(f"[phase1] demo agent answers written to {settings.paths.demo_answers}")
        except Exception as exc:  # optional step: LLM quota/network issues should not fail the pipeline
            print(f"[phase1] demo agent step skipped ({exc.__class__.__name__}: {exc})")
