"use client";

import { useState, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";

type Props = {
  content: string;
  elapsedSeconds?: number | null;
};

/** Known section headings from the coordinator pipeline. */
const SECTION_PATTERNS = [
  "Overview",
  "Style & Form",
  "Pace & Pressure",
  "Grappling & Scramble",
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

function parseSections(text: string): Section[] {
  // Try to split on markdown headings (## or ###) or === DELIMITERS ===
  const lines = text.split("\n");
  const sections: Section[] = [];
  let currentTitle = "Full Analysis";
  let currentLines: string[] = [];

  for (const line of lines) {
    // Match markdown headings: ## Title or ### Title
    const headingMatch = line.match(/^#{1,3}\s+(.+)$/);
    // Match delimiter style: === TITLE ===
    const delimiterMatch = line.match(/^={3,}\s*(.+?)\s*={3,}$/);

    const matchedTitle = headingMatch?.[1] || delimiterMatch?.[1];

    if (matchedTitle) {
      // Save previous section if it has content
      if (currentLines.length > 0) {
        const body = currentLines.join("\n").trim();
        if (body) {
          sections.push({ title: currentTitle, body });
        }
      }
      currentTitle = matchedTitle.replace(/^#+\s*/, "").trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }

  // Push final section
  if (currentLines.length > 0) {
    const body = currentLines.join("\n").trim();
    if (body) {
      sections.push({ title: currentTitle, body });
    }
  }

  return sections;
}

function MarkdownBlock({ text }: { text: string }) {
  return (
    <div className="prose prose-invert prose-sm max-w-none prose-headings:text-slate-100 prose-p:text-slate-300 prose-strong:text-slate-100 prose-li:text-slate-300 prose-a:text-accent">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

export function AnalysisResult({ content, elapsedSeconds }: Props) {
  const sections = useMemo(() => parseSections(content), [content]);
  const hasSections = sections.length > 1;

  // Build tab items: "Full" tab + individual section tabs
  const tabItems = useMemo(() => {
    const items = [
      {
        id: "full",
        label: "Full Analysis",
        content: <MarkdownBlock text={content} />,
      },
    ];

    if (hasSections) {
      for (const section of sections) {
        items.push({
          id: section.title.toLowerCase().replace(/\s+/g, "-"),
          label: section.title,
          content: <MarkdownBlock text={section.body} />,
        });
      }
    }

    return items;
  }, [content, sections, hasSections]);

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Engine Output</h2>
        <div className="flex items-center gap-3">
          {elapsedSeconds != null && (
            <span className="text-xs text-slate-500">
              {elapsedSeconds}s
            </span>
          )}
          <span className="text-xs text-slate-400">
            Router → Specialists → Coordinator → Critic
          </span>
        </div>
      </div>
      <Tabs items={tabItems} />
    </Card>
  );
}
