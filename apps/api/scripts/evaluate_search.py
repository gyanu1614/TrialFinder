import csv
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[3]
API_DIR = ROOT_DIR / "apps" / "api"

sys.path.append(str(API_DIR))

from app.search_engine import TrialSearchEngine  # noqa: E402


OUTPUT_DIR = ROOT_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RETRIEVAL_MODES = [
    "bm25",
    "bm25_tfidf",
    "weighted",
    "semantic_hybrid",
]

MODE_LABELS = {
    "bm25": "BM25 only",
    "bm25_tfidf": "BM25 + TF-IDF",
    "weighted": "Weighted hybrid",
    "semantic_hybrid": "Semantic hybrid",
}

EVAL_QUERIES = [
    {
        "query": "stage 2 breast cancer trials near los angeles",
        "condition_terms": ["breast cancer", "breast neoplasms"],
        "must_have_any": ["stage ii", "stage 2", "early-stage", "early stage", "stage ii or iii"],
        "nice_to_have_any": ["los angeles", "duarte", "california"],
        "bad_terms": ["screening", "navigation", "education", "survey", "questionnaire"],
    },
    {
        "query": "diabetes trials using continuous glucose monitoring in california",
        "condition_terms": ["diabetes", "diabetes mellitus", "prediabetes"],
        "must_have_any": ["continuous glucose", "glucose monitoring", "cgm"],
        "nice_to_have_any": ["california", "los angeles", "san diego", "san francisco"],
        "bad_terms": ["survey", "questionnaire"],
    },
    {
        "query": "asthma trials for children in united states",
        "condition_terms": ["asthma"],
        "must_have_any": ["child", "children", "pediatric", "adolescent"],
        "nice_to_have_any": ["united states", "usa"],
        "bad_terms": ["adult only"],
    },
    {
        "query": "depression trials for adults not using medication",
        "condition_terms": ["depression", "major depressive", "mdd"],
        "must_have_any": ["adult", "adults"],
        "nice_to_have_any": ["psychotherapy", "digital", "behavioral", "non-drug", "non drug"],
        "bad_terms": ["pediatric", "children"],
    },
    {
        "query": "alzheimer trials for older adults",
        "condition_terms": ["alzheimer", "dementia"],
        "must_have_any": ["older adult", "older adults", "elderly", "aged", "65 years", "60 years"],
        "nice_to_have_any": [],
        "bad_terms": ["caregiver only"],
    },
    {
        "query": "lung cancer immunotherapy trials in california",
        "condition_terms": ["lung cancer", "lung neoplasm", "small cell lung", "non-small cell lung", "nsclc"],
        "must_have_any": ["immunotherapy", "pembrolizumab", "nivolumab", "durvalumab", "atezolizumab", "checkpoint"],
        "nice_to_have_any": ["california", "los angeles", "san diego", "san francisco"],
        "bad_terms": ["screening", "survey", "smoking cessation"],
    },
    {
        "query": "parkinson trials for adults in united states",
        "condition_terms": ["parkinson"],
        "must_have_any": ["adult", "adults", "18 years"],
        "nice_to_have_any": ["united states", "usa"],
        "bad_terms": ["caregiver only"],
    },
    {
        "query": "migraine prevention trials",
        "condition_terms": ["migraine"],
        "must_have_any": ["prevention", "preventive", "prophylaxis"],
        "nice_to_have_any": [],
        "bad_terms": ["survey", "questionnaire"],
    },
    {
        "query": "glioblastoma trials",
        "condition_terms": ["glioblastoma"],
        "must_have_any": [],
        "nice_to_have_any": ["newly diagnosed", "recurrent", "therapy", "treatment"],
        "bad_terms": [],
    },
    {
        "query": "hiv vaccine trials",
        "condition_terms": ["hiv", "human immunodeficiency virus"],
        "must_have_any": ["vaccine", "vaccination", "immunization"],
        "nice_to_have_any": [],
        "bad_terms": ["hpv vaccine"],
    },
]


