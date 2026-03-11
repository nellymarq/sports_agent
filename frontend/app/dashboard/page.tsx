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

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${
        ok ? "bg-emerald-400" : "bg-red-400"
      }`}
    />
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-surface p-3">
      <p className="text-[10px] text-slate-500 uppercase tracking-wider">
        {label}
      </p>
      <p className="text-lg font-semibold mt-0.5">{value}</p>
      {sub && <p className="text-[10px] text-slate-500 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [cache, setCache] = useState<CacheData | null>(null);
  const [calibration, setCalibration] = useState<CalibrationData | null>(null);
  const [elo, setElo] = useState<ELOData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      fetch(`${apiUrl}/calibration`).then((r) =>
        r.ok ? r.json() : null
      ).catch(() => null),
      fetch(`${apiUrl}/elo/rankings?top_n=10`).then((r) =>
        r.ok ? r.json() : null
      ).catch(() => null),
    ])
      .then(([h, s, c, cal, eloData]) => {
        setHealth(h);
        setStats(s);
        // Handle both nested and flat cache formats
        setCache(c?.tool_cache || c);
        setCalibration(cal);
        setElo(eloData);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">System Dashboard</h1>
        <div className="flex gap-3 items-center">
          <button
            onClick={fetchAll}
            className="text-xs text-accent hover:underline"
          >
            Refresh
          </button>
          <Link href="/" className="text-xs text-accent hover:underline">
            Home
          </Link>
        </div>
      </div>

      {error && (
        <Card className="p-4 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
          <p className="text-xs text-red-300/60 mt-1">
            Make sure the backend is running on {apiUrl}
          </p>
        </Card>
      )}

      {loading && !health && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="rounded-lg border border-slate-800 bg-surface p-3 space-y-2"
            >
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-6 w-12" />
            </div>
          ))}
        </div>
      )}

      {/* Health Overview */}
      {health && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <StatusDot ok={health.status === "ok"} />
            <h2 className="text-sm font-semibold">Backend Health</h2>
            <span className="text-xs text-slate-500 ml-auto">
              v{health.version}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <StatCard
              label="Routing Model"
              value={health.models.routing}
              sub="Fast routing LLM"
            />
            <StatCard
              label="Prediction Model"
              value={health.models.prediction}
              sub="Main analysis LLM"
            />
          </div>
        </Card>
      )}

      {/* Pipeline Stats */}
      {stats && (
        <Card className="p-4">
          <h2 className="text-sm font-semibold mb-3">Pipeline Performance</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <StatCard
              label="Recent Pipelines"
              value={stats.recent_pipelines}
            />
            <StatCard
              label="Routing Calls"
              value={stats.routing_llm?.total_calls ?? 0}
            />
            <StatCard
              label="Prediction Calls"
              value={stats.prediction_llm?.total_calls ?? 0}
            />
          </div>

          {stats.pipeline_timings.length > 0 && (
            <div className="mt-4">
              <h3 className="text-xs font-medium text-slate-400 mb-2">
                Recent Pipeline Timings
              </h3>
              <div className="space-y-1.5">
                {stats.pipeline_timings.map((t, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between text-xs border-b border-slate-800/40 pb-1.5"
                  >
                    <span className="text-slate-400 truncate max-w-[60%]">
                      {t.query || `Pipeline #${i + 1}`}
                    </span>
                    <div className="flex gap-3 text-slate-500">
                      {t.stages &&
                        Object.entries(t.stages).map(([stage, time]) => (
                          <span key={stage}>
                            {stage}:{" "}
                            <span className="text-slate-300">
                              {typeof time === "number"
                                ? `${time.toFixed(1)}s`
                                : time}
                            </span>
                          </span>
                        ))}
                      {t.total && (
                        <span className="font-medium text-accent">
                          {typeof t.total === "number"
                            ? `${t.total.toFixed(1)}s`
                            : t.total}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Cache Stats */}
      {cache && (
        <Card className="p-4">
          <h2 className="text-sm font-semibold mb-3">Cache</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Total Entries" value={cache.total_entries} />
            <StatCard label="Active" value={cache.active_entries} />
            <StatCard label="Expired" value={cache.expired_entries} />
            <StatCard
              label="Default TTL"
              value={`${cache.default_ttl}s`}
            />
          </div>
        </Card>
      )}

      {/* Prediction Calibration Overview */}
      {calibration && calibration.resolved > 0 && (
        <Card className="p-4">
          <h2 className="text-sm font-semibold mb-3">Prediction Performance</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard
              label="Total Predictions"
              value={calibration.total_predictions}
              sub={`${calibration.resolved} resolved`}
            />
            <StatCard
              label="Accuracy"
              value={
                calibration.accuracy !== null
                  ? `${(calibration.accuracy * 100).toFixed(1)}%`
                  : "—"
              }
              sub={`${calibration.correct}/${calibration.resolved} correct`}
            />
            <StatCard
              label="Brier Score"
              value={
                calibration.brier_score !== null
                  ? calibration.brier_score.toFixed(4)
                  : "—"
              }
              sub="Lower is better"
            />
            <StatCard
              label="Pending"
              value={calibration.total_predictions - calibration.resolved}
              sub="Awaiting results"
            />
          </div>

          {/* Favorite vs Underdog */}
          {(calibration.favorite_accuracy?.total > 0 ||
            calibration.underdog_accuracy?.total > 0) && (
            <div className="mt-3 grid grid-cols-2 gap-3">
              {calibration.favorite_accuracy?.total > 0 && (
                <StatCard
                  label="Favorite Accuracy"
                  value={
                    calibration.favorite_accuracy.accuracy !== null
                      ? `${(calibration.favorite_accuracy.accuracy * 100).toFixed(1)}%`
                      : "—"
                  }
                  sub={`${calibration.favorite_accuracy.correct}/${calibration.favorite_accuracy.total} picks`}
                />
              )}
              {calibration.underdog_accuracy?.total > 0 && (
                <StatCard
                  label="Underdog Accuracy"
                  value={
                    calibration.underdog_accuracy.accuracy !== null
                      ? `${(calibration.underdog_accuracy.accuracy * 100).toFixed(1)}%`
                      : "—"
                  }
                  sub={`${calibration.underdog_accuracy.correct}/${calibration.underdog_accuracy.total} picks`}
                />
              )}
            </div>
          )}

          {/* Weight Class Breakdown */}
          {calibration.by_weight_class &&
            Object.keys(calibration.by_weight_class).filter(
              (wc) => wc !== "Unknown"
            ).length > 0 && (
              <div className="mt-4">
                <h3 className="text-xs font-medium text-slate-400 mb-2">
                  Accuracy by Weight Class
                </h3>
                <div className="space-y-1">
                  {Object.entries(calibration.by_weight_class)
                    .filter(([wc]) => wc !== "Unknown")
                    .sort((a, b) => (b[1].total ?? 0) - (a[1].total ?? 0))
                    .map(([wc, data]) => (
                      <div
                        key={wc}
                        className="flex items-center justify-between text-xs border-b border-slate-800/40 pb-1"
                      >
                        <span className="text-slate-300">{wc}</span>
                        <div className="flex gap-3">
                          <span className="text-slate-500">
                            {data.correct}/{data.total}
                          </span>
                          <span
                            className={
                              data.accuracy !== null && data.accuracy >= 0.6
                                ? "text-emerald-400 font-medium"
                                : "text-slate-400"
                            }
                          >
                            {data.accuracy !== null
                              ? `${(data.accuracy * 100).toFixed(0)}%`
                              : "—"}
                          </span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
        </Card>
      )}

      {/* Accuracy Trend */}
      {calibration?.accuracy_trend && calibration.accuracy_trend.length > 3 && (
        <Card className="p-4">
          <h2 className="text-sm font-semibold mb-3">Accuracy Trend</h2>
          <div className="flex items-end gap-0.5 h-20">
            {calibration.accuracy_trend.slice(-30).map((point, i) => (
              <div
                key={i}
                className="flex-1 rounded-t-sm transition-all"
                style={{
                  height: `${point.rolling_accuracy * 100}%`,
                  backgroundColor:
                    point.rolling_accuracy >= 0.6
                      ? "rgb(52, 211, 153)"
                      : point.rolling_accuracy >= 0.5
                      ? "rgb(250, 204, 21)"
                      : "rgb(248, 113, 113)",
                  opacity: 0.7 + (i / 30) * 0.3,
                }}
                title={`#${point.index}: ${(point.rolling_accuracy * 100).toFixed(0)}% rolling, ${(point.cumulative_accuracy * 100).toFixed(0)}% cumulative`}
              />
            ))}
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>
              Rolling (10):{" "}
              {(
                calibration.accuracy_trend[calibration.accuracy_trend.length - 1]
                  ?.rolling_accuracy * 100
              ).toFixed(0)}
              %
            </span>
            <span>
              Cumulative:{" "}
              {(
                calibration.accuracy_trend[calibration.accuracy_trend.length - 1]
                  ?.cumulative_accuracy * 100
              ).toFixed(0)}
              %
            </span>
          </div>
        </Card>
      )}

      {/* ELO Power Rankings */}
      {elo && elo.rankings.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold">Power Rankings (ELO)</h2>
            <span className="text-[10px] text-slate-500">
              {elo.total_rated} rated fighters
            </span>
          </div>
          <div className="space-y-1">
            {elo.rankings.map((r) => (
              <div
                key={r.fighter_id}
                className="flex items-center justify-between text-xs border-b border-slate-800/40 pb-1"
              >
                <div className="flex items-center gap-2">
                  <span className="text-slate-500 w-5 text-right">
                    #{r.rank}
                  </span>
                  <span className="text-slate-200 font-medium">
                    {r.name || r.fighter_id}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-slate-500">{r.fights} fights</span>
                  <span className="font-medium text-accent w-12 text-right">
                    {Math.round(r.rating)}
                  </span>
                  <span className="w-4 text-center">{r.trend}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Quick Links */}
      <Card className="p-4">
        <h2 className="text-sm font-semibold mb-3">Quick Actions</h2>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/calibration"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 hover:border-accent/40 transition-colors"
          >
            View Calibration
          </Link>
          <Link
            href="/predictions"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 hover:border-accent/40 transition-colors"
          >
            Prediction History
          </Link>
          <Link
            href="/value-bets"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 hover:border-accent/40 transition-colors"
          >
            Value Bet Scanner
          </Link>
          <Link
            href="/events"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 hover:border-accent/40 transition-colors"
          >
            Events Browser
          </Link>
          <Link
            href="/bet-calculator"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 hover:border-accent/40 transition-colors"
          >
            Bet Calculator
          </Link>
          <Link
            href="/fighters"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 hover:border-accent/40 transition-colors"
          >
            Fighter Profiles
          </Link>
        </div>
      </Card>
    </div>
  );
}
