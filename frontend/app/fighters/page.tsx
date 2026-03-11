"use client";

import { useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";

type StyleData = {
  primary_style: string;
  primary_score: number;
  primary_description: string;
  secondary_style: string | null;
  secondary_score: number | null;
  style_scores: Record<string, number>;
  relevant_specialists: string[];
};

type RiskProfile = {
  chin_risk: string;
  ko_vulnerability: string;
  takedown_vulnerability: string;
  submission_vulnerability: string;
  layoff_risk?: string;
};

type MethodDist = {
  wins: Record<string, number>;
  losses: Record<string, number>;
  finish_rate: number;
  ko_rate: number;
  sub_rate: number;
  been_finished_rate: number;
  total_wins: number;
  total_losses: number;
};

type Streak = {
  current_streak: number;
  streak_type: string;
  form_last_5: string;
};

type Activity = {
  fights_per_year: number;
  last_fight_days_ago: number | null;
  total_ufc_fights: number;
  last_fight_date?: string;
};

type EloData = {
  rating: number;
  fights_rated: number;
  history: Array<{
    date: string;
    event: string;
    result: string;
    old_rating: number;
    new_rating: number;
    change: number;
  }>;
};

type FighterProfile = {
  name: string;
  record?: string;
  height?: string;
  weight?: string;
  reach?: string;
  stance?: string;
  slpm?: string;
  str_acc?: string;
  sapm?: string;
  str_def?: string;
  td_avg?: string;
  td_acc?: string;
  td_def?: string;
  sub_avg?: string;
  style?: StyleData;
  elo?: EloData;
  risk_profile?: RiskProfile;
  method_distribution?: MethodDist;
  streak?: Streak;
  activity?: Activity;
};

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    low: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    moderate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
    high: "bg-red-500/10 text-red-400 border-red-500/30",
  };
  return (
    <span
      className={`text-[10px] px-1.5 py-0.5 rounded border ${
        colors[level] || colors.low
      }`}
    >
      {level}
    </span>
  );
}

function StyleBar({
  label,
  score,
  max,
}: {
  label: string;
  score: number;
  max: number;
}) {
  const pct = Math.min((score / max) * 100, 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-slate-400 w-28 text-right truncate">{label}</span>
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-accent/70 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-slate-500 w-8 text-right">{score.toFixed(0)}</span>
    </div>
  );
}

function FormDot({ result }: { result: string }) {
  const colors: Record<string, string> = {
    W: "bg-emerald-400",
    L: "bg-red-400",
    D: "bg-yellow-400",
    "?": "bg-slate-600",
  };
  return (
    <span
      className={`inline-block h-5 w-5 rounded-full text-[10px] font-bold flex items-center justify-center ${
        colors[result] || colors["?"]
      }`}
    >
      {result}
    </span>
  );
}