def text_blob(result: Dict[str, Any]) -> str:
    trial = result["trial"]

    parts = [
        trial.get("title", ""),
        trial.get("summary", ""),
        trial.get("eligibility", ""),
        " ".join(trial.get("conditions", [])),
        " ".join(trial.get("interventions", [])),
    ]

    for loc in trial.get("locations", []):
        parts.extend(
            [
                str(loc.get("facility") or ""),
                str(loc.get("city") or ""),
                str(loc.get("state") or ""),
                str(loc.get("country") or ""),
            ]
        )

    return " ".join(parts).lower()


def has_any(blob: str, terms: List[str]) -> bool:
    return any(term.lower() in blob for term in terms)


def relevance_grade(result: Dict[str, Any], query_spec: Dict[str, Any]) -> int:
    blob = text_blob(result)

    condition_match = has_any(blob, query_spec["condition_terms"])
    must_match = True if not query_spec["must_have_any"] else has_any(blob, query_spec["must_have_any"])
    nice_match = True if not query_spec["nice_to_have_any"] else has_any(blob, query_spec["nice_to_have_any"])
    bad_match = has_any(blob, query_spec["bad_terms"])

    if not condition_match:
        return 0

    if condition_match and must_match and nice_match and not bad_match:
        return 2

    return 1


def precision_at_k_binary(grades: List[int], k: int) -> float:
    top_k = grades[:k]
    if not top_k:
        return 0.0

    relevant = sum(1 for grade in top_k if grade > 0)
    return relevant / k


def highly_relevant_at_k(grades: List[int], k: int) -> float:
    top_k = grades[:k]
    if not top_k:
        return 0.0

    highly_relevant = sum(1 for grade in top_k if grade == 2)
    return highly_relevant / k


def dcg_at_k(grades: List[int], k: int) -> float:
    import math

    dcg = 0.0
    for index, grade in enumerate(grades[:k]):
        rank = index + 1
        gain = 0 if grade == 0 else (1 if grade == 1 else 3)
        dcg += gain / math.log2(rank + 1)

    return dcg


def ndcg_at_k(grades: List[int], k: int) -> float:
    actual_dcg = dcg_at_k(grades, k)
    ideal_grades = sorted(grades, reverse=True)
    ideal_dcg = dcg_at_k(ideal_grades, k)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


def average(values: List[float]) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)


def evaluate_mode(engine: TrialSearchEngine, retrieval_mode: str) -> List[Dict[str, Any]]:
    rows = []

    for item in EVAL_QUERIES:
        query = item["query"]

        start = time.perf_counter()
        results, metadata = engine.search(
            query=query,
            top_k=10,
            include_live_api=False,
            retrieval_mode=retrieval_mode,
        )
        end = time.perf_counter()

        latency_ms = round((end - start) * 1000, 2)
        grades = [relevance_grade(result, item) for result in results]

        row = {
            "query": query,
            "retrieval_mode": retrieval_mode,
            "retrieval_label": MODE_LABELS[retrieval_mode],
            "precision_at_5": round(precision_at_k_binary(grades, 5), 3),
            "precision_at_10": round(precision_at_k_binary(grades, 10), 3),
            "highly_relevant_at_5": round(highly_relevant_at_k(grades, 5), 3),
            "highly_relevant_at_10": round(highly_relevant_at_k(grades, 10), 3),
            "ndcg_at_10": round(ndcg_at_k(grades, 10), 3),
            "latency_ms": latency_ms,
            "result_count": len(results),
            "top_result_title": results[0]["trial"]["title"] if results else "",
            "top_result_score": results[0]["score"]["final_score"] if results else 0,
            "top_result_grade": grades[0] if grades else 0,
            "grades": " ".join(str(grade) for grade in grades),
            "semantic_available": metadata.get("semantic_available"),
        }

        rows.append(row)

        print(
            f"{row['retrieval_label']} | "
            f"P@5={row['precision_at_5']} | "
            f"HR@5={row['highly_relevant_at_5']} | "
            f"HR@10={row['highly_relevant_at_10']} | "
            f"nDCG@10={row['ndcg_at_10']} | "
            f"{latency_ms} ms | {query}"
        )

    return rows


