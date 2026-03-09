"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const EXAMPLE_QUERIES = [
  "Break down UFC 313 main event: Pereira vs Ankalaev",
  "Who wins between Islam Makhachev and Arman Tsarukyan?",
  "Analyze the style matchup for Merab Dvalishvili vs Umar Nurmagomedov",
  "Give me a full breakdown of the UFC 313 card",
];

export default function HomePage() {
  const [query, setQuery] = useState("");

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 space-y-6">
      <Card className="p-8 bg-surface border-slate-800 shadow-lg shadow-black/40">
        <h1 className="text-2xl font-semibold tracking-tight mb-2">
          Fight-week level UFC analysis.
        </h1>
        <p className="text-sm text-slate-400 mb-6">
          Ask about a matchup, event, or fighter. The engine routes through
          14 specialist agents, merges analysis, and returns a unified breakdown
          with a structured prediction.
        </p>

        <label className="block text-xs font-medium text-slate-400 mb-1">
          Question
        </label>
        <textarea
          className="w-full rounded-lg bg-black/40 border border-slate-800 px-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent resize-none h-28"
          placeholder="Example: Break down UFC 313 main event and tell me who you favor."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && query.trim()) {
              e.preventDefault();
              window.location.href = `/analyze?q=${encodeURIComponent(query)}`;
            }
          }}
        />

        <div className="mt-4 flex justify-between items-center">
          <span className="text-xs text-slate-500">
            Pipeline: retrieval → router → specialists → coordinator → prediction → critic
          </span>
          <Link
            href={{
              pathname: "/analyze",
              query: query ? { q: query } : {},
            }}
          >
            <Button disabled={!query.trim()}>Analyze</Button>
          </Link>
        </div>
      </Card>

      <div>
        <h2 className="text-xs font-medium text-slate-500 mb-2 px-1">
          Try an example
        </h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {EXAMPLE_QUERIES.map((eq) => (
            <Link
              key={eq}
              href={{
                pathname: "/analyze",
                query: { q: eq },
              }}
              className="rounded-lg border border-slate-800/60 bg-surface/50 px-3 py-2.5 text-xs text-slate-400 hover:border-accent/40 hover:text-slate-200 transition-colors"
            >
              {eq}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
