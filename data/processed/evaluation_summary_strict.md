# TrialFinder Strict Evaluation Summary

## Dataset

- Indexed local trials: 36,522
- Evaluation queries: 10
- Results per query: Top 10

## Relevance labels

- 2 = highly relevant: condition plus query intent match
- 1 = partially relevant: condition match but missing key intent such as treatment, stage, location, or intervention
- 0 = not relevant: wrong condition or unrelated trial

## Metrics

| Mode | Precision@5 | Precision@10 | HighlyRelevant@5 | HighlyRelevant@10 | nDCG@10 | Avg latency ms |
|---|---:|---:|---:|---:|---:|---:|
| Local index | 1.0 | 1.0 | 0.58 | 0.53 | 0.915 | 2722.6 |
| Local + Live API | 1.0 | 1.0 | 0.6 | 0.6 | 0.935 | 2520.08 |

## Interpretation

This stricter evaluation separates condition-level relevance from intent-level relevance. A result can match the disease but still be only partially relevant if it misses the requested stage, treatment type, location, or intervention. This makes the evaluation more realistic than keyword-only matching.

## Report-ready sentence

TrialFinder was evaluated with 10 manually designed clinical-trial search queries and graded relevance labels. We measured Precision@5, Precision@10, HighlyRelevant@5, HighlyRelevant@10, nDCG@10, and average latency. The stricter evaluator distinguishes general condition matches from highly relevant results that also satisfy query intent such as stage, treatment, location, or intervention.
