"use client";

import { useState } from "react";
import {
  Activity,
  Brain,
  Database,
  ExternalLink,
  FileText,
  Filter,
  Loader2,
  MapPin,
  Scale,
  Search,
  Sparkles,
} from "lucide-react";

import {
  searchTrials,
  type RetrievalMode,
  type SearchResponse,
  type SearchResult,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const exampleQueries = [
  "alzheimer trials for older adults",
  "lung cancer immunotherapy trials in california",
  "glioblastoma trials",
  "liver disease",
  "Migraine and Headache",
];

const retrievalModes: Array<{
  value: RetrievalMode;
  label: string;
  description: string;
}> = [
  { value: "bm25", label: "BM25 only", description: "Keyword baseline" },
  { value: "bm25_tfidf", label: "BM25 + TF-IDF", description: "Keyword + Vector Space" },
  { value: "weighted", label: "Weighted hybrid", description: "Lexical + structured fields" },
  { value: "semantic_hybrid", label: "Semantic hybrid", description: "Lexical + structured + embeddings" },
];

const methodChips = [
  { icon: Search, label: "BM25", description: "Lexical relevance" },
  { icon: FileText, label: "TF-IDF", description: "Cosine similarity" },
  { icon: Filter, label: "Condition", description: "Medical concept matching" },
  { icon: Scale, label: "Weighted", description: "Final rank formula" },
  { icon: Brain, label: "Semantic", description: "Meaning-based reranking" },
];

function scorePercent(score: number) {
  return Math.round(score * 100);
}

function formatSearchMode(mode?: string | null) {
  if (!mode) return "Local Index";
  return mode.split("_").map((word) => word[0]?.toUpperCase() + word.slice(1)).join(" ");
}

function getRetrievalModeLabel(mode?: string | null) {
  return retrievalModes.find((item) => item.value === mode)?.label || "Weighted hybrid";
}

function getScoreLabel(score: number) {
  if (score >= 0.75) return "Strong match";
  if (score >= 0.5) return "Good match";
  if (score >= 0.3) return "Partial match";
  return "Weak match";
}

function getScoreColor(score: number) {
  if (score >= 0.75) return "text-emerald-600";
  if (score >= 0.5) return "text-amber-600";
  if (score >= 0.3) return "text-orange-500";
  return "text-slate-400";
}

function formatStatus(status: string) {
  return status
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getStatusStyle(status: string): React.CSSProperties {
  const s = (status || "").toUpperCase();
  if (s === "RECRUITING")
    return { background: "rgba(16,185,129,0.1)", color: "#059669", border: "1px solid rgba(16,185,129,0.2)" };
  if (s === "NOT_YET_RECRUITING")
    return { background: "rgba(245,158,11,0.1)", color: "#d97706", border: "1px solid rgba(245,158,11,0.2)" };
  if (s === "ACTIVE_NOT_RECRUITING")
    return { background: "rgba(59,130,246,0.1)", color: "#2563eb", border: "1px solid rgba(59,130,246,0.2)" };
  if (s === "COMPLETED")
    return { background: "rgba(148,163,184,0.1)", color: "#64748b", border: "1px solid rgba(148,163,184,0.25)" };
  if (s === "TERMINATED" || s === "WITHDRAWN")
    return { background: "rgba(239,68,68,0.08)", color: "#dc2626", border: "1px solid rgba(239,68,68,0.15)" };
  return { background: "rgba(148,163,184,0.1)", color: "#64748b", border: "1px solid rgba(148,163,184,0.2)" };
}

function getLocationPreview(result: SearchResult) {
  const locations = result.trial.locations || [];
  if (locations.length === 0) return "Location not listed";
  const first = locations[0];
  const cityState = [first.city, first.state].filter(Boolean).join(", ");
  if (locations.length === 1) return cityState || "Location listed";
  return `${cityState || "Multiple locations"} +${locations.length - 1} more`;
}

function getTopLocationMatches(result: SearchResult) {
  const locations = result.trial.locations || [];
  return locations
    .slice(0, 2)
    .map((loc) => [loc.facility, loc.city, loc.state].filter(Boolean).join(", "))
    .filter(Boolean);
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = scorePercent(value);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-500">{label}</span>
        <span className="text-xs font-bold text-slate-700">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: pct >= 75
              ? "linear-gradient(90deg, #059669, #10b981)"
              : pct >= 50
              ? "linear-gradient(90deg, #d97706, #f59e0b)"
              : pct >= 30
              ? "linear-gradient(90deg, #D85F2F, #f97316)"
              : "linear-gradient(90deg, #94a3b8, #cbd5e1)",
          }}
        />
      </div>
    </div>
  );
}

