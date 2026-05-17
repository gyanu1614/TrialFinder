export type RetrievalMode =
  | "bm25"
  | "bm25_tfidf"
  | "weighted"
  | "semantic_hybrid";

export type Trial = {
  nct_id: string;
  title: string;
  status: string;
  phase?: string | null;
  conditions: string[];
  interventions: string[];
  summary: string;
  eligibility: string;
  sex?: string | null;
  minimum_age?: string | null;
  maximum_age?: string | null;
  locations: Array<{
    facility?: string | null;
    city?: string | null;
    state?: string | null;
    country?: string | null;
    zip?: string | null;
  }>;
  source_url?: string | null;
  last_update_date?: string | null;
};

export type ScoreBreakdown = {
  bm25_score: number;
  tfidf_score: number;
  lexical_score: number;
  semantic_score: number;
  condition_score: number;
  eligibility_score: number;
  status_score: number;
  location_score: number;
  condition_penalty: number;
  final_score: number;
};

export type SearchResult = {
  trial: Trial;
  source: "local_index" | "live_api";
  score: ScoreBreakdown;
  explanation: string[];
};

export type SearchResponse = {
  query: string;
  detected_filters: {
    condition?: string | null;
    location?: string[] | string | null;
    status?: string | null;
    search_mode?: string | null;
    retrieval_mode?: RetrievalMode | string | null;
    indexed_trial_count?: number;
    candidate_count?: number;
    fallback_recommended?: boolean;
    live_api_used?: boolean;
    live_api_count?: number;
    live_api_forced?: boolean;
    semantic_available?: boolean;
    note?: string;
  };
  results: SearchResult[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function searchTrials(
  query: string,
  includeLiveApi = false,
  retrievalMode: RetrievalMode = "weighted"
): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      status: "RECRUITING",
      top_k: 10,
      include_live_api: includeLiveApi,
      retrieval_mode: retrievalMode,
    }),
  });

  if (!response.ok) {
    throw new Error("Search request failed");
  }

  return response.json();
}