export default function FightersPage() {
  const [query, setQuery] = useState("");
  const [profile, setProfile] = useState<FighterProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const search = () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setProfile(null);

    fetch(`${apiUrl}/fighters/${encodeURIComponent(query.trim())}/profile`)
      .then((r) => {
        if (r.status === 404) throw new Error("Fighter not found");
        if (!r.ok) throw new Error("Profile fetch failed");
        return r.json();
      })
      .then((data) => setProfile(data.fighter))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Fighter Profile</h1>
        <Link href="/dashboard" className="text-xs text-accent hover:underline">
          Dashboard
        </Link>
      </div>

      {/* Search */}
      <Card className="p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="Search fighter (e.g., Alex Pereira)"
            className="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm focus:border-accent/60 outline-none"
          />
          <button
            onClick={search}
            disabled={loading}
            className="px-4 py-1.5 rounded bg-accent/20 border border-accent/40 text-accent text-sm font-medium hover:bg-accent/30 transition-colors disabled:opacity-50"
          >
            {loading ? "..." : "Search"}
          </button>
        </div>
      </Card>

      {error && (
        <Card className="p-4 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {profile && (
        <>
          {/* Header */}
          <Card className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-bold">{profile.name}</h2>
                <p className="text-sm text-slate-400 mt-0.5">
                  {profile.record || "Record N/A"}
                </p>
                {profile.style && (
                  <p className="text-xs text-accent mt-1">
                    {profile.style.primary_description}
                  </p>
                )}
              </div>
              {profile.elo && (
                <div className="text-right">
                  <p className="text-[10px] text-slate-500 uppercase">
                    ELO Rating
                  </p>
                  <p className="text-lg font-semibold text-accent">
                    {Math.round(profile.elo.rating)}
                  </p>
                  <p className="text-[10px] text-slate-500">
                    {profile.elo.fights_rated} rated fights
                  </p>
                </div>
              )}
            </div>

            {/* Physical */}
            <div className="grid grid-cols-4 gap-3 mt-4">
              {[
                { label: "Height", value: profile.height },
                { label: "Weight", value: profile.weight },
                { label: "Reach", value: profile.reach },
                { label: "Stance", value: profile.stance },
              ].map(
                (attr) =>
                  attr.value && (
                    <div key={attr.label} className="text-center">
                      <p className="text-[10px] text-slate-500 uppercase">
                        {attr.label}
                      </p>
                      <p className="text-sm font-medium">{attr.value}</p>
                    </div>
                  )
              )}
            </div>

            {/* Form */}
            {profile.streak && (
              <div className="mt-4 flex items-center gap-4">
                <div className="flex items-center gap-1">
                  <span className="text-xs text-slate-400">Form:</span>
                  <div className="flex gap-0.5">
                    {profile.streak.form_last_5.split("").map((r, i) => (
                      <FormDot key={i} result={r} />
                    ))}
                  </div>
                </div>
                <span className="text-xs text-slate-400">
                  {profile.streak.current_streak > 0
                    ? `${profile.streak.current_streak}${profile.streak.streak_type} streak`
                    : ""}
                </span>
                {profile.activity && (
                  <span className="text-xs text-slate-500 ml-auto">
                    {profile.activity.fights_per_year} fights/yr
                    {profile.activity.last_fight_days_ago !== null &&
                      ` | Last: ${profile.activity.last_fight_days_ago}d ago`}
                  </span>
                )}
              </div>
            )}
          </Card>

          {/* Stats */}
          <Card className="p-4">
            <h3 className="text-sm font-semibold mb-3">Statistics</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "SLpM", value: profile.slpm, sub: "Strikes/Min" },
                {
                  label: "Str. Accuracy",
                  value: profile.str_acc,
                  sub: "% Landed",
                },
                {
                  label: "SApM",
                  value: profile.sapm,
                  sub: "Absorbed/Min",
                },
                {
                  label: "Str. Defense",
                  value: profile.str_def,
                  sub: "% Avoided",
                },
                { label: "TD Avg", value: profile.td_avg, sub: "per 15 min" },
                {
                  label: "TD Accuracy",
                  value: profile.td_acc,
                  sub: "% Landed",
                },
                {
                  label: "TD Defense",
                  value: profile.td_def,
                  sub: "% Defended",
                },
                {
                  label: "Sub Avg",
                  value: profile.sub_avg,
                  sub: "per 15 min",
                },
              ].map(
                (stat) =>
                  stat.value && (
                    <div
                      key={stat.label}
                      className="rounded-lg border border-slate-800 bg-surface p-2.5"
                    >
                      <p className="text-[10px] text-slate-500 uppercase">
                        {stat.label}
                      </p>
                      <p className="text-base font-semibold mt-0.5">
                        {stat.value}
                      </p>
                      <p className="text-[10px] text-slate-500">{stat.sub}</p>
                    </div>
                  )
              )}
            </div>
          </Card>

          {/* Style Analysis */}
          {profile.style &&
            profile.style.style_scores &&
            Object.keys(profile.style.style_scores).length > 0 && (
              <Card className="p-4">
                <h3 className="text-sm font-semibold mb-3">Style Profile</h3>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs px-2 py-0.5 rounded bg-accent/10 border border-accent/30 text-accent">
                    {profile.style.primary_style.replace("_", " ")}
                  </span>
                  {profile.style.secondary_style && (
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                      {profile.style.secondary_style.replace("_", " ")}
                    </span>
                  )}
                </div>
                <div className="space-y-1.5">
                  {Object.entries(profile.style.style_scores)
                    .sort(([, a], [, b]) => b - a)
                    .map(([style, score]) => (
                      <StyleBar
                        key={style}
                        label={style.replace("_", " ")}
                        score={score}
                        max={100}
                      />
                    ))}
                </div>
              </Card>
            )}

          {/* Method Distribution */}
          {profile.method_distribution &&
            profile.method_distribution.total_wins > 0 && (
              <Card className="p-4">
                <h3 className="text-sm font-semibold mb-3">
                  Method Distribution
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-slate-400 mb-2">Wins</p>
                    <div className="space-y-1">
                      {Object.entries(profile.method_distribution.wins)
                        .filter(([, v]) => v > 0)
                        .map(([method, count]) => (
                          <div
                            key={method}
                            className="flex justify-between text-xs"
                          >
                            <span className="text-slate-300">
                              {method.replace("_", "/")}
                            </span>
                            <span className="text-emerald-400 font-medium">
                              {count}
                            </span>
                          </div>
                        ))}
                    </div>
                    <div className="mt-2 text-[10px] text-slate-500 space-y-0.5">
                      <p>
                        Finish rate: {profile.method_distribution.finish_rate}%
                      </p>
                      <p>KO rate: {profile.method_distribution.ko_rate}%</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-2">Losses</p>
                    <div className="space-y-1">
                      {Object.entries(profile.method_distribution.losses)
                        .filter(([, v]) => v > 0)
                        .map(([method, count]) => (
                          <div
                            key={method}
                            className="flex justify-between text-xs"
                          >
                            <span className="text-slate-300">
                              {method.replace("_", "/")}
                            </span>
                            <span className="text-red-400 font-medium">
                              {count}
                            </span>
                          </div>
                        ))}
                    </div>
                    <div className="mt-2 text-[10px] text-slate-500">
                      <p>
                        Been finished:{" "}
                        {profile.method_distribution.been_finished_rate}%
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
            )}

          {/* Risk Profile */}
          {profile.risk_profile && (
            <Card className="p-4">
              <h3 className="text-sm font-semibold mb-3">
                Vulnerability Profile
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {[
                  { label: "Chin", key: "chin_risk" },
                  { label: "KO Vulnerability", key: "ko_vulnerability" },
                  { label: "TD Defense", key: "takedown_vulnerability" },
                  { label: "Sub Vulnerability", key: "submission_vulnerability" },
                  { label: "Layoff", key: "layoff_risk" },
                ]
                  .filter(
                    (item) =>
                      profile.risk_profile?.[
                        item.key as keyof RiskProfile
                      ] !== undefined
                  )
                  .map((item) => (
                    <div
                      key={item.key}
                      className="flex items-center justify-between"
                    >
                      <span className="text-xs text-slate-400">
                        {item.label}
                      </span>
                      <RiskBadge
                        level={
                          profile.risk_profile?.[
                            item.key as keyof RiskProfile
                          ] || "low"
                        }
                      />
                    </div>
                  ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
