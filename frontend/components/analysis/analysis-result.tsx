"use client";

import { useState, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";
import { ProbabilityBar } from "@/components/ui/probability-bar";
import { EdgeBreakdown, type EdgeItem } from "@/components/ui/edge-breakdown";

type Props = {
  content: string;
  elapsedSeconds?: number | null;
  specialistCount?: number | null;
};

/** Known section headings from the coordinator pipeline. */
const SECTION_PATTERNS = [
  "Overview",
  "Style & Form",
  "Pace & Pressure",
  "Grappling & Scramble",
  "Clinch & Cage Control",
  "Aging & Career Phase",
  "Fight IQ & Gameplan",
  "Damage & Durability",
  "Judging Tendencies",
  "Metadata Snapshot",
  "Summary Takeaways",
  "Edge Summary",
  "Structured Prediction",
  "Prediction",
];

type Section = {
  title: string;
  body: string;
};

/* ────────────────────────────────────────────
   Section parser
   ──────────────────────────────────────────── */
function parseSections(text: string): Section[] {
  const lines = text.split("\n");
  const sections: Section[] = [];
  let currentTitle = "Full Analysis";
  let currentLines: string[] = [];

  for (const line of lines) {
    const headingMatch = line.match(/^#{1,3}\s+(.+)$/);
    const delimiterMatch = line.match(/^={3,}\s*(.+?)\s*={3,}$/);
    const matchedTitle = headingMatch?.[1] || delimiterMatch?.[1];

    if (matchedTitle) {
      if (currentLines.length > 0) {
        const body = currentLines.join("\n").trim();
        if (body) sections.push({ title: currentTitle, body });
      }
      currentTitle = matchedTitle.replace(/^#+\s*/, "").trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }

  if (currentLines.length > 0) {
    const body = currentLines.join("\n").trim();
    if (body) sections.push({ title: currentTitle, body });
  }

  return sections;
}

/* ────────────────────────────────────────────
   Edge Summary parser
   ──────────────────────────────────────────── */
function parseEdges(text: string): { edges: EdgeItem[]; fighterA: string; fighterB: string } {
  const edges: EdgeItem[] = [];
  let fighterA = "";
  let fighterB = "";

  const lines = text.split("\n").filter((l) => l.trim());

  for (const line of lines) {
    // Pattern: "- **Striking**: Pereira — Higher SLpM and accuracy"
    // or "- Striking: Pereira - Higher SLpM"
    const m = line.match(
      /[-*•]\s*\*{0,2}([^*:]+?)\*{0,2}\s*:\s*([^—–\-]+?)(?:\s*[—–\-]\s*(.+))?$/
    );
    if (m) {
      const domain = m[1].trim();
      const winner = m[2].trim();
      const reason = m[3]?.trim() || "";
      edges.push({ domain, winner, reason });

      // Try to identify fighters from non-Even winners
      if (winner.toLowerCase() !== "even" && winner.toLowerCase() !== "draw") {
        if (!fighterA) fighterA = winner;
        else if (winner !== fighterA && !fighterB) fighterB = winner;
      }
    }
  }

  return { edges, fighterA, fighterB };
}

/* ────────────────────────────────────────────
   Win Probability parser
   ──────────────────────────────────────────── */
type WinProb = { fighterA: string; fighterB: string; probA: number; probB: number };

function parseWinProbability(text: string): WinProb | null {
  // "Pereira: 62%"  or  "Pereira — 62%"
  const matches = [...text.matchAll(/([A-Z][a-zA-Z'.\- ]+?)\s*[:\-—]\s*(\d{1,3})%/g)];
  if (matches.length >= 2) {
    return {
      fighterA: matches[0][1].trim(),
      fighterB: matches[1][1].trim(),
      probA: parseInt(matches[0][2]),
      probB: parseInt(matches[1][2]),
    };
  }
  return null;
}

/* ────────────────────────────────────────────
   Method Probabilities parser
   ──────────────────────────────────────────── */
type MethodProb = { method: string; pct: number; color: string };

function parseMethodProbabilities(text: string): MethodProb[] {
  const methods: MethodProb[] = [];
  const colorMap: Record<string, string> = {
    ko: "#f97316",
    tko: "#f97316",
    "ko/tko": "#f97316",
    submission: "#a78bfa",
    sub: "#a78bfa",
    decision: "#38bdf8",
    dec: "#38bdf8",
    "unanimous decision": "#38bdf8",
    "split decision": "#60a5fa",
  };

  const lines = text.split("\n");
  for (const line of lines) {
    const m = line.match(/[-*•]\s*\*{0,2}([^*:]+?)\*{0,2}\s*[:\-—]\s*(\d{1,3})%/);
    if (m) {
      const method = m[1].trim();
      const pct = parseInt(m[2]);
      const key = method.toLowerCase().replace(/\//g, "/");
      const color =
        Object.entries(colorMap).find(([k]) => key.includes(k))?.[1] || "#64748b";
      methods.push({ method, pct, color });
    }
  }
  return methods;
}

/* ────────────────────────────────────────────
   Key/Risk Factors parser
   ──────────────────────────────────────────── */
function parseFactors(text: string): string[] {
  const factors: string[] = [];
  const lines = text.split("\n");
  for (const line of lines) {
    const m = line.match(/^\s*(?:\d+[.)]\s*|[-*•]\s+)(.+)/);
    if (m) factors.push(m[1].trim());
  }
  return factors;
}

/* ────────────────────────────────────────────
   Markdown renderer
   ──────────────────────────────────────────── */
function MarkdownBlock({ text }: { text: string }) {
  return (
    <div className="prose-analysis">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

/* ────────────────────────────────────────────
   Visual: Method Probability Segments
   ──────────────────────────────────────────── */
function MethodSegments({ methods }: { methods: MethodProb[] }) {
  const total = methods.reduce((s, m) => s + m.pct, 0) || 1;

  return (
    <div className="space-y-3">
      {/* Horizontal segmented bar */}
      <div className="flex h-4 rounded-full overflow-hidden bg-slate-800/50 border border-slate-700/30">
        {methods.map((m, i) => (
          <div
            key={m.method}
            className="flex items-center justify-center transition-all duration-500"
            style={{
              width: `${(m.pct / total) * 100}%`,
              backgroundColor: m.color,
              opacity: 0.7,
              borderRight:
                i < methods.length - 1 ? "1px solid rgba(0,0,0,0.3)" : "none",
            }}
          >
            {m.pct >= 15 && (
              <span className="text-[9px] font-bold text-white/90 drop-shadow-sm">
                {m.pct}%
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap">
        {methods.map((m) => (
          <div key={m.method} className="flex items-center gap-1.5">
            <div
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: m.color, opacity: 0.8 }}
            />
            <span className="text-[10px] text-slate-400">
              {m.method}:{" "}
              <span className="text-slate-200 font-semibold">{m.pct}%</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────
   Visual: Callout Box
   ──────────────────────────────────────────── */
function CalloutBox({
  title,
  items,
  variant = "info",
}: {
  title: string;
  items: string[];
  variant?: "info" | "warning";
}) {
  if (!items.length) return null;

  const isWarning = variant === "warning";

  return (
    <div
      className={`rounded-lg border p-4 ${
        isWarning
          ? "border-amber-500/20 bg-amber-500/5"
          : "border-accent/20 bg-accent/5"
      }`}
    >
      <h4
        className={`text-xs font-bold uppercase tracking-wide mb-2.5 ${
          isWarning ? "text-amber-400" : "text-accent"
        }`}
      >
        {isWarning ? "\u26A0 " : ""}
        {title}
      </h4>
      <ol className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-xs text-slate-300 leading-relaxed">
            <span
              className={`font-bold tabular-nums shrink-0 ${
                isWarning ? "text-amber-500/60" : "text-accent/50"
              }`}
            >
              {i + 1}.
            </span>
            {item}
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ────────────────────────────────────────────
   Section content renderers
   ──────────────────────────────────────────── */
function renderSectionContent(section: Section) {
  const titleLower = section.title.toLowerCase();

  // Edge Summary -> visual edge breakdown
  if (titleLower.includes("edge summary")) {
    const { edges, fighterA, fighterB } = parseEdges(section.body);
    if (edges.length > 0) {
      return (
        <div className="space-y-4">
          <EdgeBreakdown
            edges={edges}
            fighterA={fighterA}
            fighterB={fighterB}
          />
          {/* Also show raw text below for completeness */}
          <details className="group">
            <summary className="text-[10px] text-slate-600 cursor-pointer hover:text-slate-400 transition-colors">
              Show raw text
            </summary>
            <div className="mt-2 opacity-60">
              <MarkdownBlock text={section.body} />
            </div>
          </details>
        </div>
      );
    }
  }

  // Prediction / Structured Prediction -> probability + methods
  if (
    titleLower.includes("prediction") ||
    titleLower.includes("structured prediction")
  ) {
    const winProb = parseWinProbability(section.body);
    const methods = parseMethodProbabilities(section.body);

    // Try to find key factors and risk factors within the body
    const keyFactorsMatch = section.body.match(
      /(?:key factors?|deciding factors?|critical factors?)[\s:]*\n((?:\s*[-*•\d].*\n?)+)/i
    );
    const riskFactorsMatch = section.body.match(
      /(?:risk factors?|upset factors?|wild cards?)[\s:]*\n((?:\s*[-*•\d].*\n?)+)/i
    );

    const keyFactors = keyFactorsMatch ? parseFactors(keyFactorsMatch[1]) : [];
    const riskFactors = riskFactorsMatch ? parseFactors(riskFactorsMatch[1]) : [];

    return (
      <div className="space-y-5">
        {/* Win Probability Meter */}
        {winProb && (
          <div>
            <h4 className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-2">
              Win Probability
            </h4>
            <ProbabilityBar
              labelA={winProb.fighterA}
              labelB={winProb.fighterB}
              valueA={winProb.probA}
              valueB={winProb.probB}
            />
          </div>
        )}

        {/* Method Probabilities */}
        {methods.length > 0 && (
          <div>
            <h4 className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-2">
              Method Probabilities
            </h4>
            <MethodSegments methods={methods} />
          </div>
        )}

        {/* Key Factors */}
        {keyFactors.length > 0 && (
          <CalloutBox title="Key Factors" items={keyFactors} variant="info" />
        )}

        {/* Risk Factors */}
        {riskFactors.length > 0 && (
          <CalloutBox title="Risk Factors" items={riskFactors} variant="warning" />
        )}

        {/* Full markdown content */}
        <MarkdownBlock text={section.body} />
      </div>
    );
  }

  // Default: markdown
  return <MarkdownBlock text={section.body} />;
}

/* ────────────────────────────────────────────
   Main Component
   ──────────────────────────────────────────── */
export function AnalysisResult({ content, elapsedSeconds, specialistCount }: Props) {
  const sections = useMemo(() => parseSections(content), [content]);
  const hasSections = sections.length > 1;

  // Try to extract key/risk factors from full content for the summary tab
  const globalKeyFactors = useMemo(() => {
    const m = content.match(
      /(?:key factors?|deciding factors?|critical factors?)[\s:]*\n((?:\s*[-*•\d].*\n?)+)/i
    );
    return m ? parseFactors(m[1]) : [];
  }, [content]);

  const globalRiskFactors = useMemo(() => {
    const m = content.match(
      /(?:risk factors?|upset factors?|wild cards?)[\s:]*\n((?:\s*[-*•\d].*\n?)+)/i
    );
    return m ? parseFactors(m[1]) : [];
  }, [content]);

  // Build tab items
  const tabItems = useMemo(() => {
    const items = [
      {
        id: "full",
        label: "Full Analysis",
        content: (
          <div className="space-y-5">
            <MarkdownBlock text={content} />
            {/* Global callouts at the end of full analysis */}
            {globalKeyFactors.length > 0 && (
              <CalloutBox title="Key Factors" items={globalKeyFactors} variant="info" />
            )}
            {globalRiskFactors.length > 0 && (
              <CalloutBox title="Risk Factors" items={globalRiskFactors} variant="warning" />
            )}
          </div>
        ),
      },
    ];

    if (hasSections) {
      for (const section of sections) {
        items.push({
          id: section.title.toLowerCase().replace(/\s+/g, "-"),
          label: section.title,
          content: renderSectionContent(section),
        });
      }
    }

    return items;
  }, [content, sections, hasSections, globalKeyFactors, globalRiskFactors]);

  return (
    <Card variant="glow" className="p-5 space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gradient">Engine Output</h2>
        <div className="flex items-center gap-3">
          {elapsedSeconds != null && (
            <span className="text-xs text-slate-500 tabular-nums">
              {elapsedSeconds}s
            </span>
          )}
          {specialistCount != null && specialistCount > 0 && (
            <span className="text-[10px] text-slate-600 border border-slate-800 rounded-md px-1.5 py-0.5">
              {specialistCount} specialists
            </span>
          )}
        </div>
      </div>

      {/* Pipeline breadcrumb */}
      <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
        {["Router", "Specialists", "Coordinator", "Critic"].map((stage, i, arr) => (
          <span key={stage} className="flex items-center gap-1.5">
            <span className="text-slate-400 font-medium">{stage}</span>
            {i < arr.length - 1 && (
              <svg
                className="h-2.5 w-2.5 text-slate-700"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            )}
          </span>
        ))}
      </div>

      {/* Tabs content */}
      <Tabs items={tabItems} />

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-800/50">
        <span className="text-[10px] text-slate-600">
          Multi-agent analysis pipeline
        </span>
        <div className="flex items-center gap-2">
          {elapsedSeconds != null && (
            <span className="text-[10px] text-slate-600">
              Completed in {elapsedSeconds}s
            </span>
          )}
          {specialistCount != null && specialistCount > 0 && (
            <span className="text-[10px] text-slate-600">
              {specialistCount} specialists consulted
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}
