"use client";

import { useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";

type SimResult = {
  fighter_a: string;
  fighter_b: string;
  simulations: number;
  win_probability: Record<string, number>;
  method_distribution: Record<string, number>;
  round_distribution: Record<string, number>;
  winner_method_breakdown: Record<string, Record<string, number>>;
  statistical_edge: Record<string, number>;
  matchup_type: string;
  is_five_round: boolean;
};

function ProbBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-medium">{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}

function EdgeBar({
  label,
  value,
  nameA,
  nameB,
}: {
  label: string;
  value: number;
  nameA: string;
  nameB: string;
}) {
  const pct = Math.abs(value) * 100;
  const isPositive = value > 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-slate-500 w-12 text-right truncate">{nameB}</span>
      <div className="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden relative">
        <div className="absolute inset-0 flex">
          <div className="w-1/2 flex justify-end">
            {!isPositive && (
              <div
                className="h-full bg-blue-500/60 rounded-l-full"
                style={{ width: `${Math.min(pct * 3, 100)}%` }}
              />
            )}
          </div>
          <div className="w-px bg-slate-600" />
          <div className="w-1/2">
            {isPositive && (
              <div
                className="h-full bg-accent/60 rounded-r-full"
                style={{ width: `${Math.min(pct * 3, 100)}%` }}
              />
            )}
          </div>
        </div>
      </div>
      <span className="text-slate-500 w-12 truncate">{nameA}</span>
      <span className="text-slate-400 w-20 text-right text-[10px]">
        {label}
      </span>
    </div>
  );
}

