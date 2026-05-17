# TrialFinder Retrieval Model Evaluation

## Dataset

- Indexed local trials: 36,522
- Evaluation queries: 10
- Results per query: Top 10
- Live API expansion: disabled for model comparison

## Relevance labels

- 2 = highly relevant: condition plus query intent match
- 1 = partially relevant: condition match but missing key intent
- 0 = not relevant: wrong condition or unrelated trial

## Metrics

| Retrieval model | Precision@5 | Precision@10 | HighlyRelevant@5 | HighlyRelevant@10 | nDCG@10 | Avg latency ms |
|---|---:|---:|---:|---:|---:|---:|
| BM25 only | 1.0 | 1.0 | 0.48 | 0.47 | 0.931 | 776.44 |
| BM25 + TF-IDF | 1.0 | 1.0 | 0.44 | 0.45 | 0.927 | 695.42 |
| Weighted hybrid | 1.0 | 1.0 | 0.58 | 0.53 | 0.91 | 721.93 |
| Semantic hybrid | 1.0 | 1.0 | 0.54 | 0.58 | 0.907 | 3177.0 |

## Interpretation

BM25 provides the lexical baseline. BM25 + TF-IDF adds vector-space similarity. Weighted hybrid adds structured field scoring for condition, eligibility, status, and location. Semantic hybrid reranks the top lexical candidates using embedding similarity, which is designed to improve intent-level matching.

## Report-ready sentence

TrialFinder compared four retrieval models: BM25 only, BM25 + TF-IDF, weighted hybrid retrieval, and semantic hybrid retrieval. Using 10 manually designed clinical-trial queries and graded relevance labels, we measured Precision@5, Precision@10, HighlyRelevant@5, HighlyRelevant@10, nDCG@10, and average latency.