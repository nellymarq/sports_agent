"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type ValueBet = {
  fighter_a: string;
  fighter_b: string;
  value_side: string;
  model_prob: number;
  market_implied: number;
  edge: number;
  kelly_bet: number;
  star_rating: number;
  event_id: string;
};

type ValueBetResponse = {
  status: string;
  active_predictions: number;
  odds_bouts: number;
  value_bets: ValueBet[];
  report: string;
};

function StarRating({ stars }: { stars: number }) {
  const filled = Math.min(Math.max(Math.round(stars), 0), 5);
  return (
    <span className="text-amber-400 text-xs tracking-wider">
      {"*".repeat(filled)}
      <span className="text-slate-600">{"*".repeat(5 - filled)}</span>
    </span>
  );
}

function EdgeBar({ edge }: { edge: number }) {
  const pct = Math.min(edge * 100, 30);
  const width = Math.max((pct / 30) * 100, 5);
  const color =
    edge > 0.15
      ? "bg-emerald-500"
      : edge > 0.08
      ? "bg-blue-500"
      : "bg-amber-500";

  return (
    <div className="w-full bg-slate-800 rounded-full h-1.5">
      <div
        className={`h-1.5 rounded-full ${color}`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

function ValueBetCard({ bet }: { bet: ValueBet }) {
  const edgePct = (bet.edge * 100).toFixed(1);
  const modelPct = (bet.model_prob * 100).toFixed(0);
  const marketPct = (bet.market_implied * 100).toFixed(0);

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium">
            {bet.fighter_a} vs {bet.fighter_b}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            {bet.event_id.replace(/_/g, " ").toUpperCase()}
          </p>
        </div>
        <StarRating stars={bet.star_rating} />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs bg-accent/20 text-accent px-2 py-0.5 rounded font-medium">
          VALUE: {bet.value_side}
        </span>
        <span className="text-xs text-emerald-400 font-medium">
          +{edgePct}% edge
        </span>
      </div>

      <div className="mt-3">
        <EdgeBar edge={bet.edge} />
      </div>

      <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
        <div>
          <p className="text-slate-500">Model</p>
          <p className="font-medium">{modelPct}%</p>
        </div>
        <div>
          <p className="text-slate-500">Market</p>
          <p className="font-medium">{marketPct}%</p>
        </div>
        <div>
          <p className="text-slate-500">Kelly Bet</p>
          <p className="font-medium">
            ${bet.kelly_bet ? bet.kelly_bet.toFixed(0) : "0"}
          </p>
        </div>
      </div>
    </Card>
  );
}

export default function ValueBetsPage() {
  const [data, setData] = useState<ValueBetResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bankroll, setBankroll] = useState(1000);
  const [minEdge, setMinEdge] = useState(3);

  const fetchValueBets = () => {
    setLoading(true);
    setError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/value-bets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        min_edge: minEdge / 100,
        bankroll: bankroll,
        kelly_fraction: 0.25,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((d) => setData(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Value Bet Finder</h1>
        <Link href="/" className="text-xs text-accent hover:underline">
          &larr; Home
        </Link>
      </div>

      <Card className="p-4">
        <p className="text-xs text-slate-400 mb-4">
          Compares your prediction model against live market odds to identify
          value betting opportunities using fractional Kelly criterion sizing.
        </p>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Bankroll ($)
            </label>
            <input
              type="number"
              value={bankroll}
              onChange={(e) => setBankroll(Number(e.target.value))}
              className="w-full rounded-lg bg-black/40 border border-slate-800 px-3 py-1.5 text-sm outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Min Edge (%)
            </label>
            <input
              type="number"
              value={minEdge}
              onChange={(e) => setMinEdge(Number(e.target.value))}
              className="w-full rounded-lg bg-black/40 border border-slate-800 px-3 py-1.5 text-sm outline-none focus:border-accent"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <Button onClick={fetchValueBets} disabled={loading}>
            {loading ? "Scanning..." : "Find Value Bets"}
          </Button>
        </div>
      </Card>

      {error && (
        <Card className="p-5 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {data && (
        <>
          <Card className="p-4">
            <div className="grid grid-cols-3 gap-3 text-center text-xs">
              <div>
                <p className="text-slate-500">Active Predictions</p>
                <p className="text-lg font-semibold">
                  {data.active_predictions}
                </p>
              </div>
              <div>
                <p className="text-slate-500">Odds Bouts</p>
                <p className="text-lg font-semibold">{data.odds_bouts}</p>
              </div>
              <div>
                <p className="text-slate-500">Value Bets Found</p>
                <p className="text-lg font-semibold text-accent">
                  {data.value_bets.length}
                </p>
              </div>
            </div>
          </Card>

          {data.value_bets.length === 0 ? (
            <Card className="p-5">
              <p className="text-sm text-slate-400">
                No value bets found at {minEdge}% minimum edge.
                {data.active_predictions === 0
                  ? " Run some predictions first."
                  : " Try lowering the minimum edge threshold."}
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {data.value_bets
                .sort((a, b) => b.edge - a.edge)
                .map((bet, i) => (
                  <ValueBetCard key={i} bet={bet} />
                ))}
            </div>
          )}
        </>
      )}

      {!data && !loading && !error && (
        <Card className="p-5">
          <p className="text-sm text-slate-400 text-center">
            Click &quot;Find Value Bets&quot; to scan your predictions against
            live market odds.
          </p>
        </Card>
      )}
    </div>
  );
}
