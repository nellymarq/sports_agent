"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";

type CalibrationData = {
  total_predictions: number;
  resolved_predictions: number;
  accuracy: number | null;
  brier_score: number | null;
  by_tier: Record<
    string,
    { total: number; correct: number; accuracy: number }
  >;
  by_probability: Record<
    string,
    { total: number; correct: number; accuracy: number }
  >;
};

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function TierTable({
  data,
  title,
}: {
  data: Record<string, { total: number; correct: number; accuracy: number }>;
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
          {entries.map(([bucket, stats]) => (
            <tr key={bucket} className="border-b border-slate-800/50">
              <td className="py-1.5">{bucket}</td>
              <td className="text-right">{stats.total}</td>
              <td className="text-right">{stats.correct}</td>
              <td className="text-right">
                {(stats.accuracy * 100).toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
          <Card className="p-5">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Stat
                label="Total Predictions"
                value={String(data.total_predictions)}
              />
              <Stat
                label="Resolved"
                value={String(data.resolved_predictions)}
              />
              <Stat
                label="Accuracy"
                value={
                  data.accuracy != null
                    ? `${(data.accuracy * 100).toFixed(1)}%`
                    : "N/A"
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
          </Card>

          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-5">
              <TierTable
                data={data.by_tier || {}}
                title="By Confidence Tier"
              />
            </Card>
            <Card className="p-5">
              <TierTable
                data={data.by_probability || {}}
                title="By Probability Bucket"
              />
            </Card>
          </div>

          {data.total_predictions === 0 && (
            <p className="text-xs text-slate-500 text-center">
              No predictions tracked yet. Run an analysis to start building
              calibration data.
            </p>
          )}
        </>
      )}
    </div>
  );
}
