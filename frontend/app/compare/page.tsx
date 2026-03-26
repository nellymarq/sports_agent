"use client";

import { useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProbabilityBar } from "@/components/ui/probability-bar";
import { EdgeBreakdown, type EdgeItem } from "@/components/ui/edge-breakdown";

/* ────────────────────────────────────────────
   Types
   ──────────────────────────────────────────── */
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
  recent_fights?: Array<{
    opponent: string;
    result: string;
    method?: string;
    date?: string;
  }>;
};

type StatEdge = {
  stat: string;
  fighter_a_value: string;
  fighter_b_value: string;
  edge: string;
};

type FighterProfile = {
  name: string;
  streak?: {
    current_streak: number;
    streak_type: string;
    form_last_5: string;
  };
  method_distribution?: {
    finish_rate: number;
    ko_rate: number;
    sub_rate: number;
    been_finished_rate: number;
  };
};

type StyleAnalysis = {
  fighter_a_style?: string;
  fighter_b_style?: string;
  archetype_a?: string;
  archetype_b?: string;
  style_clash?: string;
};

type EloMatchup = {
  fighter_a_elo?: number;
  fighter_b_elo?: number;
  elo_edge?: string;
  elo_probability?: number;
};

type SharedOpponent = {
  opponent: string;
  fighter_a_result: string;
  fighter_b_result: string;
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
  style_analysis?: StyleAnalysis;
  elo_matchup?: EloMatchup;
  shared_opponents?: SharedOpponent[];
};

/* ────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────── */
function parseNumeric(val: string | number | undefined): number | null {
  if (val == null) return null;
  const n = typeof val === "number" ? val : parseFloat(String(val).replace("%", ""));
  return isNaN(n) ? null : n;
}

/* ────────────────────────────────────────────
   StatBar: visual comparison bar for a single stat
   ──────────────────────────────────────────── */
