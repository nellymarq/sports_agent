"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type HealthData = {
  status: string;
  version: string;
  models: {
    routing: string;
    prediction: string;
  };
};

type StatsData = {
  routing_llm: Record<string, any>;
  prediction_llm: Record<string, any>;
  recent_pipelines: number;
  pipeline_timings: Array<Record<string, any>>;
};

type CacheData = {
  total_entries: number;
  active_entries: number;
  expired_entries: number;
  default_ttl: number;
};

type TrendPoint = {
  index: number;
  rolling_accuracy: number;
  rolling_brier: number;
  cumulative_accuracy: number;
};

type CalibrationData = {
  total_predictions: number;
  resolved: number;
  correct: number;
  accuracy: number | null;
  brier_score: number | null;
  favorite_accuracy: { total: number; correct: number; accuracy: number | null };
  underdog_accuracy: { total: number; correct: number; accuracy: number | null };
  by_weight_class: Record<string, { total: number; correct: number; accuracy: number | null }>;
  accuracy_trend?: TrendPoint[];
  calibration_curve?: Array<{ bucket: string; predicted: number; actual: number; count: number }>;
};

type ELORanking = {
  rank: number;
  fighter_id: string;
  name: string;
  rating: number;
  fights: number;
  trend: string;
};

type ELOData = {
  total_rated: number;
  rankings: ELORanking[];
};

/* ── tiny helper components ─────────────────────────────── */

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      {ok && (
        <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-40 animate-ping" />
      )}
      <span
        className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
          ok ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,.6)]" : "bg-red-400 shadow-[0_0_6px_rgba(248,113,113,.6)]"
        }`}
      />
    </span>
  );
}

function GlassStatCard({
  label,
  value,
  sub,
  icon,
  accent = false,
  gradient,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon?: string;
  accent?: boolean;
  gradient?: string;
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-slate-700/50 bg-surface/60 backdrop-blur-xl p-4 group hover:border-accent/30 transition-all duration-300 ${
        gradient || ""
      }`}
    >
      {/* subtle corner glow */}
      {accent && (
        <div className="absolute -top-8 -right-8 w-20 h-20 bg-accent/10 rounded-full blur-2xl group-hover:bg-accent/20 transition-all" />
      )}
      <div className="flex items-start justify-between">
        <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
          {label}
        </p>
        {icon && <span className="text-sm opacity-60">{icon}</span>}
      </div>
      <p
        className={`text-xl font-bold mt-1 ${
          accent ? "text-accent" : "text-slate-100"
        }`}
      >
        {value}
      </p>
      {sub && <p className="text-[10px] text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

function TrendArrow({ trend }: { trend: string }) {
  if (trend === "up" || trend === "\u2191")
    return <span className="text-emerald-400 text-xs font-bold">{"\u25B2"}</span>;
  if (trend === "down" || trend === "\u2193")
    return <span className="text-red-400 text-xs font-bold">{"\u25BC"}</span>;
  return <span className="text-slate-600 text-xs">{"\u2014"}</span>;
}

function BrierGauge({ score }: { score: number }) {
  // Brier: 0 = perfect, 0.25 = random. Map to 0-100 where 100 is best.
  const pct = Math.max(0, Math.min(100, (1 - score / 0.25) * 100));
  const color =
    pct >= 70
      ? "from-emerald-500 to-emerald-400"
      : pct >= 50
      ? "from-amber-500 to-yellow-400"
      : "from-red-500 to-red-400";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[10px]">
        <span className="text-slate-500 uppercase tracking-wider font-medium">Brier Score</span>
        <span className="text-slate-300 font-mono">{score.toFixed(4)}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800/80 overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${color} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-[9px] text-slate-600">
        <span>Random (0.25)</span>
        <span>Perfect (0.00)</span>
      </div>
    </div>
  );
}

function RatingBar({ rating, max }: { rating: number; max: number }) {
  const pct = Math.min(100, (rating / max) * 100);
  return (
    <div className="h-1.5 flex-1 rounded-full bg-slate-800/80 overflow-hidden">
      <div
        className="h-full rounded-full bg-gradient-to-r from-accent/60 to-accent transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function AccuracyBar({
  label,
  accuracy,
  count,
}: {
  label: string;
  accuracy: number | null;
  count: string;
}) {
  const pct = accuracy !== null ? accuracy * 100 : 0;
  const color =
    accuracy !== null && accuracy >= 0.65
      ? "from-emerald-500/80 to-emerald-400/60"
      : accuracy !== null && accuracy >= 0.5
      ? "from-amber-500/80 to-yellow-400/60"
      : "from-red-500/80 to-red-400/60";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-300 truncate mr-2">{label}</span>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-slate-600 text-[10px]">{count}</span>
          <span
            className={`font-semibold min-w-[3rem] text-right ${
              accuracy !== null && accuracy >= 0.6
                ? "text-emerald-400"
                : "text-slate-400"
            }`}
          >
            {accuracy !== null ? `${pct.toFixed(0)}%` : "\u2014"}
          </span>
        </div>
      </div>
      <div className="h-1.5 rounded-full bg-slate-800/80 overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${color} transition-all duration-500`}
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
    </div>
  );
}

