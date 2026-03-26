"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

type Prediction = {
  id: string;
  event_id: string;
  fighter_a: string;
  fighter_b: string;
  predicted_winner: string;
  win_probability: number;
  confidence_tier: string;
  method_lean: string;
  timestamp: number;
  actual_winner: string | null;
  actual_method: string | null;
  correct: boolean | null;
};

type FilterType = "all" | "correct" | "incorrect" | "pending";

/* ── badges ────────────────────────────────────────────── */

function ConfidenceBadge({ tier }: { tier: string }) {
  const styles: Record<string, string> = {
    "Very High":
      "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    High: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    Medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    Low: "bg-red-500/15 text-red-400 border-red-500/30",
  };
  const style =
    styles[tier] || "bg-slate-500/15 text-slate-400 border-slate-500/30";

  return (
    <span
      className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wide border ${style}`}
    >
      {tier}
    </span>
  );
}

function ResultBadge({ correct }: { correct: boolean | null }) {
  if (correct === null)
    return (
      <span className="text-[9px] bg-slate-500/15 text-slate-400 border border-slate-500/30 px-2 py-0.5 rounded-full font-bold uppercase tracking-wide">
        PENDING
      </span>
    );
  if (correct)
    return (
      <span className="text-[9px] bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-bold uppercase tracking-wide">
        CORRECT
      </span>
    );
  return (
    <span className="text-[9px] bg-red-500/15 text-red-400 border border-red-500/30 px-2 py-0.5 rounded-full font-bold uppercase tracking-wide">
      WRONG
    </span>
  );
}

/* ── record result form ────────────────────────────────── */

function RecordResultForm({
  pred,
  onRecorded,
}: {
  pred: Prediction;
  onRecorded: (updated: Prediction) => void;
}) {
  const [winner, setWinner] = useState("");
  const [method, setMethod] = useState("");
  const [round, setRound] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = () => {
    if (!winner) return;
    setSubmitting(true);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: pred.event_id,
        fighter_a: pred.fighter_a,
        fighter_b: pred.fighter_b,
        actual_winner: winner,
        actual_method: method,
        actual_round: round ? parseInt(round) : null,
      }),
    })
      .then((res) => res.json())
      .then((d) => {
        if (d.status === "ok" && d.prediction) {
          onRecorded(d.prediction);
        }
      })
      .catch(() => {})
      .finally(() => setSubmitting(false));
  };

  const selectClass =
    "w-full rounded-lg bg-black/40 border border-slate-700/60 px-2.5 py-1.5 text-xs outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/20 transition-all";

  return (
    <div className="mt-3 pt-3 border-t border-slate-800/40">
      <p className="text-[10px] text-slate-500 mb-2 font-medium uppercase tracking-wider">
        Record actual result
      </p>
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <label className="text-[10px] text-slate-600 block mb-0.5">
            Winner
          </label>
          <select
            value={winner}
            onChange={(e) => setWinner(e.target.value)}
            className={selectClass}
          >
            <option value="">Select winner...</option>
            <option value={pred.fighter_a}>{pred.fighter_a}</option>
            <option value={pred.fighter_b}>{pred.fighter_b}</option>
            <option value="Draw">Draw</option>
            <option value="No Contest">No Contest</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="text-[10px] text-slate-600 block mb-0.5">
            Method
          </label>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className={selectClass}
          >
            <option value="">Select method...</option>
            <option value="KO/TKO">KO/TKO</option>
            <option value="Submission">Submission</option>
            <option value="Decision - Unanimous">Decision - Unanimous</option>
            <option value="Decision - Split">Decision - Split</option>
            <option value="Decision - Majority">Decision - Majority</option>
            <option value="DQ">DQ</option>
          </select>
        </div>
        <div className="w-16">
          <label className="text-[10px] text-slate-600 block mb-0.5">
            Round
          </label>
          <select
            value={round}
            onChange={(e) => setRound(e.target.value)}
            className={selectClass}
          >
            <option value="">{"\u2014"}</option>
            <option value="1">R1</option>
            <option value="2">R2</option>
            <option value="3">R3</option>
            <option value="4">R4</option>
            <option value="5">R5</option>
          </select>
        </div>
        <Button
          onClick={handleSubmit}
          disabled={!winner || submitting}
          size="sm"
          className="text-xs px-3 py-1.5"
        >
          {submitting ? "..." : "Save"}
        </Button>
      </div>
    </div>
  );
}

/* ── probability bar ───────────────────────────────────── */

function ProbabilityBar({
  probability,
  fighterA,
  fighterB,
  predictedWinner,
}: {
  probability: number;
  fighterA: string;
  fighterB: string;
  predictedWinner: string;
}) {
  const pct = probability * 100;
  const isA = predictedWinner === fighterA;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className={isA ? "text-accent font-semibold" : "text-slate-500"}>
          {fighterA}
        </span>
        <span className={!isA ? "text-accent font-semibold" : "text-slate-500"}>
          {fighterB}
        </span>
      </div>
      <div className="flex h-1.5 rounded-full overflow-hidden bg-slate-800/80">
        <div
          className={`rounded-l-full transition-all duration-500 ${
            isA
              ? "bg-gradient-to-r from-accent to-accent/60"
              : "bg-slate-600/40"
          }`}
          style={{ width: isA ? `${pct}%` : `${100 - pct}%` }}
        />
        <div
          className={`rounded-r-full transition-all duration-500 ${
            !isA
              ? "bg-gradient-to-l from-accent to-accent/60"
              : "bg-slate-600/40"
          }`}
          style={{ width: isA ? `${100 - pct}%` : `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-[9px] text-slate-600 font-mono">
        <span>{isA ? `${pct.toFixed(0)}%` : `${(100 - pct).toFixed(0)}%`}</span>
        <span>{!isA ? `${pct.toFixed(0)}%` : `${(100 - pct).toFixed(0)}%`}</span>
      </div>
    </div>
  );
}

