# TrialFinder Evaluation Summary

## Dataset

- Indexed local trials: 36,522
- Evaluation queries: 10
- Results per query: Top 10
- Relevance labels:
  - 2 = highly relevant
  - 1 = partially relevant
  - 0 = not relevant

## Metrics

| Mode | Precision@5 | Precision@10 | nDCG@10 | Avg latency ms |
|---|---:|---:|---:|---:|
| Local index | 1.0 | 1.0 | 0.947 | 2487.53 |
| Local + Live API | 1.0 | 1.0 | 0.961 | 2577.74 |

## Interpretation

Local-index search is expected to be faster because it searches the pre-built BM25/TF-IDF index.
Local + Live API search is expected to be slower because it calls ClinicalTrials.gov at query time, but it can improve freshness and coverage for rare or unseen conditions.

## Report-ready sentence

TrialFinder was evaluated using manually designed clinical-trial search queries. For each query, the system returned the top 10 ranked results and computed Precision@5, Precision@10, nDCG@10, and average latency. We compared fast local-index retrieval against local retrieval with live ClinicalTrials.gov API expansion.