function StatBar({
  label,
  valA,
  valB,
  higherIsBetter = true,
  nameA,
  nameB,
}: {
  label: string;
  valA: string | number | undefined;
  valB: string | number | undefined;
  higherIsBetter?: boolean;
  nameA: string;
  nameB: string;
}) {
  const a = String(valA ?? "N/A");
  const b = String(valB ?? "N/A");
  const numA = parseNumeric(valA);
  const numB = parseNumeric(valB);

  let edgeSide: "A" | "B" | "even" = "even";
  if (numA !== null && numB !== null) {
    if (higherIsBetter) {
      if (numA > numB) edgeSide = "A";
      else if (numB > numA) edgeSide = "B";
    } else {
      if (numA < numB) edgeSide = "A";
      else if (numB < numA) edgeSide = "B";
    }
  }

  // Compute bar widths (relative to max)
  const maxVal = Math.max(numA || 0, numB || 0) || 1;
  const barA = numA !== null ? (numA / maxVal) * 100 : 0;
  const barB = numB !== null ? (numB / maxVal) * 100 : 0;

  return (
    <div className="py-2.5 border-b border-slate-800/30 last:border-0">
      {/* Label centered */}
      <p className="text-[10px] text-slate-500 text-center uppercase tracking-wider font-semibold mb-1.5">
        {label}
      </p>

      <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-center">
        {/* Fighter A bar (right-aligned, grows left) */}
        <div className="flex items-center gap-2 justify-end">
          <span
            className={`text-xs font-bold tabular-nums shrink-0 ${
              edgeSide === "A" ? "text-accent" : "text-slate-400"
            }`}
          >
            {a}
          </span>
          <div className="w-24 h-2 rounded-full bg-slate-800/50 overflow-hidden relative">
            <div
              className="absolute inset-y-0 right-0 rounded-full transition-all duration-500"
              style={{
                width: `${barA}%`,
                background:
                  edgeSide === "A"
                    ? "linear-gradient(270deg, rgba(0,224,255,0.7) 0%, rgba(0,224,255,0.2) 100%)"
                    : "linear-gradient(270deg, rgba(100,116,139,0.5) 0%, rgba(100,116,139,0.15) 100%)",
              }}
            />
          </div>
        </div>

        {/* Edge indicator dot */}
        <div className="flex items-center justify-center w-3">
          <div
            className={`h-1.5 w-1.5 rounded-full ${
              edgeSide === "A"
                ? "bg-accent shadow-[0_0_6px_rgba(0,224,255,0.5)]"
                : edgeSide === "B"
                ? "bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.5)]"
                : "bg-slate-600"
            }`}
          />
        </div>

        {/* Fighter B bar (left-aligned, grows right) */}
        <div className="flex items-center gap-2">
          <div className="w-24 h-2 rounded-full bg-slate-800/50 overflow-hidden relative">
            <div
              className="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
              style={{
                width: `${barB}%`,
                background:
                  edgeSide === "B"
                    ? "linear-gradient(90deg, rgba(239,68,68,0.7) 0%, rgba(239,68,68,0.2) 100%)"
                    : "linear-gradient(90deg, rgba(100,116,139,0.5) 0%, rgba(100,116,139,0.15) 100%)",
              }}
            />
          </div>
          <span
            className={`text-xs font-bold tabular-nums shrink-0 ${
              edgeSide === "B" ? "text-red-400" : "text-slate-400"
            }`}
          >
            {b}
          </span>
        </div>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────
   Fighter Header Card
   ──────────────────────────────────────────── */
function FighterHeaderCard({
  name,
  record,
  stance,
  side,
  archetype,
}: {
  name: string;
  record?: string;
  stance?: string;
  side: "A" | "B";
  archetype?: string;
}) {
  const accentColor = side === "A" ? "text-accent" : "text-red-400";
  const borderColor =
    side === "A"
      ? "border-accent/20 shadow-[0_0_20px_rgba(0,224,255,0.05)]"
      : "border-red-400/20 shadow-[0_0_20px_rgba(239,68,68,0.05)]";

  return (
    <div
      className={`text-center p-4 rounded-lg border bg-surface/50 ${borderColor} transition-all duration-300`}
    >
      <p className={`font-bold text-base ${accentColor}`}>{name}</p>
      {record && (
        <p className="text-xs text-slate-400 mt-0.5 font-mono">{record}</p>
      )}
      {stance && (
        <p className="text-[10px] text-slate-500 mt-0.5 uppercase tracking-wide">
          {stance}
        </p>
      )}
      {archetype && (
        <span
          className={`inline-block mt-2 text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${
            side === "A"
              ? "border-accent/30 bg-accent/10 text-accent"
              : "border-red-400/30 bg-red-400/10 text-red-400"
          }`}
        >
          {archetype}
        </span>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────
   Method Distribution Mini Bar
   ──────────────────────────────────────────── */
function MethodMiniBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-500 w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-slate-800/50 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${Math.min(value, 100)}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[10px] text-slate-400 tabular-nums w-8 text-right font-medium">
        {value}%
      </span>
    </div>
  );
}

/* ────────────────────────────────────────────
   Loading Skeleton
   ──────────────────────────────────────────── */
function CompareLoadingSkeleton() {
  return (
    <div className="space-y-4 animate-fade-in">
      <Card className="p-5">
        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-2 flex flex-col items-center">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
          <div className="flex items-center justify-center">
            <Skeleton className="h-4 w-8" />
          </div>
          <div className="space-y-2 flex flex-col items-center">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
      </Card>
      <Card className="p-5 space-y-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="grid grid-cols-3 gap-4">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-12 mx-auto" />
            <Skeleton className="h-3 w-full" />
          </div>
        ))}
      </Card>
      <Card className="p-5 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-11/12" />
        <Skeleton className="h-3 w-5/6" />
      </Card>
    </div>
  );
}

/* ────────────────────────────────────────────
   Main Compare Page
   ──────────────────────────────────────────── */
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

  const nameA = data?.fighter_a?.name || fighterA;
  const nameB = data?.fighter_b?.name || fighterB;

  // Build edge items from stat_edges for EdgeBreakdown
  const edgeItems: EdgeItem[] =
    data?.stat_edges?.map((se) => ({
      domain: se.stat,
      winner: se.edge,
      reason: `${nameA}: ${se.fighter_a_value} vs ${nameB}: ${se.fighter_b_value}`,
    })) || [];

  // Style clash badge
  const styleClash = data?.style_analysis;
  const archetypeA = styleClash?.archetype_a || styleClash?.fighter_a_style;
  const archetypeB = styleClash?.archetype_b || styleClash?.fighter_b_style;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-5">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-gradient">Fighter Comparison</h1>
        <Link href="/" className="text-xs text-accent hover:underline">
          &larr; Home
        </Link>
      </div>

      {/* Input card */}
      <Card variant="bordered" className="p-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block mb-1.5">
              Fighter A
            </label>
            <input
              type="text"
              value={fighterA}
              onChange={(e) => setFighterA(e.target.value)}
              placeholder="e.g. Israel Adesanya"
              className="w-full rounded-lg bg-black/40 border border-slate-800 px-3 py-2 text-sm outline-none focus:border-accent transition-colors placeholder:text-slate-600"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCompare();
              }}
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block mb-1.5">
              Fighter B
            </label>
            <input
              type="text"
              value={fighterB}
              onChange={(e) => setFighterB(e.target.value)}
              placeholder="e.g. Alex Pereira"
              className="w-full rounded-lg bg-black/40 border border-slate-800 px-3 py-2 text-sm outline-none focus:border-accent transition-colors placeholder:text-slate-600"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCompare();
              }}
            />
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <span className="text-[10px] text-slate-600">
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

      {/* Error */}
      {error && (
        <Card className="p-5 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {/* Loading skeleton */}
      {loading && <CompareLoadingSkeleton />}

      {/* Results */}
      {data && (
        <div className="space-y-4 animate-slide-up">
          {/* Style clash badge */}
          {(archetypeA || archetypeB || styleClash?.style_clash) && (
            <div className="flex justify-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-surface/80 border border-slate-800/60">
                {archetypeA && (
                  <span className="text-[10px] font-bold uppercase tracking-widest text-accent">
                    {archetypeA}
                  </span>
                )}
                {archetypeA && archetypeB && (
                  <span className="text-[10px] text-slate-600 font-bold">vs</span>
                )}
                {archetypeB && (
                  <span className="text-[10px] font-bold uppercase tracking-widest text-red-400">
                    {archetypeB}
                  </span>
                )}
                {styleClash?.style_clash && (
                  <span className="text-[10px] text-slate-500 ml-1">
                    {styleClash.style_clash}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Fighter header cards */}
          <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-center">
            <FighterHeaderCard
              name={nameA}
              record={data.fighter_a.record}
              stance={data.fighter_a.stance}
              side="A"
              archetype={archetypeA}
            />
            <div className="flex flex-col items-center gap-1">
              <span className="text-xs font-bold text-slate-600 tracking-widest">VS</span>
              <div className="h-px w-8 bg-slate-800" />
            </div>
            <FighterHeaderCard
              name={nameB}
              record={data.fighter_b.record}
              stance={data.fighter_b.stance}
              side="B"
              archetype={archetypeB}
            />
          </div>

          {/* ELO matchup */}
          {data.elo_matchup && (data.elo_matchup.fighter_a_elo || data.elo_matchup.fighter_b_elo) && (
            <Card className="p-4">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-3">
                ELO Rating
              </h3>
              <div className="grid grid-cols-3 items-center">
                <div className="text-center">
                  <p className="text-2xl font-bold text-accent tabular-nums">
                    {data.elo_matchup.fighter_a_elo ?? "N/A"}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{nameA}</p>
                </div>
                <div className="text-center">
                  {data.elo_matchup.elo_probability != null && (
                    <div className="space-y-1">
                      <p className="text-[10px] text-slate-600 uppercase tracking-wide">
                        ELO Win Prob
                      </p>
                      <ProbabilityBar
                        labelA={nameA}
                        labelB={nameB}
                        valueA={Math.round(data.elo_matchup.elo_probability * 100)}
                        valueB={Math.round((1 - data.elo_matchup.elo_probability) * 100)}
                      />
                    </div>
                  )}
                  {data.elo_matchup.elo_edge && !data.elo_matchup.elo_probability && (
                    <span className="text-[10px] text-slate-500 font-medium">
                      Edge: {data.elo_matchup.elo_edge}
                    </span>
                  )}
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-red-400 tabular-nums">
                    {data.elo_matchup.fighter_b_elo ?? "N/A"}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{nameB}</p>
                </div>
              </div>
            </Card>
          )}

          {/* Tale of the Tape / Stats comparison */}
          <Card variant="glow" className="p-5">
            <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">
              Tale of the Tape
            </h3>
            <div className="grid grid-cols-3 mb-3">
              <p className="text-xs font-semibold text-accent text-center">{nameA}</p>
              <p className="text-[10px] text-slate-600 text-center"></p>
              <p className="text-xs font-semibold text-red-400 text-center">{nameB}</p>
            </div>

            <StatBar label="Height" valA={data.fighter_a.height} valB={data.fighter_b.height} nameA={nameA} nameB={nameB} />
            <StatBar label="Reach" valA={data.fighter_a.reach} valB={data.fighter_b.reach} nameA={nameA} nameB={nameB} />
            <StatBar label="Sig. Strikes Landed / Min" valA={data.fighter_a.slpm} valB={data.fighter_b.slpm} nameA={nameA} nameB={nameB} />
            <StatBar label="Striking Accuracy" valA={data.fighter_a.str_acc} valB={data.fighter_b.str_acc} nameA={nameA} nameB={nameB} />
            <StatBar label="Sig. Strikes Absorbed / Min" valA={data.fighter_a.sapm} valB={data.fighter_b.sapm} higherIsBetter={false} nameA={nameA} nameB={nameB} />
            <StatBar label="Striking Defense" valA={data.fighter_a.str_def} valB={data.fighter_b.str_def} nameA={nameA} nameB={nameB} />
            <StatBar label="Takedowns / 15 Min" valA={data.fighter_a.td_avg} valB={data.fighter_b.td_avg} nameA={nameA} nameB={nameB} />
            <StatBar label="Takedown Accuracy" valA={data.fighter_a.td_acc} valB={data.fighter_b.td_acc} nameA={nameA} nameB={nameB} />
            <StatBar label="Takedown Defense" valA={data.fighter_a.td_def} valB={data.fighter_b.td_def} nameA={nameA} nameB={nameB} />
            <StatBar label="Submissions / 15 Min" valA={data.fighter_a.sub_avg} valB={data.fighter_b.sub_avg} nameA={nameA} nameB={nameB} />
          </Card>

          {/* Edge Breakdown */}
          {edgeItems.length > 0 && (
            <Card className="p-5">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-3">
                Edge Breakdown
              </h3>
              <EdgeBreakdown
                edges={edgeItems}
                fighterA={nameA}
                fighterB={nameB}
              />
            </Card>
          )}

          {/* Fighter Profiles - Streak & Methods */}
          {(data.fighter_a_profile || data.fighter_b_profile) && (
            <Card className="p-5">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
                Form & Method Distribution
              </h3>
              <div className="grid grid-cols-2 gap-6">
                {[
                  {
                    profile: data.fighter_a_profile,
                    name: nameA,
                    side: "A" as const,
                  },
                  {
                    profile: data.fighter_b_profile,
                    name: nameB,
                    side: "B" as const,
                  },
                ].map(({ profile, name, side }) =>
                  profile ? (
                    <div key={name} className="space-y-3">
                      <p
                        className={`text-xs font-bold text-center ${
                          side === "A" ? "text-accent" : "text-red-400"
                        }`}
                      >
                        {name}
                      </p>

                      {/* Streak */}
                      {profile.streak && (
                        <div className="flex items-center justify-center gap-3">
                          <div className="text-center">
                            <span
                              className={`text-lg font-bold tabular-nums ${
                                profile.streak.streak_type === "W"
                                  ? "text-emerald-400"
                                  : profile.streak.streak_type === "L"
                                  ? "text-red-400"
                                  : "text-slate-300"
                              }`}
                            >
                              {profile.streak.current_streak}
                              {profile.streak.streak_type}
                            </span>
                            <p className="text-[9px] text-slate-600 uppercase tracking-wide">
                              Streak
                            </p>
                          </div>
                          <div className="h-6 w-px bg-slate-800" />
                          <div className="text-center">
                            <span className="text-sm font-mono text-slate-300 tracking-wider">
                              {profile.streak.form_last_5}
                            </span>
                            <p className="text-[9px] text-slate-600 uppercase tracking-wide">
                              Last 5
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Method distribution bars */}
                      {profile.method_distribution && (
                        <div className="space-y-1.5 pt-1">
                          <MethodMiniBar
                            label="Finish"
                            value={profile.method_distribution.finish_rate}
                            color={side === "A" ? "#00E0FF" : "#f87171"}
                          />
                          <MethodMiniBar
                            label="KO"
                            value={profile.method_distribution.ko_rate}
                            color="#f97316"
                          />
                          <MethodMiniBar
                            label="Sub"
                            value={profile.method_distribution.sub_rate}
                            color="#a78bfa"
                          />
                          <MethodMiniBar
                            label="Been KO'd"
                            value={profile.method_distribution.been_finished_rate}
                            color="#ef4444"
                          />
                        </div>
                      )}
                    </div>
                  ) : null
                )}
              </div>
            </Card>
          )}

          {/* Shared Opponents */}
          {data.shared_opponents && data.shared_opponents.length > 0 && (
            <Card className="p-5">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-3">
                Common Opponents
              </h3>
              <div className="space-y-1">
                <div className="grid grid-cols-3 text-[9px] uppercase tracking-wider text-slate-600 font-semibold pb-1.5 border-b border-slate-800/50">
                  <span className="text-center text-accent/60">{nameA}</span>
                  <span className="text-center">Opponent</span>
                  <span className="text-center text-red-400/60">{nameB}</span>
                </div>
                {data.shared_opponents.map((so, i) => (
                  <div
                    key={i}
                    className="grid grid-cols-3 py-2 border-b border-slate-800/20 text-xs items-center"
                  >
                    <span
                      className={`text-center font-medium ${
                        so.fighter_a_result.toLowerCase().startsWith("w")
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {so.fighter_a_result}
                    </span>
                    <span className="text-center text-slate-400 font-medium">
                      {so.opponent}
                    </span>
                    <span
                      className={`text-center font-medium ${
                        so.fighter_b_result.toLowerCase().startsWith("w")
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {so.fighter_b_result}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Recent Fights */}
          {(data.fighter_a.recent_fights?.length || data.fighter_b.recent_fights?.length) ? (
            <Card className="p-5">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-3">
                Recent Fights
              </h3>
              <div className="grid grid-cols-2 gap-6">
                {[
                  { fights: data.fighter_a.recent_fights, name: nameA, side: "A" as const },
                  { fights: data.fighter_b.recent_fights, name: nameB, side: "B" as const },
                ].map(({ fights, name, side }) => (
                  <div key={name}>
                    <p className={`text-xs font-bold mb-2 ${side === "A" ? "text-accent" : "text-red-400"}`}>
                      {name}
                    </p>
                    {fights && fights.length > 0 ? (
                      <div className="space-y-1.5">
                        {fights.slice(0, 5).map((f, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 text-[10px] py-1 border-b border-slate-800/20"
                          >
                            <span
                              className={`font-bold w-4 ${
                                f.result.toLowerCase().startsWith("w")
                                  ? "text-emerald-400"
                                  : f.result.toLowerCase().startsWith("l")
                                  ? "text-red-400"
                                  : "text-slate-400"
                              }`}
                            >
                              {f.result.charAt(0).toUpperCase()}
                            </span>
                            <span className="text-slate-300 flex-1 truncate">
                              {f.opponent}
                            </span>
                            {f.method && (
                              <span className="text-slate-600 truncate max-w-[60px]">
                                {f.method}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[10px] text-slate-600">No data</p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          ) : null}

          {/* Text comparison */}
          {data.comparison && (
            <Card className="p-5">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-3">
                Head-to-Head Analysis
              </h3>
              <div className="text-xs text-slate-300 whitespace-pre-line leading-relaxed">
                {data.comparison}
              </div>
            </Card>
          )}

          {/* Quick action */}
          <div className="flex justify-center pt-2">
            <Link
              href={`/analyze?q=${encodeURIComponent(
                `Who wins between ${fighterA} and ${fighterB}?`
              )}`}
              className="inline-flex items-center gap-2 text-xs text-accent hover:underline group"
            >
              <span>Run full multi-agent prediction for this matchup</span>
              <svg
                className="h-3 w-3 transition-transform group-hover:translate-x-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