/* ── prediction card ───────────────────────────────────── */

function PredictionCard({
  pred,
  onResultRecorded,
}: {
  pred: Prediction;
  onResultRecorded: (id: string, updated: Prediction) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const prob = (pred.win_probability * 100).toFixed(0);
  const date = new Date(pred.timestamp * 1000).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const borderColor =
    pred.correct === true
      ? "border-l-emerald-500/60"
      : pred.correct === false
      ? "border-l-red-500/60"
      : "border-l-slate-700/60";

  return (
    <Card
      variant="glass"
      className={`overflow-hidden border-l-2 ${borderColor} hover:border-accent/20 transition-all duration-300`}
    >
      <div
        className="p-5 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Top row: fighters + badges */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-bold text-slate-100">
                {pred.fighter_a}
              </p>
              <span className="text-[10px] font-bold text-slate-600 uppercase">
                vs
              </span>
              <p className="text-sm font-bold text-slate-100">
                {pred.fighter_b}
              </p>
            </div>
            <p className="text-[10px] text-slate-600 mt-0.5 font-mono">
              {pred.event_id.replace(/_/g, " ").toUpperCase()} &middot; {date}
            </p>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <ConfidenceBadge tier={pred.confidence_tier} />
            <ResultBadge correct={pred.correct} />
          </div>
        </div>

        {/* Prediction summary row */}
        <div className="mt-3 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500 uppercase">Pick:</span>
            <span className="text-sm font-bold text-accent">
              {pred.predicted_winner}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-slate-500 uppercase">Prob:</span>
            <span className="text-sm font-bold font-mono text-slate-200">
              {prob}%
            </span>
          </div>
          {pred.method_lean && pred.method_lean !== "N/A" && (
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-slate-500 uppercase">
                Method:
              </span>
              <span className="text-xs text-slate-300">{pred.method_lean}</span>
            </div>
          )}
        </div>

        {/* Actual result if available */}
        {pred.actual_winner && (
          <div className="mt-2 pt-2 border-t border-slate-800/30 flex items-center gap-2 text-xs">
            <span className="text-slate-500">Result:</span>
            <span
              className={`font-semibold ${
                pred.correct ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {pred.actual_winner}
              {pred.actual_method ? ` by ${pred.actual_method}` : ""}
            </span>
          </div>
        )}

        {/* Expand indicator */}
        <div className="flex items-center justify-end mt-2">
          <span
            className={`text-[10px] text-slate-600 transition-transform duration-200 inline-block ${
              expanded ? "rotate-180" : ""
            }`}
          >
            {"\u25BC"}
          </span>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-800/30 pt-4 space-y-4 animate-slide-up">
          {/* Probability visualization */}
          <ProbabilityBar
            probability={pred.win_probability}
            fighterA={pred.fighter_a}
            fighterB={pred.fighter_b}
            predictedWinner={pred.predicted_winner}
          />

          {/* Detail grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg bg-black/20 border border-slate-800/40 p-3">
              <p className="text-[9px] text-slate-600 uppercase tracking-wider font-medium">
                Predicted Winner
              </p>
              <p className="text-xs font-bold text-accent mt-0.5">
                {pred.predicted_winner}
              </p>
            </div>
            <div className="rounded-lg bg-black/20 border border-slate-800/40 p-3">
              <p className="text-[9px] text-slate-600 uppercase tracking-wider font-medium">
                Win Probability
              </p>
              <p className="text-xs font-bold text-slate-200 mt-0.5 font-mono">
                {prob}%
              </p>
            </div>
            <div className="rounded-lg bg-black/20 border border-slate-800/40 p-3">
              <p className="text-[9px] text-slate-600 uppercase tracking-wider font-medium">
                Confidence
              </p>
              <p className="text-xs font-bold text-slate-200 mt-0.5">
                {pred.confidence_tier}
              </p>
            </div>
            <div className="rounded-lg bg-black/20 border border-slate-800/40 p-3">
              <p className="text-[9px] text-slate-600 uppercase tracking-wider font-medium">
                Method Lean
              </p>
              <p className="text-xs font-bold text-slate-200 mt-0.5">
                {pred.method_lean || "N/A"}
              </p>
            </div>
          </div>

          {/* Quick links */}
          <div className="flex gap-2">
            <Link
              href={`/compare?a=${encodeURIComponent(pred.fighter_a)}&b=${encodeURIComponent(pred.fighter_b)}`}
              className="text-[10px] px-3 py-1.5 rounded-lg bg-surface/60 text-slate-400 border border-slate-700/50 hover:text-accent hover:border-accent/30 transition-all font-medium"
              onClick={(e) => e.stopPropagation()}
            >
              Compare Fighters
            </Link>
            <Link
              href={`/analyze?q=${encodeURIComponent(`${pred.fighter_a} vs ${pred.fighter_b} breakdown`)}`}
              className="text-[10px] px-3 py-1.5 rounded-lg bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-all font-medium"
              onClick={(e) => e.stopPropagation()}
            >
              Deep Analysis
            </Link>
          </div>

          {/* Record result form */}
          {pred.correct === null && !showForm && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowForm(true);
              }}
              className="text-[10px] text-accent hover:text-accent/80 transition-colors font-medium"
            >
              + Record result
            </button>
          )}

          {showForm && pred.correct === null && (
            <RecordResultForm
              pred={pred}
              onRecorded={(updated) => {
                onResultRecorded(pred.id, updated);
                setShowForm(false);
              }}
            />
          )}
        </div>
      )}
    </Card>
  );
}

/* ── loading skeleton ──────────────────────────────────── */

function PredictionSkeleton() {
  return (
    <div className="rounded-xl border border-slate-800 bg-surface/60 backdrop-blur p-5 space-y-3 animate-pulse border-l-2 border-l-slate-700/40">
      <div className="flex justify-between">
        <div className="space-y-2">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-2 w-32" />
        </div>
        <div className="flex gap-1.5">
          <Skeleton className="h-4 w-14 rounded-full" />
          <Skeleton className="h-4 w-16 rounded-full" />
        </div>
      </div>
      <div className="flex gap-4">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-20" />
      </div>
    </div>
  );
}

/* ── page ──────────────────────────────────────────────── */

export default function PredictionsPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>("all");

  const fetchPredictions = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const params = filter === "correct" || filter === "incorrect" ? "?resolved_only=true" : "";

    fetch(`${apiUrl}/predictions${params}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((d) => {
        let preds: Prediction[] = d.predictions || [];

        // Apply client-side filter
        if (filter === "correct") {
          preds = preds.filter((p) => p.correct === true);
        } else if (filter === "incorrect") {
          preds = preds.filter((p) => p.correct === false);
        } else if (filter === "pending") {
          preds = preds.filter((p) => p.correct === null);
        }

        // Sort by date newest first
        preds.sort((a, b) => b.timestamp - a.timestamp);

        setPredictions(preds);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPredictions();
  }, [filter]);

  const handleResultRecorded = (id: string, updated: Prediction) => {
    setPredictions((prev) =>
      prev.map((p) => (p.id === id ? { ...p, ...updated } : p))
    );
  };

  // Compute stats from ALL predictions (not filtered)
  const [allPredictions, setAllPredictions] = useState<Prediction[]>([]);
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/predictions`)
      .then((res) => (res.ok ? res.json() : { predictions: [] }))
      .then((d) => setAllPredictions(d.predictions || []))
      .catch(() => {});
  }, []);

  const stats = {
    total: allPredictions.length,
    correct: allPredictions.filter((p) => p.correct === true).length,
    wrong: allPredictions.filter((p) => p.correct === false).length,
    pending: allPredictions.filter((p) => p.correct === null).length,
  };

  const accuracy =
    stats.correct + stats.wrong > 0
      ? ((stats.correct / (stats.correct + stats.wrong)) * 100).toFixed(1)
      : null;

  // Calculate streak
  const resolvedSorted = allPredictions
    .filter((p) => p.correct !== null)
    .sort((a, b) => b.timestamp - a.timestamp);
  let streak = 0;
  let streakType: "W" | "L" | null = null;
  for (const p of resolvedSorted) {
    if (streakType === null) {
      streakType = p.correct ? "W" : "L";
      streak = 1;
    } else if ((streakType === "W" && p.correct) || (streakType === "L" && !p.correct)) {
      streak++;
    } else {
      break;
    }
  }

  const filters: { key: FilterType; label: string; count?: number }[] = [
    { key: "all", label: "All", count: allPredictions.length },
    { key: "correct", label: "Correct", count: stats.correct },
    { key: "incorrect", label: "Incorrect", count: stats.wrong },
    { key: "pending", label: "Pending", count: stats.pending },
  ];

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 space-y-6">
      {/* ── Header ────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Predictions</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Track and verify model predictions
          </p>
        </div>
        <div className="flex gap-3 items-center">
          <Link
            href="/dashboard"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-all"
          >
            Dashboard
          </Link>
          <Link
            href="/"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-all"
          >
            Home
          </Link>
        </div>
      </div>

      {/* ── Stats Summary ─────────────────────────────────── */}
      <Card variant="glass" className="p-5">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          {/* Accuracy hero */}
          <div className="col-span-2 sm:col-span-1 flex flex-col items-center justify-center">
            <div
              className={`text-3xl font-black ${
                accuracy
                  ? parseFloat(accuracy) >= 60
                    ? "text-emerald-400"
                    : parseFloat(accuracy) >= 50
                    ? "text-amber-400"
                    : "text-red-400"
                  : "text-slate-500"
              }`}
            >
              {accuracy ? `${accuracy}%` : "\u2014"}
            </div>
            <p className="text-[9px] text-slate-500 uppercase tracking-wider font-medium mt-0.5">
              Accuracy
            </p>
          </div>

          {/* Other stats */}
          <div className="text-center">
            <p className="text-lg font-bold text-slate-200">{stats.total}</p>
            <p className="text-[9px] text-slate-500 uppercase tracking-wider font-medium">
              Total
            </p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-emerald-400">{stats.correct}</p>
            <p className="text-[9px] text-slate-500 uppercase tracking-wider font-medium">
              Correct
            </p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-red-400">{stats.wrong}</p>
            <p className="text-[9px] text-slate-500 uppercase tracking-wider font-medium">
              Wrong
            </p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1.5">
              {streakType && streak > 0 && (
                <span
                  className={`text-lg font-bold font-mono ${
                    streakType === "W" ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {streak}{streakType}
                </span>
              )}
            </div>
            <p className="text-[9px] text-slate-500 uppercase tracking-wider font-medium">
              Streak
            </p>
          </div>
        </div>
      </Card>

      {/* ── Filter Bar ────────────────────────────────────── */}
      <div className="flex gap-2">
        {filters.map((f) => (
          <button
            key={f.key}
            onClick={() => {
              setLoading(true);
              setFilter(f.key);
            }}
            className={`text-xs px-4 py-2 rounded-lg border transition-all duration-200 font-medium ${
              filter === f.key
                ? "border-accent/40 bg-accent/10 text-accent shadow-[0_0_12px_rgba(0,224,255,0.1)]"
                : "border-slate-800 text-slate-500 hover:text-slate-300 hover:border-slate-700"
            }`}
          >
            {f.label}
            {f.count !== undefined && (
              <span
                className={`ml-1.5 text-[10px] font-mono ${
                  filter === f.key ? "text-accent/60" : "text-slate-600"
                }`}
              >
                {f.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Loading ───────────────────────────────────────── */}
      {loading && (
        <div className="space-y-3">
          <PredictionSkeleton />
          <PredictionSkeleton />
          <PredictionSkeleton />
        </div>
      )}

      {/* ── Error ─────────────────────────────────────────── */}
      {error && (
        <Card variant="glass" className="p-5 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {/* ── Empty State ───────────────────────────────────── */}
      {!loading && !error && predictions.length === 0 && (
        <Card variant="glass" className="p-10 text-center">
          <div className="text-4xl mb-3 opacity-30">{"\uD83C\uDFAF"}</div>
          <p className="text-sm text-slate-400 mb-1">
            {filter === "all"
              ? "No predictions yet"
              : `No ${filter} predictions`}
          </p>
          <p className="text-xs text-slate-600 mb-4">
            {filter === "all"
              ? "Run a matchup analysis to generate predictions."
              : "Try a different filter or analyze more matchups."}
          </p>
          {filter === "all" && (
            <Link
              href="/analyze"
              className="inline-block text-xs px-4 py-2 rounded-lg bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-all font-medium"
            >
              Analyze a Matchup
            </Link>
          )}
        </Card>
      )}

      {/* ── Prediction List ───────────────────────────────── */}
      {!loading && (
        <div className="space-y-3">
          {predictions.map((pred) => (
            <PredictionCard
              key={pred.id}
              pred={pred}
              onResultRecorded={handleResultRecorded}
            />
          ))}
        </div>
      )}

      {/* ── Results count ─────────────────────────────────── */}
      {!loading && predictions.length > 0 && (
        <p className="text-center text-[10px] text-slate-600 pb-4">
          Showing {predictions.length} prediction
          {predictions.length !== 1 ? "s" : ""}
          {filter !== "all" && ` (filtered: ${filter})`}
        </p>
      )}
    </div>
  );
}