function CompactMethodsBar() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-[#D85F2F]" />
        <span className="text-sm font-semibold text-slate-800">Retrieval pipeline</span>
        <span className="text-sm text-slate-400">—</span>
        <span className="text-sm text-slate-500">Comparing four IR methods across every query</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {methodChips.map((method) => {
          const Icon = method.icon;
          return (
            <div
              key={method.label}
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs transition-colors hover:border-[#D85F2F]/40 hover:bg-orange-50"
              title={method.description}
            >
              <div className="flex h-5 w-5 items-center justify-center rounded-md bg-[#D85F2F]/10">
                <Icon className="h-3 w-3 text-[#D85F2F]" />
              </div>
              <span className="font-semibold text-slate-700">{method.label}</span>
              <span className="hidden text-slate-400 md:inline">· {method.description}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon?: React.ReactNode;
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-1 flex items-center gap-2">
        {icon && <div className="text-slate-400">{icon}</div>}
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</span>
      </div>
      <div className="text-lg font-bold text-slate-800">{value ?? "—"}</div>
    </div>
  );
}

function ResultCard({ result, rank }: { result: SearchResult; rank: number }) {
  const finalPct = scorePercent(result.score.final_score);
  const scoreColor = getScoreColor(result.score.final_score);

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      {/* Top accent bar based on score */}
      <div
        className="h-1 w-full"
        style={{
          background:
            finalPct >= 75
              ? "linear-gradient(90deg, #059669, #34d399)"
              : finalPct >= 50
              ? "linear-gradient(90deg, #d97706, #fbbf24)"
              : "linear-gradient(90deg, #D85F2F, #fb923c)",
        }}
      />

      <div className="p-6">
        {/* Header row */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex-1 space-y-3 min-w-0">
            {/* Rank + badges */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Rank pill */}
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 26,
                  height: 26,
                  borderRadius: "50%",
                  background: "#0f172a",
                  color: "#fff",
                  fontSize: 11,
                  fontWeight: 700,
                  fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                  flexShrink: 0,
                }}
              >
                {rank}
              </span>

              {/* Status — color-coded, human-readable */}
              <span
                style={{
                  ...getStatusStyle(result.trial.status),
                  borderRadius: 20,
                  padding: "3px 10px",
                  fontSize: 12,
                  fontWeight: 500,
                  fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                  letterSpacing: "-0.01em",
                }}
              >
                {formatStatus(result.trial.status)}
              </span>

              {/* Phase */}
              {result.trial.phase && (
                <span
                  style={{
                    borderRadius: 20,
                    border: "1px solid rgba(148,163,184,0.25)",
                    background: "rgba(148,163,184,0.07)",
                    color: "#64748b",
                    padding: "3px 10px",
                    fontSize: 12,
                    fontWeight: 500,
                    fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                  }}
                >
                  {result.trial.phase}
                </span>
              )}

              {/* Source */}
              <span
                style={{
                  borderRadius: 20,
                  background: "rgba(216,95,47,0.08)",
                  color: "#D85F2F",
                  padding: "3px 10px",
                  fontSize: 12,
                  fontWeight: 500,
                  fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                }}
              >
                {result.source === "local_index" ? "Local Index" : "Live API"}
              </span>
            </div>

            {/* Title */}
            <h3 className="text-lg font-bold leading-snug text-slate-900 max-w-2xl">
              {result.trial.title}
            </h3>

            {/* NCT ID + location */}
            <p className="text-sm text-slate-400">
              <span className="font-mono font-medium text-slate-500">{result.trial.nct_id}</span>
              {" · "}
              {getLocationPreview(result)}
            </p>

            {/* Location badges */}
            {getTopLocationMatches(result).length > 0 && (
              <div className="flex flex-wrap gap-2">
                {getTopLocationMatches(result).map((location) => (
                  <span
                    key={location}
                    className="flex items-center gap-1.5 rounded-xl bg-slate-100 px-3 py-1 text-xs text-slate-600"
                  >
                    <MapPin className="h-3 w-3 text-slate-400" />
                    {location}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Score dial */}
          <div className="flex flex-col items-center rounded-2xl border border-slate-200 bg-slate-50 px-6 py-4 text-center shrink-0">
            <div className={`text-4xl font-black tabular-nums ${scoreColor}`}>
              {finalPct}
              <span className="text-xl">%</span>
            </div>
            <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
              Match score
            </div>
            <div
              className={`mt-2 rounded-full px-3 py-0.5 text-[11px] font-semibold ${
                finalPct >= 75
                  ? "bg-emerald-100 text-emerald-700"
                  : finalPct >= 50
                  ? "bg-amber-100 text-amber-700"
                  : "bg-orange-100 text-orange-700"
              }`}
            >
              {getScoreLabel(result.score.final_score)}
            </div>
          </div>
        </div>

        {/* Summary */}
        <p className="mt-4 line-clamp-2 text-sm leading-relaxed text-slate-500">
          {result.trial.summary || "No summary available."}
        </p>

        {/* Score grid */}
        <div className="mt-5 grid grid-cols-2 gap-3 rounded-2xl bg-slate-50 p-4 md:grid-cols-3">
          <ScoreBar label="BM25" value={result.score.bm25_score} />
          <ScoreBar label="TF-IDF" value={result.score.tfidf_score} />
          <ScoreBar label="Semantic" value={result.score.semantic_score ?? 0} />
          <ScoreBar label="Condition" value={result.score.condition_score} />
          <ScoreBar label="Eligibility" value={result.score.eligibility_score} />
          <ScoreBar label="Location" value={result.score.location_score} />
        </div>

        {/* Explanation */}
        <div className="mt-4 rounded-xl border border-slate-100 bg-white p-4">
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Why this result ranked here
          </h4>
          <ul className="grid gap-1.5 text-sm text-slate-600 md:grid-cols-2">
            {result.explanation.map((item, index) => (
              <li
                key={`${result.trial.nct_id}-explanation-${index}`}
                className="flex gap-2.5"
              >
                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-[#D85F2F]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Accordion for details */}
        <Accordion type="single" collapsible className="mt-2">
          <AccordionItem value="details" className="border-none">
            <AccordionTrigger className="rounded-xl px-4 py-3 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:no-underline [&>svg]:text-slate-400">
              Show trial details
            </AccordionTrigger>
            <AccordionContent className="space-y-4 px-1 pt-2">
              <div>
                <h4 className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Conditions
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {result.trial.conditions.slice(0, 12).map((condition) => (
                    <span
                      key={condition}
                      className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-600"
                    >
                      {condition}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Eligibility excerpt
                </h4>
                <p className="max-h-48 overflow-auto rounded-xl border border-slate-100 bg-slate-50 p-4 font-mono text-xs leading-relaxed text-slate-500">
                  {result.trial.eligibility || "No eligibility text available."}
                </p>
              </div>

              {result.trial.source_url && (
                <a
                  href={result.trial.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl bg-[#D85F2F]/10 px-4 py-2 text-sm font-semibold text-[#D85F2F] transition-colors hover:bg-[#D85F2F]/20"
                >
                  View on ClinicalTrials.gov
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("lung cancer immunotherapy trials in california");
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>("weighted");
  const [includeLiveApi, setIncludeLiveApi] = useState(false);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(searchQuery = query) {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError("");
    try {
      const response = await searchTrials(searchQuery, includeLiveApi, retrievalMode);
      setData(response);
      setQuery(searchQuery);
    } catch {
      setError("Search failed. Make sure the FastAPI backend is running on port 8000.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen" style={{ background: "#f8f9fb" }}>
      {/* ── Hero / Search header ── */}
      <section
        className="relative overflow-hidden"
        style={{
          background: "linear-gradient(180deg, #0a0f1a 0%, #111827 60%, #0f1621 100%)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {/* Subtle ambient glow — top right */}
        <div
          className="pointer-events-none absolute right-[-80px] top-[-80px] h-[480px] w-[480px] rounded-full"
          style={{
            background:
              "radial-gradient(circle at center, rgba(216,95,47,0.18) 0%, transparent 65%)",
            filter: "blur(1px)",
          }}
        />
        {/* Bottom left glow */}
        <div
          className="pointer-events-none absolute bottom-0 left-[10%] h-[200px] w-[340px] rounded-full"
          style={{
            background: "radial-gradient(ellipse at center, rgba(216,95,47,0.07) 0%, transparent 70%)",
          }}
        />

        <div className="relative mx-auto max-w-5xl px-8 pb-10 pt-10">
          {/* Course pill */}
          <div className="mb-8">
            <span
              className="inline-flex items-center rounded-full px-3.5 py-1 text-[11px] font-medium tracking-wide"
              style={{
                background: "rgba(255,255,255,0.055)",
                border: "1px solid rgba(255,255,255,0.09)",
                color: "rgba(255,255,255,0.45)",
                letterSpacing: "0.04em",
                fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif",
              }}
            >
              CECS 429/529 · Search Engine Technology · CSULB Spring 2026
            </span>
          </div>

          {/* Wordmark row — Apple-style: icon inline with text, vertically centered */}
          <div className="mb-2 flex items-center gap-4">
            {/* Compact monogram */}
            <div
              className="flex shrink-0 items-center justify-center rounded-[14px]"
              style={{
                width: 44,
                height: 44,
                background: "linear-gradient(145deg, #e8673a 0%, #c44f22 100%)",
                boxShadow: "0 2px 12px rgba(216,95,47,0.45), inset 0 1px 0 rgba(255,255,255,0.15)",
              }}
            >
              <span
                style={{
                  fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif",
                  fontSize: 18,
                  fontWeight: 700,
                  color: "#fff",
                  letterSpacing: "-0.5px",
                  lineHeight: 1,
                }}
              >
                T
              </span>
            </div>

            {/* Title */}
            <h1
              style={{
                fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif",
                fontSize: "clamp(32px, 5vw, 48px)",
                fontWeight: 700,
                letterSpacing: "-0.035em",
                color: "#ffffff",
                lineHeight: 1,
                margin: 0,
              }}
            >
              TrialFinder
            </h1>
          </div>

          {/* Subtitle — tight, muted */}
          <p
            className="mb-8 pl-[60px]"
            style={{
              fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif",
              fontSize: 15,
              color: "rgba(255,255,255,0.38)",
              fontWeight: 400,
              letterSpacing: "-0.01em",
            }}
          >
            An explainable hybrid clinical-trial search engine
          </p>

          {/* ── Search card ── */}
          <div
            className="rounded-2xl p-[1px]"
            style={{
              background: "linear-gradient(145deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.03) 100%)",
            }}
          >
            <div
              className="rounded-2xl p-5"
              style={{
                background: "rgba(255,255,255,0.04)",
                backdropFilter: "blur(24px)",
                WebkitBackdropFilter: "blur(24px)",
              }}
            >
              {/* Search row */}
              <div className="flex gap-2.5">
                <div className="relative flex-1">
                  <Search
                    className="absolute left-3.5 top-1/2 -translate-y-1/2"
                    style={{ width: 15, height: 15, color: "rgba(255,255,255,0.25)" }}
                  />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
                    placeholder="Search for clinical trials…"
                    style={{
                      height: 44,
                      width: "100%",
                      borderRadius: 12,
                      border: "1px solid rgba(255,255,255,0.09)",
                      background: "rgba(255,255,255,0.07)",
                      paddingLeft: 38,
                      paddingRight: 16,
                      fontSize: 15,
                      color: "#fff",
                      outline: "none",
                      fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif",
                      letterSpacing: "-0.01em",
                      transition: "border-color 0.15s, background 0.15s",
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = "rgba(216,95,47,0.5)";
                      e.target.style.background = "rgba(255,255,255,0.09)";
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = "rgba(255,255,255,0.09)";
                      e.target.style.background = "rgba(255,255,255,0.07)";
                    }}
                  />
                </div>
                <button
                  onClick={() => handleSearch()}
                  disabled={loading}
                  style={{
                    height: 44,
                    paddingLeft: 20,
                    paddingRight: 20,
                    borderRadius: 12,
                    background: loading
                      ? "rgba(216,95,47,0.5)"
                      : "linear-gradient(145deg, #e8673a 0%, #c44f22 100%)",
                    border: "none",
                    color: "#fff",
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: loading ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 7,
                    whiteSpace: "nowrap",
                    boxShadow: "0 2px 8px rgba(216,95,47,0.4), inset 0 1px 0 rgba(255,255,255,0.12)",
                    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif",
                    letterSpacing: "-0.01em",
                    transition: "opacity 0.15s, transform 0.1s",
                  }}
                  onMouseEnter={(e) => { if (!loading) (e.currentTarget.style.opacity = "0.88"); }}
                  onMouseLeave={(e) => { e.currentTarget.style.opacity = "1"; }}
                  onMouseDown={(e) => { (e.currentTarget.style.transform = "scale(0.97)"); }}
                  onMouseUp={(e) => { (e.currentTarget.style.transform = "scale(1)"); }}
                >
                  {loading
                    ? <Loader2 style={{ width: 14, height: 14 }} className="animate-spin" />
                    : <Search style={{ width: 14, height: 14 }} />
                  }
                  {includeLiveApi ? "Search + Live API" : "Search"}
                </button>
              </div>

              {/* Controls row */}
              <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]">
                {/* Retrieval model */}
                <div>
                  <div
                    className="mb-1.5"
                    style={{
                      fontSize: 11,
                      fontWeight: 500,
                      color: "rgba(255,255,255,0.35)",
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                    }}
                  >
                    Retrieval model
                  </div>
                  <Select
                    value={retrievalMode}
                    onValueChange={(value) => setRetrievalMode(value as RetrievalMode)}
                  >
                    <SelectTrigger
                      className="h-10 focus:ring-0"
                      style={{
                        borderRadius: 10,
                        border: "1px solid rgba(255,255,255,0.09)",
                        background: "rgba(255,255,255,0.07)",
                        color: "rgba(255,255,255,0.8)",
                        fontSize: 14,
                        fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                      }}
                    >
                      <SelectValue placeholder="Choose retrieval model" />
                    </SelectTrigger>
                    <SelectContent>
                      {retrievalModes.map((mode) => (
                        <SelectItem key={mode.value} value={mode.value}>
                          {mode.label} — {mode.description}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Live API toggle */}
                <div
                  className="flex items-center gap-4 md:min-w-[300px]"
                  style={{
                    borderRadius: 10,
                    border: "1px solid rgba(255,255,255,0.07)",
                    background: "rgba(255,255,255,0.04)",
                    padding: "10px 14px",
                  }}
                >
                  <div className="flex-1">
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: 500,
                        color: "rgba(255,255,255,0.75)",
                        fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                        letterSpacing: "-0.01em",
                      }}
                    >
                      Include live API
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "rgba(255,255,255,0.3)",
                        fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                      }}
                    >
                      Fetches fresh results beyond local index
                    </div>
                  </div>
                  <Switch
                    checked={includeLiveApi}
                    onCheckedChange={setIncludeLiveApi}
                    aria-label="Include live ClinicalTrials.gov API"
                  />
                </div>
              </div>

              {/* Example query chips */}
              <div className="mt-3 flex flex-wrap gap-1.5">
                {exampleQueries.map((item) => (
                  <button
                    key={item}
                    onClick={() => handleSearch(item)}
                    style={{
                      borderRadius: 8,
                      border: "1px solid rgba(255,255,255,0.08)",
                      background: "rgba(255,255,255,0.04)",
                      color: "rgba(255,255,255,0.45)",
                      fontSize: 12,
                      padding: "5px 11px",
                      cursor: "pointer",
                      fontFamily: "-apple-system, BlinkMacSystemFont, system-ui, sans-serif",
                      letterSpacing: "-0.005em",
                      transition: "all 0.15s",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(216,95,47,0.12)";
                      e.currentTarget.style.borderColor = "rgba(216,95,47,0.3)";
                      e.currentTarget.style.color = "rgba(255,255,255,0.75)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                      e.currentTarget.style.color = "rgba(255,255,255,0.45)";
                    }}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Results area ── */}
      <section className="mx-auto max-w-6xl space-y-5 px-6 py-8">
        {/* Error */}
        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {data && (
          <>
            <CompactMethodsBar />

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
              <StatCard
                icon={<Activity className="h-4 w-4" />}
                label="Search mode"
                value={formatSearchMode(data.detected_filters.search_mode)}
              />
              <StatCard
                label="Retrieval model"
                value={getRetrievalModeLabel(data.detected_filters.retrieval_mode)}
              />
              <StatCard
                icon={<Database className="h-4 w-4" />}
                label="Indexed trials"
                value={data.detected_filters.indexed_trial_count}
              />
              <StatCard
                label="Candidates"
                value={data.detected_filters.candidate_count}
              />
              <StatCard
                label="Condition detected"
                value={data.detected_filters.condition || "Not detected"}
              />
              <StatCard
                label="Live API fetched"
                value={
                  data.detected_filters.live_api_used
                    ? data.detected_filters.live_api_count ?? 0
                    : 0
                }
              />
            </div>

            {/* Semantic warning */}
            {data.detected_filters.retrieval_mode === "semantic_hybrid" &&
              !data.detected_filters.semantic_available && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                  <strong>Semantic model unavailable.</strong> Install sentence-transformers in the FastAPI environment and restart the backend.
                </div>
              )}

            {/* Results header */}
            <div className="flex items-baseline justify-between border-b border-slate-200 pb-4 pt-2">
              <div>
                <h2
                  className="text-2xl font-black text-slate-900"
                  style={{ fontFamily: "Georgia, serif" }}
                >
                  Ranked results
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  {data.results.length} results for{" "}
                  <span className="font-medium text-slate-700">"{data.query}"</span>
                </p>
              </div>
            </div>

            {/* Result cards */}
            <div className="space-y-4">
              {data.results.map((result, index) => (
                <ResultCard
                  key={result.trial.nct_id}
                  result={result}
                  rank={index + 1}
                />
              ))}
            </div>
          </>
        )}

        {/* Empty state */}
        {!data && !loading && !error && (
          <div className="flex flex-col items-center py-24 text-center">
            <div
              className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl text-2xl font-black text-white"
              style={{ background: "#D85F2F", fontFamily: "Georgia, serif" }}
            >
              T.
            </div>
            <p className="text-lg font-semibold text-slate-600">Search to get started</p>
            <p className="mt-1 max-w-sm text-sm text-slate-400">
              Enter a condition, treatment, or location above to find matching clinical trials.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}