export default function SimulatePage() {
  const [fighterA, setFighterA] = useState("");
  const [fighterB, setFighterB] = useState("");
  const [fiveRound, setFiveRound] = useState(false);
  const [result, setResult] = useState<SimResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const simulate = () => {
    if (!fighterA.trim() || !fighterB.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    fetch(`${apiUrl}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fighter_a: fighterA.trim(),
        fighter_b: fighterB.trim(),
        is_five_round: fiveRound,
        n_simulations: 10000,
      }),
    })
      .then((r) => {
        if (r.status === 404) throw new Error("Fighter not found");
        if (!r.ok) throw new Error("Simulation failed");
        return r.json();
      })
      .then((data) => setResult(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const nameA = result?.fighter_a || fighterA || "Fighter A";
  const nameB = result?.fighter_b || fighterB || "Fighter B";

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Fight Simulator</h1>
        <Link href="/dashboard" className="text-xs text-accent hover:underline">
          Dashboard
        </Link>
      </div>

      <Card className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Fighter A
            </label>
            <input
              type="text"
              value={fighterA}
              onChange={(e) => setFighterA(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && simulate()}
              placeholder="e.g., Alex Pereira"
              className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm focus:border-accent/60 outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Fighter B
            </label>
            <input
              type="text"
              value={fighterB}
              onChange={(e) => setFighterB(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && simulate()}
              placeholder="e.g., Magomed Ankalaev"
              className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm focus:border-accent/60 outline-none"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={fiveRound}
              onChange={(e) => setFiveRound(e.target.checked)}
              className="accent-cyan-500"
            />
            Championship / 5-round fight
          </label>
        </div>

        <button
          onClick={simulate}
          disabled={loading || !fighterA.trim() || !fighterB.trim()}
          className="w-full py-2 rounded bg-accent/20 border border-accent/40 text-accent text-sm font-medium hover:bg-accent/30 transition-colors disabled:opacity-50"
        >
          {loading ? "Simulating 10,000 fights..." : "Run Simulation"}
        </button>
      </Card>

      {error && (
        <Card className="p-4 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {result && (
        <>
          {/* Win Probability */}
          <Card className="p-4">
            <h3 className="text-sm font-semibold mb-3">
              Win Probability ({result.simulations.toLocaleString()} simulations)
            </h3>
            <div className="flex items-center gap-3 mb-2">
              <div className="text-right flex-1">
                <p className="text-lg font-bold text-accent">
                  {result.win_probability[nameA]?.toFixed(1)}%
                </p>
                <p className="text-xs text-slate-400">{nameA}</p>
              </div>
              <div className="w-full max-w-xs h-4 bg-slate-800 rounded-full overflow-hidden flex">
                <div
                  className="h-full bg-accent/70 transition-all"
                  style={{
                    width: `${result.win_probability[nameA] || 50}%`,
                  }}
                />
                <div
                  className="h-full bg-blue-500/70 transition-all"
                  style={{
                    width: `${result.win_probability[nameB] || 50}%`,
                  }}
                />
              </div>
              <div className="flex-1">
                <p className="text-lg font-bold text-blue-400">
                  {result.win_probability[nameB]?.toFixed(1)}%
                </p>
                <p className="text-xs text-slate-400">{nameB}</p>
              </div>
            </div>
            <p className="text-[10px] text-slate-500 text-center">
              Matchup type: {result.matchup_type.replace("_", " ")} |{" "}
              {result.is_five_round ? "5 rounds" : "3 rounds"}
            </p>
          </Card>

          {/* Method Distribution */}
          <Card className="p-4">
            <h3 className="text-sm font-semibold mb-3">Method Distribution</h3>
            <div className="space-y-2">
              <ProbBar
                label="KO/TKO"
                value={result.method_distribution.ko_tko || 0}
                color="bg-red-500/70"
              />
              <ProbBar
                label="Submission"
                value={result.method_distribution.submission || 0}
                color="bg-purple-500/70"
              />
              <ProbBar
                label="Decision"
                value={result.method_distribution.decision || 0}
                color="bg-slate-500/70"
              />
            </div>
          </Card>

          {/* Round Distribution */}
          <Card className="p-4">
            <h3 className="text-sm font-semibold mb-3">Round Distribution</h3>
            <div className="flex items-end gap-1.5 h-24">
              {Object.entries(result.round_distribution)
                .filter(([, v]) => v > 0)
                .map(([round, pct]) => (
                  <div key={round} className="flex-1 flex flex-col items-center">
                    <div
                      className="w-full rounded-t transition-all"
                      style={{
                        height: `${(pct / Math.max(...Object.values(result.round_distribution))) * 80}px`,
                        backgroundColor:
                          round === "decision"
                            ? "rgb(100, 116, 139)"
                            : "rgb(6, 182, 212)",
                        opacity: 0.7,
                      }}
                    />
                    <p className="text-[10px] text-slate-400 mt-1">
                      {round === "decision" ? "DEC" : round.toUpperCase()}
                    </p>
                    <p className="text-[10px] font-medium">{pct.toFixed(1)}%</p>
                  </div>
                ))}
            </div>
          </Card>

          {/* Statistical Edge */}
          <Card className="p-4">
            <h3 className="text-sm font-semibold mb-3">Statistical Edge Map</h3>
            <div className="space-y-1.5">
              {Object.entries(result.statistical_edge).map(([dim, value]) => (
                <EdgeBar
                  key={dim}
                  label={dim.replace("_", " ")}
                  value={value}
                  nameA={nameA}
                  nameB={nameB}
                />
              ))}
            </div>
            <p className="text-[10px] text-slate-500 mt-2 text-center">
              Center = even | Left favors {nameB} | Right favors {nameA}
            </p>
          </Card>

          {/* Quick Actions */}
          <Card className="p-3">
            <div className="flex gap-2 flex-wrap">
              <Link
                href={`/compare?a=${encodeURIComponent(nameA)}&b=${encodeURIComponent(nameB)}`}
                className="text-xs px-3 py-1.5 rounded border border-slate-700 hover:border-accent/40 transition-colors"
              >
                Detailed Comparison
              </Link>
              <Link
                href={`/fighters/${encodeURIComponent(nameA)}`}
                className="text-xs px-3 py-1.5 rounded border border-slate-700 hover:border-accent/40 transition-colors"
              >
                {nameA} Profile
              </Link>
              <Link
                href={`/fighters/${encodeURIComponent(nameB)}`}
                className="text-xs px-3 py-1.5 rounded border border-slate-700 hover:border-accent/40 transition-colors"
              >
                {nameB} Profile
              </Link>
              <Link
                href={`/analyze?q=${encodeURIComponent(`${nameA} vs ${nameB} full analysis`)}`}
                className="text-xs px-3 py-1.5 rounded border border-accent/40 bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
              >
                Full AI Analysis
              </Link>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
