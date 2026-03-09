"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function HomePage() {
  const [query, setQuery] = useState("");

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <Card className="p-8 bg-surface border-slate-800 shadow-lg shadow-black/40">
        <h1 className="text-2xl font-semibold tracking-tight mb-2">
          Fight‑week level UFC analysis.
        </h1>
        <p className="text-sm text-slate-400 mb-6">
          Ask about a matchup, event, or fighter. The engine routes through
          specialists, merges analysis, and returns a unified breakdown.
        </p>

        <label className="block text-xs font-medium text-slate-400 mb-1">
          Question
        </label>
        <textarea
          className="w-full rounded-lg bg-black/40 border border-slate-800 px-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent resize-none h-28"
          placeholder="Example: Break down UFC 313 main event and tell me who you favor."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        <div className="mt-4 flex justify-between items-center">
          <span className="text-xs text-slate-500">
            The engine will run router → supervisor → orchestrator → critic.
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
    </div>
  );
}