/* ── loading skeletons ───────────────────────────────────── */

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* status bar */}
      <div className="rounded-xl border border-slate-800 bg-surface/60 p-4 flex items-center gap-3">
        <Skeleton className="h-3 w-3 rounded-full" />
        <Skeleton className="h-4 w-32" />
        <div className="ml-auto flex gap-3">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-16" />
        </div>
      </div>
      {/* hero stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="rounded-xl border border-slate-800 bg-surface/60 backdrop-blur p-4 space-y-3"
          >
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-7 w-14" />
            <Skeleton className="h-2 w-24" />
          </div>
        ))}
      </div>
      {/* two column */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-xl border border-slate-800 bg-surface/60 p-5 space-y-3">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
            <Skeleton className="h-3 w-4/6" />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── main page ───────────────────────────────────────────── */

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [cache, setCache] = useState<CacheData | null>(null);
  const [calibration, setCalibration] = useState<CalibrationData | null>(null);
  const [elo, setElo] = useState<ELOData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchAll = () => {
    setLoading(true);
    setError(null);

    Promise.all([
      fetch(`${apiUrl}/health`).then((r) =>
        r.ok ? r.json() : Promise.reject("Health check failed")
      ),
      fetch(`${apiUrl}/stats`).then((r) =>
        r.ok ? r.json() : Promise.reject("Stats fetch failed")
      ),
      fetch(`${apiUrl}/cache/stats`).then((r) =>
        r.ok ? r.json() : Promise.reject("Cache stats failed")
      ),
      fetch(`${apiUrl}/calibration`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
      fetch(`${apiUrl}/elo/rankings?top_n=10`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
    ])
      .then(([h, s, c, cal, eloData]) => {
        setHealth(h);
        setStats(s);
        setCache(c?.tool_cache || c);
        setCalibration(cal);
        setElo(eloData);
        setLastRefresh(new Date());
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, []);

  const winRate =
    calibration && calibration.resolved > 0 && calibration.accuracy !== null
      ? (calibration.accuracy * 100).toFixed(1)
      : null;

  const latestTrend =
    calibration?.accuracy_trend && calibration.accuracy_trend.length >= 2
      ? calibration.accuracy_trend[calibration.accuracy_trend.length - 1]
          .rolling_accuracy -
        calibration.accuracy_trend[calibration.accuracy_trend.length - 2]
          .rolling_accuracy
      : 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">
      {/* ── Header ────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">
            Command Center
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            UFC Analytics Engine
            {lastRefresh && (
              <> &middot; Updated {lastRefresh.toLocaleTimeString()}</>
            )}
          </p>
        </div>
        <div className="flex gap-3 items-center">
          <button
            onClick={fetchAll}
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-700 bg-surface/60 text-accent hover:bg-accent/10 hover:border-accent/40 transition-all"
          >
            Refresh
          </button>
          <Link
            href="/"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-all"
          >
            Home
          </Link>
        </div>
      </div>

      {/* ── Error ─────────────────────────────────────────── */}
      {error && (
        <Card variant="glass" className="p-4 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
          <p className="text-xs text-red-300/60 mt-1">
            Make sure the backend is running on {apiUrl}
          </p>
        </Card>
      )}

      {/* ── Loading skeleton ──────────────────────────────── */}
      {loading && !health && <DashboardSkeleton />}

      {/* ── System Status Bar ─────────────────────────────── */}
      {health && (
        <Card
          variant="glass"
          className="px-5 py-3 flex flex-wrap items-center gap-4"
        >
          <div className="flex items-center gap-2.5">
            <StatusDot ok={health.status === "ok"} />
            <span className="text-sm font-semibold">
              {health.status === "ok" ? "All Systems Online" : "System Issue"}
            </span>
          </div>
          <div className="h-4 w-px bg-slate-700 hidden sm:block" />
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span>
              v<span className="text-slate-300 font-mono">{health.version}</span>
            </span>
            <span>
              Router:{" "}
              <span className="text-slate-300">{health.models.routing}</span>
            </span>
            <span>
              Predictor:{" "}
              <span className="text-slate-300">{health.models.prediction}</span>
            </span>
          </div>
          {cache && (
            <>
              <div className="h-4 w-px bg-slate-700 hidden sm:block" />
              <span className="text-xs text-slate-500">
                Cache:{" "}
                <span className="text-slate-300">
                  {cache.active_entries}/{cache.total_entries} active
                </span>
              </span>
            </>
          )}
        </Card>
      )}

      {/* ── Hero Prediction Performance ───────────────────── */}
      {calibration && calibration.resolved > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* big accuracy card */}
          <Card
            variant="glass"
            className="p-6 lg:col-span-1 relative overflow-hidden"
          >
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-accent/8 rounded-full blur-3xl" />
            <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-2">
              Overall Accuracy
            </p>
            <div className="flex items-end gap-2">
              <span className="text-5xl font-black text-accent leading-none">
                {winRate ?? "\u2014"}
              </span>
              <span className="text-xl text-accent/60 font-bold mb-1">%</span>
              {latestTrend !== 0 && (
                <span
                  className={`text-sm font-bold mb-1.5 ${
                    latestTrend > 0 ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {latestTrend > 0 ? "\u25B2" : "\u25BC"}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-2">
              {calibration.correct}/{calibration.resolved} correct picks
            </p>
            {calibration.brier_score !== null && (
              <div className="mt-4">
                <BrierGauge score={calibration.brier_score} />
              </div>
            )}
          </Card>

          {/* quick stats grid */}
          <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-3 gap-3">
            <GlassStatCard
              label="Total Predictions"
              value={calibration.total_predictions}
              icon={"\uD83C\uDFAF"}
              sub={`${calibration.resolved} resolved`}
            />
            <GlassStatCard
              label="Win Rate"
              value={winRate ? `${winRate}%` : "\u2014"}
              icon={"\uD83C\uDFC6"}
              accent
              sub={`${calibration.correct} correct`}
            />
            <GlassStatCard
              label="Pending"
              value={calibration.total_predictions - calibration.resolved}
              icon={"\u23F3"}
              sub="Awaiting results"
            />
            {stats && (
              <>
                <GlassStatCard
                  label="Pipeline Runs"
                  value={stats.recent_pipelines}
                  icon={"\u26A1"}
                  sub={`${stats.routing_llm?.total_calls ?? 0} routing calls`}
                />
                <GlassStatCard
                  label="Prediction Calls"
                  value={stats.prediction_llm?.total_calls ?? 0}
                  icon={"\uD83E\uDDE0"}
                />
              </>
            )}
            {cache && (
              <GlassStatCard
                label="Cache Hit Rate"
                value={
                  cache.total_entries > 0
                    ? `${((cache.active_entries / cache.total_entries) * 100).toFixed(0)}%`
                    : "\u2014"
                }
                icon={"\uD83D\uDCBE"}
                sub={`TTL ${cache.default_ttl}s`}
              />
            )}
          </div>
        </div>
      )}

      {/* ── Two-column grid ───────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ── Favorite vs Underdog ──────────────────────────── */}
        {calibration &&
          (calibration.favorite_accuracy?.total > 0 ||
            calibration.underdog_accuracy?.total > 0) && (
            <Card variant="glass" className="p-5">
              <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
                <span className="w-1 h-4 rounded-full bg-accent inline-block" />
                Favorite vs Underdog
              </h2>
              <div className="grid grid-cols-2 gap-3">
                {calibration.favorite_accuracy?.total > 0 && (
                  <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4 text-center">
                    <p className="text-[10px] text-emerald-400/80 uppercase tracking-wider font-medium">
                      Favorites
                    </p>
                    <p className="text-2xl font-bold text-emerald-400 mt-1">
                      {calibration.favorite_accuracy.accuracy !== null
                        ? `${(calibration.favorite_accuracy.accuracy * 100).toFixed(1)}%`
                        : "\u2014"}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-1">
                      {calibration.favorite_accuracy.correct}/
                      {calibration.favorite_accuracy.total} picks
                    </p>
                  </div>
                )}
                {calibration.underdog_accuracy?.total > 0 && (
                  <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-center">
                    <p className="text-[10px] text-amber-400/80 uppercase tracking-wider font-medium">
                      Underdogs
                    </p>
                    <p className="text-2xl font-bold text-amber-400 mt-1">
                      {calibration.underdog_accuracy.accuracy !== null
                        ? `${(calibration.underdog_accuracy.accuracy * 100).toFixed(1)}%`
                        : "\u2014"}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-1">
                      {calibration.underdog_accuracy.correct}/
                      {calibration.underdog_accuracy.total} picks
                    </p>
                  </div>
                )}
              </div>
            </Card>
          )}

        {/* ── Accuracy by Weight Class ──────────────────────── */}
        {calibration?.by_weight_class &&
          Object.keys(calibration.by_weight_class).filter(
            (wc) => wc !== "Unknown"
          ).length > 0 && (
            <Card variant="glass" className="p-5">
              <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
                <span className="w-1 h-4 rounded-full bg-accent inline-block" />
                Accuracy by Weight Class
              </h2>
              <div className="space-y-3">
                {Object.entries(calibration.by_weight_class)
                  .filter(([wc]) => wc !== "Unknown")
                  .sort((a, b) => (b[1].total ?? 0) - (a[1].total ?? 0))
                  .map(([wc, data]) => (
                    <AccuracyBar
                      key={wc}
                      label={wc}
                      accuracy={data.accuracy}
                      count={`${data.correct}/${data.total}`}
                    />
                  ))}
              </div>
            </Card>
          )}

        {/* ── Calibration Curve ─────────────────────────────── */}
        {calibration?.calibration_curve &&
          calibration.calibration_curve.length > 0 && (
            <Card variant="glass" className="p-5">
              <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
                <span className="w-1 h-4 rounded-full bg-accent inline-block" />
                Calibration Curve
              </h2>
              <div className="space-y-2">
                {calibration.calibration_curve.map((b, i) => (
                  <div key={i} className="space-y-1">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-400">{b.bucket}</span>
                      <span className="text-slate-500">n={b.count}</span>
                    </div>
                    <div className="flex gap-1 items-center">
                      <div className="flex-1 h-2 rounded-full bg-slate-800/80 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-accent/50"
                          style={{ width: `${b.predicted * 100}%` }}
                          title={`Predicted: ${(b.predicted * 100).toFixed(0)}%`}
                        />
                      </div>
                      <div className="flex-1 h-2 rounded-full bg-slate-800/80 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-emerald-400/60"
                          style={{ width: `${b.actual * 100}%` }}
                          title={`Actual: ${(b.actual * 100).toFixed(0)}%`}
                        />
                      </div>
                    </div>
                    <div className="flex justify-between text-[9px]">
                      <span className="text-accent/60">
                        Pred {(b.predicted * 100).toFixed(0)}%
                      </span>
                      <span className="text-emerald-400/60">
                        Actual {(b.actual * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

        {/* ── ELO Power Rankings ────────────────────────────── */}
        {elo && elo.rankings.length > 0 && (
          <Card variant="glass" className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold flex items-center gap-2">
                <span className="w-1 h-4 rounded-full bg-accent inline-block" />
                Power Rankings
              </h2>
              <span className="text-[10px] text-slate-500 font-mono">
                {elo.total_rated} rated
              </span>
            </div>
            <div className="space-y-2.5">
              {elo.rankings.map((r) => {
                const maxRating = elo.rankings[0]?.rating || 1600;
                return (
                  <div key={r.fighter_id} className="group">
                    <div className="flex items-center gap-3 text-xs">
                      <span
                        className={`w-6 text-right font-mono font-bold ${
                          r.rank <= 3
                            ? "text-accent"
                            : "text-slate-600"
                        }`}
                      >
                        {r.rank}
                      </span>
                      <span className="text-slate-200 font-medium flex-1 truncate group-hover:text-white transition-colors">
                        {r.name || r.fighter_id}
                      </span>
                      <TrendArrow trend={r.trend} />
                      <span className="text-slate-600 text-[10px] w-14 text-right">
                        {r.fights} fights
                      </span>
                      <span className="font-bold text-accent w-12 text-right font-mono">
                        {Math.round(r.rating)}
                      </span>
                    </div>
                    <div className="ml-9 mt-1">
                      <RatingBar rating={r.rating} max={maxRating * 1.05} />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* ── Accuracy Trend Sparkline ──────────────────────── */}
        {calibration?.accuracy_trend &&
          calibration.accuracy_trend.length > 3 && (
            <Card variant="glass" className="p-5">
              <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <span className="w-1 h-4 rounded-full bg-accent inline-block" />
                Rolling Accuracy Trend
              </h2>
              <div className="flex items-end gap-[2px] h-24 px-1">
                {calibration.accuracy_trend.slice(-40).map((point, i, arr) => {
                  const barColor =
                    point.rolling_accuracy >= 0.65
                      ? "bg-emerald-400"
                      : point.rolling_accuracy >= 0.5
                      ? "bg-amber-400"
                      : "bg-red-400";
                  return (
                    <div
                      key={i}
                      className={`flex-1 rounded-t transition-all duration-300 ${barColor}`}
                      style={{
                        height: `${point.rolling_accuracy * 100}%`,
                        opacity: 0.5 + (i / arr.length) * 0.5,
                      }}
                      title={`#${point.index}: ${(
                        point.rolling_accuracy * 100
                      ).toFixed(0)}% rolling, ${(
                        point.cumulative_accuracy * 100
                      ).toFixed(0)}% cumulative`}
                    />
                  );
                })}
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 mt-2 px-1">
                <span>
                  Rolling (10):{" "}
                  <span className="text-slate-300 font-mono">
                    {(
                      calibration.accuracy_trend[
                        calibration.accuracy_trend.length - 1
                      ]?.rolling_accuracy * 100
                    ).toFixed(0)}
                    %
                  </span>
                </span>
                <span>
                  Cumulative:{" "}
                  <span className="text-slate-300 font-mono">
                    {(
                      calibration.accuracy_trend[
                        calibration.accuracy_trend.length - 1
                      ]?.cumulative_accuracy * 100
                    ).toFixed(0)}
                    %
                  </span>
                </span>
              </div>
            </Card>
          )}

        {/* ── Pipeline Timings ──────────────────────────────── */}
        {stats && stats.pipeline_timings.length > 0 && (
          <Card variant="glass" className="p-5">
            <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-accent inline-block" />
              Recent Pipeline Runs
            </h2>
            <div className="space-y-3">
              {stats.pipeline_timings.slice(0, 5).map((t, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-slate-800/60 bg-black/20 p-3"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-300 truncate max-w-[70%]">
                      {t.query || `Pipeline #${i + 1}`}
                    </span>
                    {t.total && (
                      <span className="text-xs font-bold text-accent font-mono">
                        {typeof t.total === "number"
                          ? `${t.total.toFixed(1)}s`
                          : t.total}
                      </span>
                    )}
                  </div>
                  {t.stages && (
                    <div className="flex gap-1 h-1.5 rounded-full overflow-hidden">
                      {Object.entries(t.stages).map(
                        ([stage, time], si, arr) => {
                          const total = t.total || 1;
                          const pct =
                            typeof time === "number"
                              ? (time / (typeof total === "number" ? total : 1)) * 100
                              : 20;
                          const colors = [
                            "bg-accent/60",
                            "bg-blue-400/60",
                            "bg-purple-400/60",
                            "bg-amber-400/60",
                            "bg-emerald-400/60",
                          ];
                          return (
                            <div
                              key={stage}
                              className={`${colors[si % colors.length]} rounded-sm transition-all`}
                              style={{ width: `${pct}%` }}
                              title={`${stage}: ${
                                typeof time === "number"
                                  ? `${(time as number).toFixed(1)}s`
                                  : time
                              }`}
                            />
                          );
                        }
                      )}
                    </div>
                  )}
                  {t.stages && (
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5">
                      {Object.entries(t.stages).map(
                        ([stage, time], si) => {
                          const dots = [
                            "bg-accent/60",
                            "bg-blue-400/60",
                            "bg-purple-400/60",
                            "bg-amber-400/60",
                            "bg-emerald-400/60",
                          ];
                          const timeVal = time as number | string;
                          return (
                            <span
                              key={stage}
                              className="text-[10px] text-slate-500 flex items-center gap-1"
                            >
                              <span
                                className={`inline-block w-1.5 h-1.5 rounded-full ${dots[si % dots.length]}`}
                              />
                              {stage}:{" "}
                              <span className="text-slate-400">
                                {typeof timeVal === "number"
                                  ? `${timeVal.toFixed(1)}s`
                                  : String(timeVal)}
                              </span>
                            </span>
                          );
                        }
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* ── Quick Actions ─────────────────────────────────── */}
      <Card variant="glass" className="p-5">
        <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <span className="w-1 h-4 rounded-full bg-accent inline-block" />
          Quick Actions
        </h2>
        <div className="flex flex-wrap gap-2">
          {[
            { href: "/calibration", label: "Calibration" },
            { href: "/predictions", label: "Predictions" },
            { href: "/value-bets", label: "Value Bets" },
            { href: "/events", label: "Events" },
            { href: "/bet-calculator", label: "Bet Calculator" },
            { href: "/fighters", label: "Fighters" },
            { href: "/simulate", label: "Simulator" },
          ].map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-xs px-4 py-2 rounded-lg border border-slate-700/60 bg-surface/40 backdrop-blur text-slate-300 hover:text-accent hover:border-accent/40 hover:bg-accent/5 transition-all duration-200"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}