def write_csv(rows: List[Dict[str, Any]]) -> Path:
    output_path = OUTPUT_DIR / "evaluation_results_models.csv"

    fieldnames = [
        "query",
        "retrieval_mode",
        "retrieval_label",
        "precision_at_5",
        "precision_at_10",
        "highly_relevant_at_5",
        "highly_relevant_at_10",
        "ndcg_at_10",
        "latency_ms",
        "result_count",
        "top_result_title",
        "top_result_score",
        "top_result_grade",
        "grades",
        "semantic_available",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def write_summary(rows: List[Dict[str, Any]]) -> Path:
    output_path = OUTPUT_DIR / "evaluation_summary_models.md"

    def summarize(mode: str) -> Dict[str, float]:
        mode_rows = [row for row in rows if row["retrieval_mode"] == mode]

        return {
            "precision_at_5": round(average([row["precision_at_5"] for row in mode_rows]), 3),
            "precision_at_10": round(average([row["precision_at_10"] for row in mode_rows]), 3),
            "highly_relevant_at_5": round(average([row["highly_relevant_at_5"] for row in mode_rows]), 3),
            "highly_relevant_at_10": round(average([row["highly_relevant_at_10"] for row in mode_rows]), 3),
            "ndcg_at_10": round(average([row["ndcg_at_10"] for row in mode_rows]), 3),
            "latency_ms": round(average([row["latency_ms"] for row in mode_rows]), 2),
        }

    summaries = {mode: summarize(mode) for mode in RETRIEVAL_MODES}

    lines = [
        "# TrialFinder Retrieval Model Evaluation",
        "",
        "## Dataset",
        "",
        "- Indexed local trials: 36,522",
        f"- Evaluation queries: {len(EVAL_QUERIES)}",
        "- Results per query: Top 10",
        "- Live API expansion: disabled for model comparison",
        "",
        "## Relevance labels",
        "",
        "- 2 = highly relevant: condition plus query intent match",
        "- 1 = partially relevant: condition match but missing key intent",
        "- 0 = not relevant: wrong condition or unrelated trial",
        "",
        "## Metrics",
        "",
        "| Retrieval model | Precision@5 | Precision@10 | HighlyRelevant@5 | HighlyRelevant@10 | nDCG@10 | Avg latency ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for mode in RETRIEVAL_MODES:
        summary = summaries[mode]
        lines.append(
            f"| {MODE_LABELS[mode]} | "
            f"{summary['precision_at_5']} | "
            f"{summary['precision_at_10']} | "
            f"{summary['highly_relevant_at_5']} | "
            f"{summary['highly_relevant_at_10']} | "
            f"{summary['ndcg_at_10']} | "
            f"{summary['latency_ms']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "BM25 provides the lexical baseline. BM25 + TF-IDF adds vector-space similarity. "
            "Weighted hybrid adds structured field scoring for condition, eligibility, status, and location. "
            "Semantic hybrid reranks the top lexical candidates using embedding similarity, which is designed to improve intent-level matching.",
            "",
            "## Report-ready sentence",
            "",
            "TrialFinder compared four retrieval models: BM25 only, BM25 + TF-IDF, weighted hybrid retrieval, and semantic hybrid retrieval. "
            "Using 10 manually designed clinical-trial queries and graded relevance labels, we measured Precision@5, Precision@10, HighlyRelevant@5, HighlyRelevant@10, nDCG@10, and average latency.",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main():
    print("Loading TrialFinder search engine...")
    engine = TrialSearchEngine()

    print(f"Loaded {len(engine.trials)} trials.")

    all_rows = []

    for mode in RETRIEVAL_MODES:
        print(f"\nEvaluating retrieval mode: {MODE_LABELS[mode]}")
        rows = evaluate_mode(engine, retrieval_mode=mode)
        all_rows.extend(rows)

    csv_path = write_csv(all_rows)
    summary_path = write_summary(all_rows)

    print("\nDone.")
    print(f"CSV saved to: {csv_path}")
    print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()