import json
import math
import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.clinicaltrials_client import fetch_live_trials

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity
except Exception:
    SentenceTransformer = None
    sklearn_cosine_similarity = None


ROOT_DIR = Path(__file__).resolve().parents[3]
TRIAL_DATA_FILE = os.getenv("TRIAL_DATA_FILE", "trials.json")
TRIALS_PATH = ROOT_DIR / "data" / "processed" / TRIAL_DATA_FILE


KNOWN_CONDITIONS = [
    "glioblastoma",
    "breast cancer",
    "lung cancer",
    "prostate cancer",
    "colon cancer",
    "colorectal cancer",
    "skin cancer",
    "melanoma",
    "leukemia",
    "lymphoma",
    "diabetes",
    "type 1 diabetes",
    "type 2 diabetes",
    "depression",
    "anxiety",
    "asthma",
    "alzheimer",
    "parkinson",
    "heart disease",
    "hypertension",
    "stroke",
    "obesity",
    "arthritis",
    "migraine",
    "hiv",
    "covid",
    "kidney disease",
    "liver disease",
    "multiple sclerosis",
    "hidradenitis suppurativa",
]


CONDITION_ALIASES = {
    "glioblastoma": ["glioblastoma", "gbm"],
    "breast cancer": ["breast cancer", "breast carcinoma", "breast neoplasm", "breast neoplasms"],
    "lung cancer": ["lung cancer", "lung carcinoma", "non-small cell lung cancer", "nsclc", "small cell lung cancer"],
    "prostate cancer": ["prostate cancer", "prostate carcinoma"],
    "colon cancer": ["colon cancer", "colorectal cancer", "colon carcinoma"],
    "colorectal cancer": ["colorectal cancer", "colon cancer", "rectal cancer"],
    "diabetes": ["diabetes", "type 1 diabetes", "type 2 diabetes", "diabetes mellitus"],
    "depression": ["depression", "major depressive disorder", "mdd"],
    "anxiety": ["anxiety", "generalized anxiety disorder", "gad"],
    "asthma": ["asthma"],
    "alzheimer": ["alzheimer", "alzheimer disease", "alzheimer's disease"],
    "parkinson": ["parkinson", "parkinson disease", "parkinson's disease"],
    "hypertension": ["hypertension", "high blood pressure"],
    "heart disease": ["heart disease", "cardiovascular disease", "coronary artery disease"],
    "stroke": ["stroke", "cerebrovascular accident"],
    "obesity": ["obesity", "overweight"],
    "migraine": ["migraine"],
    "hiv": ["hiv", "human immunodeficiency virus"],
    "covid": ["covid", "covid-19", "sars-cov-2"],
    "hidradenitis suppurativa": ["hidradenitis suppurativa"],
}


VALID_RETRIEVAL_MODES = {
    "bm25",
    "bm25_tfidf",
    "weighted",
    "semantic_hybrid",
}


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def normalize_text(text: str) -> str:
    return " ".join(tokenize(text))


def normalize_scores(scores: List[float]) -> List[float]:
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if math.isclose(max_score, min_score):
        return [0.0 for _ in scores]

    return [(score - min_score) / (max_score - min_score) for score in scores]


def trial_to_document(trial: Dict[str, Any]) -> str:
    title = trial.get("title", "")
    conditions = " ".join(trial.get("conditions", []))
    interventions = " ".join(trial.get("interventions", []))
    summary = trial.get("summary", "")
    eligibility = trial.get("eligibility", "")

    return (
        f"{title} {title} {title} "
        f"{conditions} {conditions} {conditions} {conditions} "
        f"{interventions} {interventions} "
        f"{summary} "
        f"{eligibility}"
    )


def trial_to_semantic_document(trial: Dict[str, Any]) -> str:
    title = trial.get("title", "")
    conditions = ", ".join(trial.get("conditions", [])[:8])
    interventions = ", ".join(trial.get("interventions", [])[:8])
    summary = trial.get("summary", "")

    return (
        f"Title: {title}. "
        f"Conditions: {conditions}. "
        f"Interventions: {interventions}. "
        f"Summary: {summary[:1200]}"
    )


def detect_condition(query: str) -> Optional[str]:
    query_norm = normalize_text(query)

    for canonical, aliases in CONDITION_ALIASES.items():
        for alias in aliases:
            if normalize_text(alias) in query_norm:
                return canonical

    for condition in KNOWN_CONDITIONS:
        if normalize_text(condition) in query_norm:
            return condition

    return None


def detect_location_terms(query: str) -> List[str]:
    common_locations = [
        "los angeles",
        "california",
        "new york",
        "boston",
        "chicago",
        "houston",
        "dallas",
        "texas",
        "san diego",
        "san francisco",
        "seattle",
        "florida",
        "united states",
    ]

    query_norm = normalize_text(query)
    return [loc for loc in common_locations if normalize_text(loc) in query_norm]


