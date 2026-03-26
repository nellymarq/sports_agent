"use client";

import { useEffect, useState, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const PIPELINE_STAGES = [
  { key: "retrieval", label: "Retrieving context & fighter data", time: 5 },
  { key: "routing", label: "Routing to specialists", time: 3 },
  { key: "supervisor", label: "Building task plan", time: 5 },
  { key: "orchestrator", label: "Running specialists & generating analysis", time: 25 },
];

const TOTAL_EST_TIME = 38; // average pipeline time in seconds

type Props = {
  /** Current pipeline stage from SSE, or empty for time-based fallback. */
  stage?: string;
};

export function AnalysisLoading({ stage }: Props) {
  const [fallbackStage, setFallbackStage] = useState(0);
  const [elapsed, setElapsed] = useState(0);
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

  // Elapsed time counter
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const activeIndex = useMemo(() => {
    if (!isStreaming) return fallbackStage;
    const idx = PIPELINE_STAGES.findIndex((s) => s.key === stage);
    return idx >= 0 ? idx : PIPELINE_STAGES.length - 1;
  }, [isStreaming, stage, fallbackStage]);

  // Progress percentage based on stages completed
  const progressPct = useMemo(() => {
    const stageWeight = 100 / PIPELINE_STAGES.length;
    const completed = activeIndex * stageWeight;
    // Add partial progress within current stage based on elapsed time
    const currentStageTime = PIPELINE_STAGES[activeIndex]?.time || 10;
    const stageElapsed = Math.min(elapsed, currentStageTime);
    const partial = (stageElapsed / currentStageTime) * stageWeight * 0.8; // 80% max within stage
    return Math.min(completed + partial, 95); // Never show 100% until done
  }, [activeIndex, elapsed]);

  // Estimated time remaining
  const estRemaining = Math.max(0, TOTAL_EST_TIME - elapsed);

  const isOrchestrator = PIPELINE_STAGES[activeIndex]?.key === "orchestrator";

  return (
    <div className="space-y-4 animate-fade-in">
      <Card variant="glow" className="p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-200">
            Pipeline running...
          </h2>
          <div className="flex items-center gap-3">
            <span className="text-[10px] text-slate-500 tabular-nums">
              {elapsed}s elapsed
            </span>
            {estRemaining > 0 && (
              <span className="text-[10px] text-accent/60 tabular-nums">
                ~{estRemaining}s remaining
              </span>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="relative h-1.5 rounded-full bg-slate-800/70 overflow-hidden mb-5">
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all duration-1000 ease-out"
            style={{
              width: `${progressPct}%`,
              background:
                "linear-gradient(90deg, rgba(0,224,255,0.6) 0%, rgba(0,224,255,0.9) 100%)",
              boxShadow: "0 0 12px rgba(0,224,255,0.4)",
            }}
          />
          {/* Shimmer on progress bar */}
          <div
            className="absolute inset-y-0 left-0 rounded-full overflow-hidden"
            style={{ width: `${progressPct}%` }}
          >
            <div
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.15) 50%, transparent 100%)",
                backgroundSize: "200% 100%",
                animation: "shimmer 1.5s ease-in-out infinite",
              }}
            />
          </div>
        </div>

        {/* Stage list */}
        <div className="space-y-2.5">
          {PIPELINE_STAGES.map((s, i) => (
            <div
              key={s.key}
              className={`flex items-center gap-3 text-xs transition-all duration-500 ${
                i <= activeIndex ? "opacity-100" : "opacity-30"
              }`}
            >
              {/* Stage dot with accent ring pulse */}
              <div className="relative flex items-center justify-center">
                <div
                  className={`h-2 w-2 rounded-full transition-all duration-300 ${
                    i < activeIndex
                      ? "bg-green-400"
                      : i === activeIndex
                      ? "bg-accent"
                      : "bg-slate-600"
                  }`}
                />
                {i === activeIndex && (
                  <div className="absolute inset-0 -m-1 rounded-full ring-pulse-accent" />
                )}
              </div>

              {/* Label */}
              <span
                className={`transition-colors duration-300 ${
                  i === activeIndex
                    ? "text-accent font-medium"
                    : i < activeIndex
                    ? "text-slate-400"
                    : "text-slate-600"
                }`}
              >
                {s.label}
              </span>

              {/* Status */}
              <span className="ml-auto">
                {i < activeIndex && (
                  <span className="text-green-400/70 flex items-center gap-1">
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    done
                  </span>
                )}
                {i === activeIndex && (
                  <span className="text-accent/50 animate-pulse">processing</span>
                )}
              </span>
            </div>
          ))}
        </div>

        {/* Orchestrator detail */}
        {isOrchestrator && (
          <div className="mt-4 pt-3 border-t border-slate-800/50">
            <div className="flex items-center gap-2">
              <div className="h-1 w-1 rounded-full bg-accent animate-ping" />
              <span className="text-[10px] text-accent/70 font-medium">
                Running 16 specialists in parallel...
              </span>
            </div>
            <p className="text-[10px] text-slate-600 mt-1 ml-3">
              Striking, grappling, cardio, fight IQ, damage analysis and more
            </p>
          </div>
        )}
      </Card>

      {/* Skeleton preview */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-5 w-44" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-11/12" />
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-4/6" />
        </div>
        <div className="mt-5 space-y-3">
          <Skeleton className="h-8 w-full rounded-lg" />
          <div className="grid grid-cols-3 gap-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-full" />
          </div>
        </div>
      </Card>
    </div>
  );
}
