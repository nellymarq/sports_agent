"use client";

import clsx from "classnames";

type Props = {
  labelA: string;
  labelB: string;
  valueA: number;
  valueB: number;
  className?: string;
};

export function ProbabilityBar({ labelA, labelB, valueA, valueB, className }: Props) {
  const total = valueA + valueB || 1;
  const pctA = Math.round((valueA / total) * 100);
  const pctB = 100 - pctA;
  const favored = pctA >= pctB ? "A" : "B";

  return (
    <div className={clsx("w-full", className)}>
      {/* Labels row */}
      <div className="flex items-center justify-between mb-1.5">
        <span
          className={clsx(
            "text-xs font-semibold",
            favored === "A" ? "text-accent" : "text-slate-400"
          )}
        >
          {labelA}
        </span>
        <span
          className={clsx(
            "text-xs font-semibold",
            favored === "B" ? "text-red-400" : "text-slate-400"
          )}
        >
          {labelB}
        </span>
      </div>

      {/* Bar */}
      <div className="relative h-8 rounded-lg overflow-hidden bg-slate-800/50 border border-slate-700/40">
        {/* Fighter A side */}
        <div
          className="absolute inset-y-0 left-0 flex items-center justify-center transition-all duration-700 ease-out"
          style={{
            width: `${pctA}%`,
            background:
              favored === "A"
                ? "linear-gradient(90deg, rgba(0,224,255,0.25) 0%, rgba(0,224,255,0.45) 100%)"
                : "linear-gradient(90deg, rgba(100,116,139,0.2) 0%, rgba(100,116,139,0.3) 100%)",
          }}
        >
          <span
            className={clsx(
              "text-xs font-bold tabular-nums",
              favored === "A" ? "text-accent" : "text-slate-400"
            )}
          >
            {pctA}%
          </span>
        </div>

        {/* Divider */}
        <div
          className="absolute inset-y-0 w-px bg-white/20"
          style={{ left: `${pctA}%` }}
        />

        {/* Fighter B side */}
        <div
          className="absolute inset-y-0 right-0 flex items-center justify-center transition-all duration-700 ease-out"
          style={{
            width: `${pctB}%`,
            background:
              favored === "B"
                ? "linear-gradient(270deg, rgba(239,68,68,0.25) 0%, rgba(239,68,68,0.45) 100%)"
                : "linear-gradient(270deg, rgba(100,116,139,0.2) 0%, rgba(100,116,139,0.3) 100%)",
          }}
        >
          <span
            className={clsx(
              "text-xs font-bold tabular-nums",
              favored === "B" ? "text-red-400" : "text-slate-400"
            )}
          >
            {pctB}%
          </span>
        </div>
      </div>
    </div>
  );
}
