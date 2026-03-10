"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";

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

function PredictionCard({ pred }: { pred: Prediction }) {
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
    </Card>
  );
}

export default function PredictionsPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "resolved" | "pending">("all");

  useEffect(() => {
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
  }, [filter]);

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
          <PredictionCard key={pred.id} pred={pred} />
        ))}
      </div>
    </div>
  );
}
