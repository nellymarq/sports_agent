"use client";

import { useEffect, useState, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const PIPELINE_STAGES = [
  { key: "retrieval", label: "Retrieving context & fighter data" },
  { key: "routing", label: "Routing to specialists" },
  { key: "supervisor", label: "Building task plan" },
  { key: "orchestrator", label: "Running specialists & generating analysis" },
];

type Props = {
  /** Current pipeline stage from SSE, or empty for time-based fallback. */
  stage?: string;
};

export function AnalysisLoading({ stage }: Props) {
  const [fallbackStage, setFallbackStage] = useState(0);
  const isStreaming = !!stage;

  // Time-based fallback when no SSE stage is available
  useEffect(() => {
    if (isStreaming) return;
    const timers = [
      setTimeout(() => setFallbackStage(1), 4000),
      setTimeout(() => setFallbackStage(2), 8000),
      setTimeout(() => setFallbackStage(3), 15000),
    ];
    return () => timers.forEach(clearTimeout);
  }, [isStreaming]);

  const activeIndex = useMemo(() => {
    if (!isStreaming) return fallbackStage;
    const idx = PIPELINE_STAGES.findIndex((s) => s.key === stage);
    return idx >= 0 ? idx : PIPELINE_STAGES.length - 1;
  }, [isStreaming, stage, fallbackStage]);

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <h2 className="text-sm font-semibold mb-3 text-slate-300">
          Pipeline running...
        </h2>
        <div className="space-y-2">
          {PIPELINE_STAGES.map((s, i) => (
            <div
              key={s.key}
              className={`flex items-center gap-2 text-xs transition-opacity duration-300 ${
                i <= activeIndex ? "opacity-100" : "opacity-30"
              }`}
            >
              <div
                className={`h-1.5 w-1.5 rounded-full ${
                  i < activeIndex
                    ? "bg-green-400"
                    : i === activeIndex
                    ? "bg-accent animate-pulse"
                    : "bg-slate-600"
                }`}
              />
              <span
                className={
                  i === activeIndex
                    ? "text-accent"
                    : i < activeIndex
                    ? "text-slate-400"
                    : "text-slate-600"
                }
              >
                {s.label}
              </span>
              {i < activeIndex && (
                <span className="text-green-400/60 ml-auto">done</span>
              )}
            </div>
          ))}
        </div>
      </Card>
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-4/6" />
        </div>
      </Card>
    </div>
  );
}
