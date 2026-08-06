# Phase 1 Baseline Report

## Source

- API: Crossref REST API
- Query: agentic retrieval augmented generation large language model
- Filter: from-pub-date:2026-02-07,has-abstract:true
- Raw records fetched: 24
- Clean records kept: 24
- Fetched at: 2026-08-06T08:46:46.305750+00:00

## Evaluation metrics

| Metric | Value |
| --- | --- |
| `retrieval_hit_rate` | 1.0 |
| `mean_token_f1` | 1.0 |
| `judge_accuracy` | 1.0 |
| `mean_judge_score` | 5 |
| `samples` | 24 |

## Data quality

| Check | Dimension | Passed | Detail |
| --- | --- | --- | --- |
| row_count | completeness | True | {'total_rows': 24} |
| paper_id_not_null_unique | uniqueness | True | {'null_or_blank': 0, 'duplicates': 0} |
| title_not_null | completeness | True | {'blank_titles': 0} |
| summary_length | validity | True | {'short_summaries': 0, 'min_chars': 40} |
| freshness | freshness | True | {'stale_rows': 0, 'threshold_days': 180} |

Overall passed: **True**

## Freshness

- Latest published: 2026-08-01
- Oldest published: 2026-02-12
- Stale rows: 0 / 24
- Threshold (days): 180
- Is fresh: **True**
