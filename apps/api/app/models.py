from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class Trial(BaseModel):
    nct_id: str
    title: str
    status: str
    phase: Optional[str] = None
    conditions: List[str] = []
    interventions: List[str] = []
    summary: str = ""
    eligibility: str = ""
    sex: Optional[str] = None
    minimum_age: Optional[str] = None
    maximum_age: Optional[str] = None
    locations: List[Dict[str, Any]] = []
    source_url: Optional[str] = None
    last_update_date: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    condition: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "RECRUITING"
    top_k: int = 10
    include_live_api: bool = False

    # Retrieval modes:
    # bm25 = BM25 only
    # bm25_tfidf = BM25 + TF-IDF
    # weighted = BM25 + TF-IDF + structured scoring
    # semantic_hybrid = weighted + semantic reranking
    retrieval_mode: str = "weighted"


class ScoreBreakdown(BaseModel):
    bm25_score: float
    tfidf_score: float
    lexical_score: float
    semantic_score: float = 0.0
    condition_score: float
    eligibility_score: float
    status_score: float
    location_score: float
    condition_penalty: float
    final_score: float


class SearchResult(BaseModel):
    trial: Trial
    source: str
    score: ScoreBreakdown
    explanation: List[str]


class SearchResponse(BaseModel):
    query: str
    detected_filters: Dict[str, Any]
    results: List[SearchResult]