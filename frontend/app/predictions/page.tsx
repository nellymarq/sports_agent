"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

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

function ConfidenceBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    "Very High": "bg-emerald-500/20 text-emerald-400",
    High: "bg-blue-500/20 text-blue-400",
    Medium: "bg-amber-500/20 text-amber-400",
    Low: "bg-red-500/20 text-red-400",
  };
  const color = colors[tier] || "bg-slate-500/20 text-slate-400";

  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${color}`}>
      {tier}
    </span>
  );
}

function ResultBadge({ correct }: { correct: boolean | null }) {
  if (correct === null)
    return (
      <span className="text-[10px] bg-slate-500/20 text-slate-400 px-1.5 py-0.5 rounded font-medium">
        PENDING
      </span>
    );
  if (correct)
    return (
      <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-medium">
        CORRECT
      </span>
    );
  return (
    <span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-medium">
      WRONG
    </span>
  );
}

function RecordResultForm({
  pred,
  onRecorded,
}: {
  pred: Prediction;
  onRecorded: (updated: Prediction) => void;
}) {
  const [winner, setWinner] = useState("");
  const [method, setMethod] = useState("");
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

  return (
    <div className="mt-3 pt-3 border-t border-slate-800/50">
      <p className="text-[10px] text-slate-500 mb-2">Record actual result:</p>
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <label className="text-[10px] text-slate-500 block mb-0.5">Winner</label>
          <select
            value={winner}
            onChange={(e) => setWinner(e.target.value)}
            className="w-full rounded bg-black/40 border border-slate-800 px-2 py-1 text-xs outline-none focus:border-accent"
          >
            <option value="">Select winner...</option>
            <option value={pred.fighter_a}>{pred.fighter_a}</option>
            <option value={pred.fighter_b}>{pred.fighter_b}</option>
            <option value="Draw">Draw</option>
            <option value="No Contest">No Contest</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="text-[10px] text-slate-500 block mb-0.5">Method</label>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="w-full rounded bg-black/40 border border-slate-800 px-2 py-1 text-xs outline-none focus:border-accent"
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
        <Button
          onClick={handleSubmit}
          disabled={!winner || submitting}
          className="text-xs px-3 py-1"
        >
          {submitting ? "..." : "Save"}
        </Button>
      </div>
    </div>
  );
}

function PredictionCard({
  pred,
  onResultRecorded,
}: {
  pred: Prediction;
  onResultRecorded: (id: string, updated: Prediction) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const prob = (pred.win_probability * 100).toFixed(0);
  const date = new Date(pred.timestamp * 1000).toLocaleDateString();

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium">
            {pred.fighter_a} vs {pred.fighter_b}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            {pred.event_id.replace(/_/g, " ").toUpperCase()} &middot; {date}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <ConfidenceBadge tier={pred.confidence_tier} />
          <ResultBadge correct={pred.correct} />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
        <div>
          <p className="text-slate-500">Predicted</p>
          <p className="font-medium text-accent">{pred.predicted_winner}</p>
        </div>
        <div>
          <p className="text-slate-500">Probability</p>
          <p className="font-medium">{prob}%</p>
        </div>
        <div>
          <p className="text-slate-500">Method Lean</p>
          <p className="font-medium">{pred.method_lean || "N/A"}</p>
        </div>
      </div>

      {pred.actual_winner && (
        <div className="mt-2 pt-2 border-t border-slate-800/50 text-xs">
          <span className="text-slate-500">Result: </span>
          <span className="font-medium">
            {pred.actual_winner}
            {pred.actual_method ? ` by ${pred.actual_method}` : ""}
          </span>
        </div>
      )}

      {/* Record result for pending predictions */}
      {pred.correct === null && !showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="mt-2 text-[10px] text-accent hover:underline"
        >
          Record result
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
    </Card>
  );
}

export default function PredictionsPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "resolved" | "pending">("all");

  const fetchPredictions = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const params = filter === "resolved" ? "?resolved_only=true" : "";

    fetch(`${apiUrl}/predictions${params}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((d) => {
        let preds = d.predictions || [];
        if (filter === "pending") {
          preds = preds.filter((p: Prediction) => p.correct === null);
        }
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

  const stats = {
    total: predictions.length,
    correct: predictions.filter((p) => p.correct === true).length,
    wrong: predictions.filter((p) => p.correct === false).length,
    pending: predictions.filter((p) => p.correct === null).length,
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Prediction History</h1>
        <Link href="/" className="text-xs text-accent hover:underline">
          &larr; Home
        </Link>
      </div>

      {/* Stats bar */}
      <Card className="p-4">
        <div className="grid grid-cols-4 gap-3 text-center text-xs">
          <div>
            <p className="text-slate-500">Total</p>
            <p className="text-lg font-semibold">{stats.total}</p>
          </div>
          <div>
            <p className="text-slate-500">Correct</p>
            <p className="text-lg font-semibold text-emerald-400">
              {stats.correct}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Wrong</p>
            <p className="text-lg font-semibold text-red-400">{stats.wrong}</p>
          </div>
          <div>
            <p className="text-slate-500">Pending</p>
            <p className="text-lg font-semibold text-slate-400">
              {stats.pending}
            </p>
          </div>
        </div>
      </Card>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {(["all", "resolved", "pending"] as const).map((f) => (
          <button
            key={f}
            onClick={() => {
              setLoading(true);
              setFilter(f);
            }}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              filter === f
                ? "border-accent bg-accent/10 text-accent"
                : "border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {loading && (
        <Card className="p-5">
          <p className="text-sm text-slate-400 animate-pulse">
            Loading predictions...
          </p>
        </Card>
      )}

      {error && (
        <Card className="p-5 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {!loading && !error && predictions.length === 0 && (
        <Card className="p-5">
          <p className="text-sm text-slate-400">
            No predictions yet. Run a matchup analysis to generate predictions.
          </p>
        </Card>
      )}

      <div className="space-y-3">
        {predictions.map((pred) => (
          <PredictionCard
            key={pred.id}
            pred={pred}
            onResultRecorded={handleResultRecorded}
          />
        ))}
      </div>
    </div>
  );
}
