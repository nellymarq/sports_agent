"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";

type BucketStats = { total: number; correct: number; accuracy: number };

type CalibrationData = {
  total_predictions: number;
  resolved: number;
  correct: number;
  accuracy: number | null;
  brier_score: number | null;
  by_tier: Record<string, number | BucketStats>;
  by_probability: Record<string, BucketStats>;
  by_method: Record<string, BucketStats>;
  by_event: Record<string, BucketStats>;
};

function Stat({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-xl font-semibold ${color || ""}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function BucketTable({
  data,
  title,
}: {
  data: Record<string, BucketStats | number>;
  title: string;
}) {
  const entries = Object.entries(data);
  if (!entries.length)
    return <p className="text-xs text-slate-500">No data yet.</p>;

  return (
    <div>
      <h3 className="text-sm font-semibold mb-2">{title}</h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-800 text-slate-400">
            <th className="text-left py-1">Bucket</th>
            <th className="text-right py-1">Total</th>
            <th className="text-right py-1">Correct</th>
            <th className="text-right py-1">Accuracy</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([bucket, stats]) => {
            // Handle both old format (number) and new format (object)
            const s = typeof stats === "number"
              ? { total: 0, correct: 0, accuracy: stats }
              : stats;
            return (
              <tr key={bucket} className="border-b border-slate-800/50">
                <td className="py-1.5 capitalize">{bucket.replace(/_/g, " ")}</td>
                <td className="text-right">{s.total}</td>
                <td className="text-right">{s.correct}</td>
                <td className="text-right">
                  {s.accuracy != null ? `${(s.accuracy * 100).toFixed(1)}%` : "N/A"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AccuracyBar({ accuracy }: { accuracy: number | null }) {
  if (accuracy === null) return null;
  const pct = accuracy * 100;
  const color =
    pct >= 70 ? "bg-emerald-500" : pct >= 55 ? "bg-blue-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="w-full bg-slate-800 rounded-full h-2 mt-2">
      <div
        className={`h-2 rounded-full ${color} transition-all`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

export default function CalibrationPage() {
  const [data, setData] = useState<CalibrationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/calibration`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((d) => setData(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Prediction Calibration</h1>
        <Link href="/" className="text-xs text-accent hover:underline">
          &larr; Home
        </Link>
      </div>

      {loading && (
        <Card className="p-5">
          <p className="text-sm text-slate-400 animate-pulse">
            Loading calibration data...
          </p>
        </Card>
      )}

      {error && (
        <Card className="p-5 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {data && (
        <>
          {/* Overview stats */}
          <Card className="p-5">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Stat
                label="Total Predictions"
                value={String(data.total_predictions)}
              />
              <Stat
                label="Resolved"
                value={String(data.resolved || 0)}
              />
              <Stat
                label="Accuracy"
                value={
                  data.accuracy != null
                    ? `${(data.accuracy * 100).toFixed(1)}%`
                    : "N/A"
                }
                color={
                  data.accuracy != null && data.accuracy >= 0.6
                    ? "text-emerald-400"
                    : data.accuracy != null && data.accuracy >= 0.5
                    ? "text-amber-400"
                    : ""
                }
              />
              <Stat
                label="Brier Score"
                value={
                  data.brier_score != null
                    ? data.brier_score.toFixed(4)
                    : "N/A"
                }
                sub="Lower is better"
              />
            </div>
            <AccuracyBar accuracy={data.accuracy} />
          </Card>

          {/* Tier and Probability breakdowns */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-5">
              <BucketTable
                data={data.by_tier || {}}
                title="By Confidence Tier"
              />
            </Card>
            <Card className="p-5">
              <BucketTable
                data={data.by_probability || {}}
                title="By Probability Bucket"
              />
            </Card>
          </div>

          {/* Method and Event breakdowns */}
          <div className="grid gap-4 sm:grid-cols-2">
            {data.by_method && Object.keys(data.by_method).length > 0 && (
              <Card className="p-5">
                <BucketTable
                  data={data.by_method}
                  title="By Method Prediction"
                />
              </Card>
            )}
            {data.by_event && Object.keys(data.by_event).length > 0 && (
              <Card className="p-5">
                <BucketTable
                  data={data.by_event}
                  title="By Event"
                />
              </Card>
            )}
          </div>

          {data.total_predictions === 0 && (
            <p className="text-xs text-slate-500 text-center">
              No predictions tracked yet. Run an analysis to start building
              calibration data.
            </p>
          )}

          {/* Calibration guide */}
          <Card className="p-4 bg-slate-900/50">
            <h3 className="text-xs font-semibold text-slate-400 mb-2">
              Calibration Guide
            </h3>
            <div className="text-xs text-slate-500 space-y-1">
              <p>A well-calibrated model should have accuracy close to the predicted probability:</p>
              <p>- 50-60% bucket should have ~55% accuracy</p>
              <p>- 60-70% bucket should have ~65% accuracy</p>
              <p>- 70-80% bucket should have ~75% accuracy</p>
              <p>- Brier score below 0.20 is good, below 0.15 is excellent</p>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
