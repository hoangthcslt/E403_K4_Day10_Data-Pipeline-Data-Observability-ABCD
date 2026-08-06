# Corruption / Repair Comparison Report

## Metrics: baseline vs corrupted vs repaired

| Metric | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| `retrieval_hit_rate` | 1.0 | 0.75 | 1.0 |
| `mean_token_f1` | 1.0 | 0.5575295578736194 | 1.0 |
| `judge_accuracy` | 1.0 | 0.5416666666666666 | 1.0 |
| `mean_judge_score` | 5 | 3.0833333333333335 | 5 |
| `samples` | 24 | 24 | 24 |

## Data quality & freshness

- Corrupted quality checks passed: **False** (failed: paper_id_not_null_unique, summary_length, freshness)
- Corrupted freshness: is_fresh=**False**, stale_rows=2/24
- Repaired quality checks passed: **True** (failed: none)
- Repaired freshness: is_fresh=**True**, stale_rows=0/24

## Metric deltas

| Metric | Baseline -> Corrupted | Corrupted -> Repaired |
| --- | --- | --- |
| `retrieval_hit_rate` | -0.25 | 0.25 |
| `mean_token_f1` | -0.44247044212638065 | 0.44247044212638065 |
| `judge_accuracy` | -0.45833333333333337 | 0.45833333333333337 |
| `mean_judge_score` | -1.9166666666666665 | 1.9166666666666665 |
