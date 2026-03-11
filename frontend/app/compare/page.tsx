"use client";

import { useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type FighterData = {
  name?: string;
  record?: string;
  stance?: string;
  height?: string;
  weight?: string;
  reach?: string;
  slpm?: string | number;
  str_acc?: string;
  sapm?: string | number;
  str_def?: string;
  td_avg?: string | number;
  td_acc?: string;
  td_def?: string;
  sub_avg?: string | number;
  recent_fights?: Array<{ opponent: string; result: string; method?: string; date?: string }>;
};

type StatEdge = {
  stat: string;
  fighter_a_value: string;
  fighter_b_value: string;
  edge: string;
};

type FighterProfile = {
  name: string;
  streak?: { current_streak: number; streak_type: string; form_last_5: string };
  method_distribution?: {
    finish_rate: number;
    ko_rate: number;
    sub_rate: number;
    been_finished_rate: number;
  };
};

type CompareResponse = {
  status: string;
  fighter_a: FighterData;
  fighter_b: FighterData;
  comparison: string;
  tale_of_the_tape?: string;
  stat_edges?: StatEdge[];
  fighter_a_profile?: FighterProfile;
  fighter_b_profile?: FighterProfile;
};

function StatRow({
  label,
  valA,
  valB,
}: {
  label: string;
  valA: string | number | undefined;
  valB: string | number | undefined;
}) {
  const a = String(valA ?? "N/A");
  const b = String(valB ?? "N/A");

  return (
    <div className="grid grid-cols-3 py-1.5 border-b border-slate-800/30 text-xs">
      <span className="text-right pr-3 font-medium">{a}</span>
      <span className="text-center text-slate-500">{label}</span>
      <span className="pl-3 font-medium">{b}</span>
    </div>
  );
}

function FighterHeader({
  name,
  record,
  stance,
}: {
  name: string;
  record?: string;
  stance?: string;
}) {
  return (
    <div className="text-center">
      <p className="font-semibold text-sm">{name}</p>
      {record && <p className="text-xs text-slate-400">{record}</p>}
      {stance && <p className="text-[10px] text-slate-500">{stance}</p>}
    </div>
  );
}

export default function ComparePage() {
  const [fighterA, setFighterA] = useState("");
  const [fighterB, setFighterB] = useState("");
  const [data, setData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = () => {
    if (!fighterA.trim() || !fighterB.trim()) return;

    setLoading(true);
    setError(null);
    setData(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fighter_a: fighterA.trim(),
        fighter_b: fighterB.trim(),
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
        <h1 className="text-lg font-semibold">Fighter Comparison</h1>
        <Link href="/" className="text-xs text-accent hover:underline">
          &larr; Home
        </Link>
      </div>

      <Card className="p-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Fighter A
            </label>
            <input
              type="text"
              value={fighterA}
              onChange={(e) => setFighterA(e.target.value)}
              placeholder="e.g. Israel Adesanya"
              className="w-full rounded-lg bg-black/40 border border-slate-800 px-3 py-1.5 text-sm outline-none focus:border-accent"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCompare();
              }}
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
              placeholder="e.g. Alex Pereira"
              className="w-full rounded-lg bg-black/40 border border-slate-800 px-3 py-1.5 text-sm outline-none focus:border-accent"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCompare();
              }}
            />
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Pulls live data from UFCStats
          </span>
          <Button
            onClick={handleCompare}
            disabled={loading || !fighterA.trim() || !fighterB.trim()}
          >
            {loading ? "Comparing..." : "Compare"}
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
          {/* Fighter headers */}
          <Card className="p-4">
            <div className="grid grid-cols-3">
              <FighterHeader
                name={data.fighter_a.name || fighterA}
                record={data.fighter_a.record}
                stance={data.fighter_a.stance}
              />
              <div className="flex items-center justify-center">
                <span className="text-xs text-slate-500 font-semibold">VS</span>
              </div>
              <FighterHeader
                name={data.fighter_b.name || fighterB}
                record={data.fighter_b.record}
                stance={data.fighter_b.stance}
              />
            </div>
          </Card>

          {/* Stats comparison */}
          <Card className="p-4">
            <h3 className="text-xs font-semibold text-slate-400 mb-2">
              Statistical Comparison
            </h3>
            <StatRow label="Height" valA={data.fighter_a.height} valB={data.fighter_b.height} />
            <StatRow label="Reach" valA={data.fighter_a.reach} valB={data.fighter_b.reach} />
            <StatRow label="SLpM" valA={data.fighter_a.slpm} valB={data.fighter_b.slpm} />
            <StatRow label="Str. Acc." valA={data.fighter_a.str_acc} valB={data.fighter_b.str_acc} />
            <StatRow label="SApM" valA={data.fighter_a.sapm} valB={data.fighter_b.sapm} />
            <StatRow label="Str. Def." valA={data.fighter_a.str_def} valB={data.fighter_b.str_def} />
            <StatRow label="TD Avg" valA={data.fighter_a.td_avg} valB={data.fighter_b.td_avg} />
            <StatRow label="TD Acc." valA={data.fighter_a.td_acc} valB={data.fighter_b.td_acc} />
            <StatRow label="TD Def." valA={data.fighter_a.td_def} valB={data.fighter_b.td_def} />
            <StatRow label="Sub Avg" valA={data.fighter_a.sub_avg} valB={data.fighter_b.sub_avg} />
          </Card>

          {/* Stat Edges */}
          {data.stat_edges && data.stat_edges.length > 0 && (
            <Card className="p-4">
              <h3 className="text-xs font-semibold text-slate-400 mb-2">
                Statistical Edge Breakdown
              </h3>
              <div className="space-y-1">
                {data.stat_edges.map((se, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-xs py-1 border-b border-slate-800/30"
                  >
                    <span className="text-slate-400 w-28">{se.stat}</span>
                    <span
                      className={`font-medium ${
                        se.edge === (data.fighter_a.name || fighterA)
                          ? "text-cyan-400"
                          : se.edge === (data.fighter_b.name || fighterB)
                          ? "text-orange-400"
                          : "text-slate-500"
                      }`}
                    >
                      {se.edge}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Fighter Profiles - Streak & Methods */}
          {(data.fighter_a_profile || data.fighter_b_profile) && (
            <Card className="p-4">
              <h3 className="text-xs font-semibold text-slate-400 mb-3">
                Form & Method Distribution
              </h3>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { profile: data.fighter_a_profile, name: data.fighter_a.name || fighterA },
                  { profile: data.fighter_b_profile, name: data.fighter_b.name || fighterB },
                ].map(({ profile, name }) =>
                  profile ? (
                    <div key={name} className="space-y-2">
                      <p className="text-xs font-semibold text-center">{name}</p>
                      {profile.streak && (
                        <div className="text-center">
                          <span className="text-xs text-slate-400">
                            Streak:{" "}
                            <span
                              className={
                                profile.streak.streak_type === "W"
                                  ? "text-emerald-400 font-medium"
                                  : profile.streak.streak_type === "L"
                                  ? "text-red-400 font-medium"
                                  : "text-slate-300"
                              }
                            >
                              {profile.streak.current_streak}
                              {profile.streak.streak_type}
                            </span>
                          </span>
                          <span className="text-xs text-slate-500 ml-2">
                            Form: {profile.streak.form_last_5}
                          </span>
                        </div>
                      )}
                      {profile.method_distribution && (
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10px]">
                            <span className="text-slate-500">Finish Rate</span>
                            <span className="text-slate-300">
                              {profile.method_distribution.finish_rate}%
                            </span>
                          </div>
                          <div className="flex justify-between text-[10px]">
                            <span className="text-slate-500">KO Rate</span>
                            <span className="text-slate-300">
                              {profile.method_distribution.ko_rate}%
                            </span>
                          </div>
                          <div className="flex justify-between text-[10px]">
                            <span className="text-slate-500">Sub Rate</span>
                            <span className="text-slate-300">
                              {profile.method_distribution.sub_rate}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : null
                )}
              </div>
            </Card>
          )}

          {/* Text comparison */}
          {data.comparison && (
            <Card className="p-4">
              <h3 className="text-xs font-semibold text-slate-400 mb-2">
                Head-to-Head Analysis
              </h3>
              <div className="text-xs text-slate-300 whitespace-pre-line leading-relaxed">
                {data.comparison}
              </div>
            </Card>
          )}

          {/* Quick action */}
          <div className="flex justify-center">
            <Link
              href={`/analyze?q=${encodeURIComponent(`Who wins between ${fighterA} and ${fighterB}?`)}`}
              className="text-xs text-accent hover:underline"
            >
              Run full multi-agent prediction for this matchup &rarr;
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