class TrialSearchEngine:
    def __init__(self):
        self.trials = self.load_trials()
        self.documents = [trial_to_document(trial) for trial in self.trials]
        self.tokenized_documents = [tokenize(doc) for doc in self.documents]

        self.bm25 = BM25Okapi(self.tokenized_documents)

        self.tfidf = TfidfVectorizer(stop_words="english", max_features=20000)
        self.tfidf_matrix = self.tfidf.fit_transform(self.documents)

        self.semantic_model = None

    def load_trials(self) -> List[Dict[str, Any]]:
        if not TRIALS_PATH.exists():
            return []

        with open(TRIALS_PATH, "r", encoding="utf-8") as file:
            return json.load(file)

    def load_semantic_model(self):
        if self.semantic_model is not None:
            return self.semantic_model

        if SentenceTransformer is None:
            return None

        if os.getenv("DISABLE_SEMANTIC", "false").lower() == "true":
            self.semantic_model = None
        return None

        # Lightweight model commonly used for semantic similarity demos.
        self.semantic_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self.semantic_model

    def get_trial_condition_text(self, trial: Dict[str, Any]) -> str:
        return normalize_text(" ".join(trial.get("conditions", [])))

    def strict_condition_match(self, detected_condition: Optional[str], trial: Dict[str, Any]) -> bool:
        if not detected_condition:
            return True

        trial_conditions = self.get_trial_condition_text(trial)
        aliases = CONDITION_ALIASES.get(detected_condition, [detected_condition])

        for alias in aliases:
            alias_norm = normalize_text(alias)
            if alias_norm and alias_norm in trial_conditions:
                return True

        return False

    def condition_score(
        self,
        query: str,
        trial: Dict[str, Any],
        detected_condition: Optional[str],
    ) -> float:
        trial_conditions = self.get_trial_condition_text(trial)

        if detected_condition:
            return 1.0 if self.strict_condition_match(detected_condition, trial) else 0.0

        query_tokens = set(tokenize(query))
        condition_tokens = set(tokenize(" ".join(trial.get("conditions", []))))

        if not condition_tokens:
            return 0.0

        overlap = query_tokens.intersection(condition_tokens)
        return min(1.0, len(overlap) / max(1, len(condition_tokens)))

    def eligibility_score(self, query: str, trial: Dict[str, Any]) -> float:
        query_tokens = set(tokenize(query))
        eligibility_tokens = set(tokenize(trial.get("eligibility", "")))

        if not eligibility_tokens:
            return 0.0

        overlap = query_tokens.intersection(eligibility_tokens)
        return min(1.0, len(overlap) / 8)

    def status_score(self, trial: Dict[str, Any]) -> float:
        status = trial.get("status", "").upper()

        if status == "RECRUITING":
            return 1.0
        if status == "NOT_YET_RECRUITING":
            return 0.8
        if status == "ACTIVE_NOT_RECRUITING":
            return 0.4
        return 0.2

    def location_score(self, query: str, trial: Dict[str, Any]) -> float:
        location_terms = detect_location_terms(query)
        if not location_terms:
            return 0.0

        location_blob = normalize_text(
            " ".join(
                " ".join(
                    str(loc.get(field) or "")
                    for field in ["facility", "city", "state", "country", "zip"]
                )
                for loc in trial.get("locations", [])
            )
        )

        if not location_blob:
            return 0.0

        for loc in location_terms:
            if normalize_text(loc) in location_blob:
                return 1.0

        query_norm = normalize_text(query)
        if "los angeles" in query_norm and "california" in location_blob:
            return 0.6

        return 0.0

    def compute_semantic_scores(
        self,
        query: str,
        ranked_items: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        model = self.load_semantic_model()

        if model is None or sklearn_cosine_similarity is None or not ranked_items:
            return {}

        try:
            query_embedding = model.encode([query])
            candidate_texts = [
                trial_to_semantic_document(item["trial"])
                for item in ranked_items
            ]
            candidate_embeddings = model.encode(candidate_texts)

            similarities = sklearn_cosine_similarity(
                query_embedding,
                candidate_embeddings,
            ).flatten().tolist()

            normalized = normalize_scores(similarities)

            scores = {}
            for item, score in zip(ranked_items, normalized):
                scores[item["trial"]["nct_id"]] = score

            return scores
        except Exception:
            return {}

    def build_explanation(
        self,
        trial: Dict[str, Any],
        detected_condition: Optional[str],
        bm25_score: float,
        tfidf_score: float,
        semantic_score: float,
        condition_score: float,
        eligibility_score: float,
        status_score: float,
        location_score: float,
        source: str,
        retrieval_mode: str,
    ) -> List[str]:
        explanation = []

        if retrieval_mode == "bm25":
            explanation.append("Ranked using BM25 lexical retrieval only.")
        elif retrieval_mode == "bm25_tfidf":
            explanation.append("Ranked using BM25 and TF-IDF cosine similarity.")
        elif retrieval_mode == "weighted":
            explanation.append("Ranked using BM25, TF-IDF, and structured field scoring.")
        elif retrieval_mode == "semantic_hybrid":
            explanation.append("Ranked using lexical, structured, and semantic similarity signals.")

        if detected_condition and condition_score == 1.0:
            explanation.append(f"Condition field matches detected condition: {detected_condition}.")

        if eligibility_score > 0.2:
            explanation.append("Eligibility criteria contain relevant query terms.")

        if status_score >= 1.0:
            explanation.append("Trial is currently recruiting.")
        elif status_score >= 0.8:
            explanation.append("Trial is not yet recruiting but may become available.")

        if location_score > 0:
            explanation.append("Trial location appears relevant to the query.")

        if bm25_score > 0.5:
            explanation.append("High BM25 lexical relevance.")

        if tfidf_score > 0.5:
            explanation.append("High TF-IDF similarity.")

        if semantic_score > 0.5:
            explanation.append("High semantic similarity to the query.")

        if source == "local_index":
            explanation.append("Result came from the fast local indexed dataset.")
        elif source == "live_api":
            explanation.append("Result came from live ClinicalTrials.gov API expansion.")

        return explanation

    def get_candidate_indices(self, detected_condition: Optional[str]) -> List[int]:
        if not detected_condition:
            return list(range(len(self.trials)))

        matched = [
            index
            for index, trial in enumerate(self.trials)
            if self.strict_condition_match(detected_condition, trial)
        ]

        if len(matched) >= 5:
            return matched

        return list(range(len(self.trials)))

    def score_trials(
        self,
        query: str,
        trials: List[Dict[str, Any]],
        source: str,
        detected_condition: Optional[str],
        top_k: int,
        retrieval_mode: str,
    ) -> List[Dict[str, Any]]:
        if not trials:
            return []

        if retrieval_mode not in VALID_RETRIEVAL_MODES:
            retrieval_mode = "weighted"

        documents = [trial_to_document(trial) for trial in trials]
        tokenized_documents = [tokenize(doc) for doc in documents]

        bm25 = BM25Okapi(tokenized_documents)

        tfidf = TfidfVectorizer(stop_words="english", max_features=20000)
        tfidf_matrix = tfidf.fit_transform(documents)

        query_tokens = tokenize(query)

        raw_bm25_scores = bm25.get_scores(query_tokens).tolist()
        bm25_scores = normalize_scores(raw_bm25_scores)

        query_vector = tfidf.transform([query])
        raw_tfidf_scores = cosine_similarity(query_vector, tfidf_matrix).flatten().tolist()
        tfidf_scores = normalize_scores(raw_tfidf_scores)

        base_results = []

        for index, trial in enumerate(trials):
            c_score = self.condition_score(query, trial, detected_condition)
            e_score = self.eligibility_score(query, trial)
            s_score = self.status_score(trial)
            l_score = self.location_score(query, trial)

            condition_penalty = 1.0
            if detected_condition and c_score == 0.0:
                condition_penalty = 0.15

            lexical_score = 0.60 * bm25_scores[index] + 0.40 * tfidf_scores[index]

            if retrieval_mode == "bm25":
                final_score = bm25_scores[index]

            elif retrieval_mode == "bm25_tfidf":
                final_score = lexical_score

            else:
                final_score = (
                    0.40 * lexical_score
                    + 0.25 * c_score
                    + 0.15 * e_score
                    + 0.10 * s_score
                    + 0.10 * l_score
                ) * condition_penalty

            base_results.append(
                {
                    "trial": trial,
                    "source": source,
                    "score": {
                        "bm25_score": round(bm25_scores[index], 4),
                        "tfidf_score": round(tfidf_scores[index], 4),
                        "lexical_score": round(lexical_score, 4),
                        "semantic_score": 0.0,
                        "condition_score": round(c_score, 4),
                        "eligibility_score": round(e_score, 4),
                        "status_score": round(s_score, 4),
                        "location_score": round(l_score, 4),
                        "condition_penalty": round(condition_penalty, 4),
                        "final_score": round(final_score, 4),
                    },
                    "explanation": [],
                }
            )

        base_results.sort(key=lambda item: item["score"]["final_score"], reverse=True)

        # Semantic hybrid reranks only a candidate pool to keep the app usable.
        # This is enough for the academic demo: lexical retrieval gets candidates,
        # semantic similarity reranks them.
        if retrieval_mode == "semantic_hybrid":
            rerank_pool_size = min(80, len(base_results))
            rerank_pool = base_results[:rerank_pool_size]
            semantic_scores = self.compute_semantic_scores(query, rerank_pool)

            for item in rerank_pool:
                nct_id = item["trial"]["nct_id"]
                sem_score = semantic_scores.get(nct_id, 0.0)
                item["score"]["semantic_score"] = round(sem_score, 4)

                lexical_score = item["score"]["lexical_score"]
                c_score = item["score"]["condition_score"]
                e_score = item["score"]["eligibility_score"]
                s_score = item["score"]["status_score"]
                l_score = item["score"]["location_score"]
                condition_penalty = item["score"]["condition_penalty"]

                hybrid_score = (
                    0.30 * lexical_score
                    + 0.25 * sem_score
                    + 0.20 * c_score
                    + 0.10 * e_score
                    + 0.075 * s_score
                    + 0.075 * l_score
                ) * condition_penalty

                item["score"]["final_score"] = round(hybrid_score, 4)

            base_results = rerank_pool + base_results[rerank_pool_size:]
            base_results.sort(key=lambda item: item["score"]["final_score"], reverse=True)

        top_results = base_results[:top_k]

        for item in top_results:
            item["explanation"] = self.build_explanation(
                trial=item["trial"],
                detected_condition=detected_condition,
                bm25_score=item["score"]["bm25_score"],
                tfidf_score=item["score"]["tfidf_score"],
                semantic_score=item["score"]["semantic_score"],
                condition_score=item["score"]["condition_score"],
                eligibility_score=item["score"]["eligibility_score"],
                status_score=item["score"]["status_score"],
                location_score=item["score"]["location_score"],
                source=source,
                retrieval_mode=retrieval_mode,
            )

        return top_results

    def search(
        self,
        query: str,
        top_k: int = 10,
        include_live_api: bool = False,
        retrieval_mode: str = "weighted",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if retrieval_mode not in VALID_RETRIEVAL_MODES:
            retrieval_mode = "weighted"

        if not self.trials:
            return [], {
                "search_mode": "local_index",
                "retrieval_mode": retrieval_mode,
                "indexed_trial_count": 0,
                "detected_condition": None,
                "detected_locations": [],
                "candidate_count": 0,
                "fallback_recommended": True,
                "live_api_used": False,
                "live_api_count": 0,
                "live_api_forced": include_live_api,
            }

        detected_condition = detect_condition(query)
        detected_locations = detect_location_terms(query)

        candidate_indices = self.get_candidate_indices(detected_condition)
        local_candidates = [self.trials[index] for index in candidate_indices]

        local_results = self.score_trials(
            query=query,
            trials=local_candidates,
            source="local_index",
            detected_condition=detected_condition,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
        )

        best_score = local_results[0]["score"]["final_score"] if local_results else 0

        fallback_recommended = (
            len(local_results) < 3
            or best_score < 0.25
            or (detected_condition is not None and len(candidate_indices) < 5)
        )

        live_api_used = False
        live_api_count = 0
        final_results = local_results
        search_mode = "local_index"

        if fallback_recommended or include_live_api:
            try:
                live_trials = fetch_live_trials(
                    query=query,
                    condition=detected_condition,
                    page_size=50,
                )

                raw_live_api_count = len(live_trials)

                existing_ids = {result["trial"]["nct_id"] for result in local_results}
                live_trials = [
                    trial for trial in live_trials
                    if trial["nct_id"] not in existing_ids
                ]

                live_api_count = raw_live_api_count

                if include_live_api:
                    search_mode = "local_plus_live_api"

                if live_trials:
                    live_results = self.score_trials(
                        query=query,
                        trials=live_trials,
                        source="live_api",
                        detected_condition=detected_condition,
                        top_k=top_k,
                        retrieval_mode=retrieval_mode,
                    )

                    combined = local_results + live_results
                    combined.sort(
                        key=lambda item: item["score"]["final_score"],
                        reverse=True,
                    )

                    final_results = combined[:top_k]
                    live_api_used = True
                    search_mode = "local_plus_live_api"

            except Exception:
                live_api_used = False
                live_api_count = 0
                final_results = local_results
                search_mode = "local_index"

        metadata = {
            "search_mode": search_mode,
            "retrieval_mode": retrieval_mode,
            "indexed_trial_count": len(self.trials),
            "detected_condition": detected_condition,
            "detected_locations": detected_locations,
            "candidate_count": len(candidate_indices),
            "fallback_recommended": fallback_recommended,
            "live_api_used": live_api_used,
            "live_api_count": live_api_count,
            "live_api_forced": include_live_api,
            "semantic_available": SentenceTransformer is not None,
            "note": "Retrieval mode controls the ranking algorithm: BM25, BM25+TF-IDF, weighted hybrid, or semantic hybrid.",
        }

        return final_results, metadata