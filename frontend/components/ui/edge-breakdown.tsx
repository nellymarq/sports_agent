"use client";

import clsx from "classnames";

export type EdgeItem = {
  domain: string;
  winner: string;
  reason?: string;
};

type Props = {
  edges: EdgeItem[];
  fighterA?: string;
  fighterB?: string;
  className?: string;
};

export function EdgeBreakdown({ edges, fighterA, fighterB, className }: Props) {
  if (!edges.length) return null;

  return (
    <div className={clsx("w-full space-y-2", className)}>
      {/* Legend */}
      <div className="flex items-center gap-4 mb-3">
        {fighterA && (
          <div className="flex items-center gap-1.5">
            <div className="h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_6px_rgba(0,224,255,0.5)]" />
            <span className="text-[10px] text-slate-400 font-medium">{fighterA}</span>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-slate-600" />
          <span className="text-[10px] text-slate-400 font-medium">Even</span>
        </div>
        {fighterB && (
          <div className="flex items-center gap-1.5">
            <div className="h-2.5 w-2.5 rounded-full bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
            <span className="text-[10px] text-slate-400 font-medium">{fighterB}</span>
          </div>
        )}
      </div>

      {/* Edge rows */}
      {edges.map((edge, i) => {
        const isEven =
          edge.winner.toLowerCase() === "even" ||
          edge.winner.toLowerCase() === "draw" ||
          edge.winner === "";
        const isA =
          !isEven &&
          fighterA &&
          edge.winner.toLowerCase().includes(fighterA.split(" ").pop()?.toLowerCase() || "___");
        const isB = !isEven && !isA;

        return (
          <div
            key={`${edge.domain}-${i}`}
            className="group relative rounded-lg border border-slate-800/50 bg-slate-900/30 hover:bg-slate-800/30 transition-all duration-200"
          >
            <div className="flex items-center gap-3 px-3 py-2.5">
              {/* Direction indicator - left bar */}
              <div
                className={clsx(
                  "absolute left-0 top-0 bottom-0 w-0.5 rounded-l-lg transition-all duration-300",
                  isA
                    ? "bg-accent shadow-[0_0_8px_rgba(0,224,255,0.4)]"
                    : isB
                    ? "bg-red-400 shadow-[0_0_8px_rgba(239,68,68,0.4)]"
                    : "bg-slate-600"
                )}
              />

              {/* Domain label */}
              <span className="text-xs font-semibold text-slate-200 w-24 shrink-0">
                {edge.domain}
              </span>

              {/* Visual bar */}
              <div className="flex-1 h-2 rounded-full bg-slate-800/70 overflow-hidden relative">
                {isA && (
                  <div
                    className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-accent/60 to-accent/30 transition-all duration-500"
                    style={{ width: "70%" }}
                  />
                )}
                {isB && (
                  <div
                    className="absolute inset-y-0 right-0 rounded-full bg-gradient-to-l from-red-400/60 to-red-400/30 transition-all duration-500"
                    style={{ width: "70%" }}
                  />
                )}
                {isEven && (
                  <div className="absolute inset-y-0 left-1/4 right-1/4 rounded-full bg-slate-600/50" />
                )}
              </div>

              {/* Winner badge */}
              <span
                className={clsx(
                  "text-[10px] font-bold uppercase tracking-wide w-20 text-right shrink-0",
                  isA ? "text-accent" : isB ? "text-red-400" : "text-slate-500"
                )}
              >
                {isEven ? "Even" : edge.winner.split(" ").pop()}
              </span>
            </div>

            {/* Reason tooltip on hover */}
            {edge.reason && (
              <div className="px-3 pb-2 pt-0 hidden group-hover:block animate-fade-in">
                <p className="text-[10px] text-slate-500 leading-relaxed pl-[calc(6rem+0.75rem)]">
                  {edge.reason}
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
