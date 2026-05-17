# TrialFinder

**An Explainable Hybrid Search Engine for Clinical Trial Discovery**

TrialFinder is a clinical-trial search engine built for **CECS 429/529 Search Engine Technology**. It helps users search clinical trials using natural language and compares multiple information retrieval models, including **BM25**, **BM25 + TF-IDF**, **Weighted Hybrid Retrieval**, and **Semantic Hybrid Retrieval**.

Instead of only returning a ranked list, TrialFinder explains why each trial was ranked by showing component-level scores such as BM25 score, TF-IDF score, semantic score, condition match, eligibility match, location match, and final score.

---

## Project Motivation

ClinicalTrials.gov contains hundreds of thousands of clinical studies, but searching for the right trial can be difficult for patients, students, and even clinicians. A user may search:

```text
lung cancer immunotherapy trials in California
Instead of returning only a ranked list, TrialFinder shows why each result ranked where it did. Each trial card includes score breakdowns for BM25, TF-IDF, semantic similarity, condition match, eligibility match, location match, and final ranking score.

The project compares four retrieval models on the same clinical-trial corpus:

BM25 only
BM25 + TF-IDF
Weighted Hybrid Retrieval
Semantic Hybrid Retrieval

The full local index was built from the public ClinicalTrials.gov API v2. The repository excludes the generated trials.json file because it is larger than GitHub’s normal file-size limit. GitHub blocks regular Git pushes for files over 100 MB, so the dataset must be regenerated locally using the ingestion script.

Project Motivation

ClinicalTrials.gov contains hundreds of thousands of registered clinical studies. However, finding the right trial is still difficult because trial records are written in dense clinical language.

A patient or student may search:

stage 2 breast cancer trials near los angeles

But the trial record may use wording such as:

Stage II breast neoplasms
early-stage breast cancer
neoadjuvant treatment
eligibility criteria

This creates a classic information retrieval problem:

How do we rank clinical trials so that the best results match both the medical condition and the user’s actual intent?

TrialFinder addresses this by combining lexical search, vector-space scoring, structured field scoring, and semantic reranking.

Key Features
Natural-language clinical-trial search
Local indexed corpus of 36,522 clinical trials
Data sourced from ClinicalTrials.gov API v2
Four retrieval modes:
BM25 only
BM25 + TF-IDF
Weighted Hybrid
Semantic Hybrid
Explainable score breakdown for every result
Live ClinicalTrials.gov API expansion toggle
Model-comparison UI
Evaluation script for:
Precision@5
Precision@10
HighlyRelevant@5
HighlyRelevant@10
nDCG@10
latency
Final report and presentation files included in docs/
Demo Queries

Use these queries to test the system:

lung cancer immunotherapy trials in california
stage 2 breast cancer trials near los angeles
diabetes trials using continuous glucose monitoring in california
glioblastoma CAR T therapy trials in texas
depression trials for adults not using medication

The ranking may change when switching retrieval modes. That is expected because each model optimizes for a different retrieval signal.

Retrieval Models
Model	Description	Strength	Limitation
BM25 only	Classic lexical keyword baseline	Fast and strong for exact word matching	Can over-rank keyword-heavy but intent-weak results
BM25 + TF-IDF	Combines BM25 with TF-IDF cosine similarity	Improves document-level text similarity	Still mostly lexical
Weighted Hybrid	Adds condition, eligibility, status, and location scoring	Best practical default; fast and explainable	Uses hand-chosen weights
Semantic Hybrid	Adds embedding-based semantic reranking	Better meaning-based matching in the top 10	Slower because embeddings are computed at query time
Evaluation Results

Evaluation setup:

Indexed local trials: 36,522
Evaluation queries: 10
Results per query: Top 10
Live API expansion: disabled for fair model comparison
Relevance labels:
2 = highly relevant: condition plus full query intent match
1 = partially relevant: condition match but missing key intent
0 = not relevant: wrong condition or unrelated trial
Retrieval model	Precision@5	Precision@10	HighlyRelevant@5	HighlyRelevant@10	nDCG@10	Avg latency
BM25 only	1.00	1.00	0.48	0.47	0.931	776 ms
BM25 + TF-IDF	1.00	1.00	0.44	0.45	0.927	695 ms
Weighted Hybrid	1.00	1.00	0.58	0.53	0.910	722 ms
Semantic Hybrid	1.00	1.00	0.54	0.58	0.907	3,177 ms
Main Finding

All models achieved Precision@5 = 1.00 and Precision@10 = 1.00, meaning they were all good at finding trials in the correct medical area.

However, the stricter metric HighlyRelevant@k shows the real difference.

Weighted Hybrid is the best practical default because it has the best HighlyRelevant@5, good latency, and clear explainability.

Semantic Hybrid is the advanced option because it improves HighlyRelevant@10, but it is slower because it performs embedding-based reranking.

What Each Score Means
Score	Meaning
BM25 score	Measures exact keyword relevance
TF-IDF score	Measures vector-space document similarity
Semantic score	Measures meaning similarity using embeddings
Condition score	Checks whether the condition field matches the query
Eligibility score	Checks whether eligibility criteria match query terms
Location score	Checks whether trial locations match the user’s location
Status score	Boosts recruiting trials
Final score	Combined ranking score used to order results

This makes the search engine explainable instead of a black-box ranked list.

System Architecture
ClinicalTrials.gov API v2
        |
        v
Data ingestion script
        |
        v
Local trial index
        |
        v
FastAPI backend
        |
        v
Retrieval pipeline
BM25 / TF-IDF / Weighted Hybrid / Semantic Hybrid
        |
        v
Next.js frontend
        |
        v
Explainable ranked results
Tech Stack
Backend
Python
FastAPI
Pydantic
scikit-learn
rank-bm25
sentence-transformers
ClinicalTrials.gov API v2
Frontend
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Lucide React icons
Evaluation
Custom Python evaluation script
Precision@5
Precision@10
HighlyRelevant@5
HighlyRelevant@10
nDCG@10
latency measurement
Project Structure
trialfinder/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   ├── search_engine.py
│   │   │   └── clinicaltrials_client.py
│   │   ├── scripts/
│   │   │   ├── ingest_trials.py
│   │   │   └── evaluate_search.py
│   │   └── requirements.txt
│   │
│   └── web/
│       ├── src/
│       │   ├── app/
│       │   │   └── page.tsx
│       │   ├── components/
│       │   └── lib/
│       │       └── api.ts
│       └── package.json
│
├── data/
│   └── processed/
│       ├── evaluation_results_models.csv
│       └── evaluation_summary_models.md
│
├── docs/
│   ├── TrialFinder_Report.pdf
│   ├── TrialFinder_Report.docx
│   └── presentation files
│
├── README.md
└── .gitignore
Important Dataset Note

The generated local index file is:

data/processed/trials.json

This file is excluded from GitHub because it is larger than the normal GitHub file-size limit.

To regenerate it locally, run the ingestion script:

cd apps/api
source .venv/bin/activate
python scripts/ingest_trials.py

Expected output:

Saved 36522 unique trials to data/processed/trials.json
How to Run Locally

Open two terminal windows.

Terminal 1: Backend API
cd ~/trialfinder/apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

Backend links:

http://127.0.0.1:8000
http://127.0.0.1:8000/docs
Terminal 2: Frontend UI
cd ~/trialfinder/apps/web
npm install
npm run dev

Frontend link:

http://localhost:3000

If Next.js shows a Turbopack/native binding issue on Mac, run:

npm pkg set scripts.dev="next dev --webpack"
npm run dev
API Example

Example POST request:

curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "lung cancer immunotherapy trials in california",
    "status": "RECRUITING",
    "top_k": 10,
    "include_live_api": false,
    "retrieval_mode": "weighted"
  }'

Supported retrieval modes:

bm25
bm25_tfidf
weighted
semantic_hybrid
Running Evaluation

Run the evaluation script:

cd apps/api
source .venv/bin/activate
python scripts/evaluate_search.py

Generated outputs:

data/processed/evaluation_results_models.csv
data/processed/evaluation_summary_models.md

The evaluation compares:

BM25 only
BM25 + TF-IDF
Weighted Hybrid
Semantic Hybrid
Why Weighted Hybrid Is the Default

Weighted Hybrid is the best practical default because it balances:

relevance
speed
explainability
structured medical-field matching

It improves top-5 intent relevance over BM25 while staying close to lexical retrieval latency.

Semantic Hybrid is still included because it improves deeper intent matching in the top 10, but it is slower because embeddings are computed during search.

Future Work
AI Consensus Layer

A future version of TrialFinder could add an AI Consensus panel above the ranked list.

Instead of forcing users to inspect every result one by one, the system could summarize the top trials and recommend the strongest candidate.

Example:

AI Consensus:
Best candidate: NCT06926179 — Neoadjuvant/Induction Immunotherapy in NSCLC

Why:
This trial strongly matches lung cancer and immunotherapy intent.
BM25 and TF-IDF agree on text relevance, while semantic similarity confirms treatment intent.

Possible bias:
The system may under-rank California trials if they are screening-focused and over-rank treatment trials outside California.

Action:
Review the official ClinicalTrials.gov page and confirm eligibility with a clinician.
Other Future Improvements
Pre-compute embeddings for all trials
Store embeddings in FAISS or pgvector
Add patient-profile matching
Add age, sex, prior-treatment, and exclusion-criteria filtering
Add plain-English eligibility summaries
Evaluate with clinician-reviewed relevance labels
Expand to more international trial registries
Safety Disclaimer

TrialFinder is a search and discovery aid, not a medical decision system.

It does not determine whether a patient is eligible for a trial. Final eligibility and medical decisions must be confirmed by clinicians, trial coordinators, or the official ClinicalTrials.gov trial record.

Course Information
Item	Details
Course	CECS 429/529 Search Engine Technology
Project	Final Project
Student	Gyanendra Pandey
Institution	California State University, Long Beach
Target venue	SIGIR 2026 Demo Track
References
Robertson, S., & Zaragoza, H. The Probabilistic Relevance Framework: BM25 and Beyond.
Reimers, N., & Gurevych, I. Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.
U.S. National Library of Medicine. ClinicalTrials.gov.
U.S. National Library of Medicine. ClinicalTrials.gov API v2.
FastAPI Documentation.
Next.js Documentation.
scikit-learn Documentation.
SentenceTransformers Documentation.
