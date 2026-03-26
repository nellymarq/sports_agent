import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";

type Props = {
  query: string;
  children: ReactNode;
};

export function AnalysisLayout({ query, children }: Props) {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 space-y-6">
      {/* Hero glow background */}
      <div className="relative">
        {/* Subtle radial glow behind query card */}
        <div
          className="absolute -inset-6 -top-10 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse at center top, rgba(0,224,255,0.06) 0%, transparent 70%)",
          }}
        />

        <Card variant="bordered" className="p-5 relative z-10">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">
                Analysis Request
              </h1>
              {/* Styled code block for query */}
              <div className="rounded-lg bg-black/40 border border-slate-800/60 px-4 py-3">
                <p className="text-sm text-slate-200 whitespace-pre-wrap font-mono leading-relaxed">
                  {query}
                </p>
              </div>
            </div>
          </div>

          {/* Pipeline stages breadcrumb */}
          <div className="flex items-center gap-1 mt-4 pt-3 border-t border-slate-800/40">
            {[
              { label: "Query", icon: "Q" },
              { label: "Router", icon: "R" },
              { label: "Specialists", icon: "S" },
              { label: "Coordinator", icon: "C" },
              { label: "Critic", icon: "K" },
              { label: "Output", icon: "O" },
            ].map((stage, i, arr) => (
              <div key={stage.label} className="flex items-center gap-1">
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-800/30 border border-slate-800/40">
                  <span className="text-[9px] font-bold text-accent/40 tabular-nums">
                    {stage.icon}
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium">
                    {stage.label}
                  </span>
                </div>
                {i < arr.length - 1 && (
                  <svg
                    className="h-2.5 w-2.5 text-slate-700 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {children}
    </div>
  );
}
