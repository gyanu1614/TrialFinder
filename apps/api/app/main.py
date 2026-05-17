from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import SearchRequest
from app.search_engine import TrialSearchEngine

app = FastAPI(
    title="TrialFinder API",
    description="Explainable clinical trial search engine using BM25, TF-IDF, weighted scoring, and semantic hybrid retrieval.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

search_engine = TrialSearchEngine()


@app.get("/")
def root():
    return {
        "app": "TrialFinder API",
        "status": "running",
        "trial_count": len(search_engine.trials),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "trial_count": len(search_engine.trials),
    }


@app.post("/search")
def search_trials(request: SearchRequest):
    results, metadata = search_engine.search(
        request.query,
        top_k=request.top_k,
        include_live_api=request.include_live_api,
        retrieval_mode=request.retrieval_mode,
    )

    return {
        "query": request.query,
        "detected_filters": {
            "condition": metadata.get("detected_condition") or request.condition,
            "location": metadata.get("detected_locations") or request.location,
            "status": request.status,
            "search_mode": metadata.get("search_mode"),
            "retrieval_mode": metadata.get("retrieval_mode"),
            "indexed_trial_count": metadata.get("indexed_trial_count"),
            "candidate_count": metadata.get("candidate_count"),
            "fallback_recommended": metadata.get("fallback_recommended"),
            "live_api_used": metadata.get("live_api_used"),
            "live_api_count": metadata.get("live_api_count"),
            "live_api_forced": metadata.get("live_api_forced"),
            "semantic_available": metadata.get("semantic_available"),
            "note": metadata.get("note"),
        },
        "results": results,
    }


@app.get("/trial/{nct_id}")
def get_trial(nct_id: str):
    for trial in search_engine.trials:
        if trial["nct_id"] == nct_id:
            return trial

    return {"error": "Trial not found"}