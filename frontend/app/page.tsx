"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const EXAMPLE_QUERIES = [
  {
    title: "UFC 313 Main Event",
    query: "Break down UFC 313 main event: Pereira vs Ankalaev",
    tag: "Event",
  },
  {
    title: "Lightweight Championship",
    query: "Who wins between Islam Makhachev and Arman Tsarukyan?",
    tag: "Matchup",
  },
  {
    title: "Bantamweight Clash",
    query: "Analyze the style matchup for Merab Dvalishvili vs Umar Nurmagomedov",
    tag: "Style",
  },
  {
    title: "Full Card Breakdown",
    query: "Give me a full breakdown of the UFC 313 card",
    tag: "Card",
  },
];

const FEATURES = [
  {
    href: "/compare",
    label: "Compare",
    description: "Head-to-head fighter analysis",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    ),
  },
  {
    href: "/simulate",
    label: "Simulate",
    description: "Monte Carlo fight simulation",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
      </svg>
    ),
  },
  {
    href: "/events",
    label: "Events",
    description: "Upcoming UFC event cards",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
      </svg>
    ),
  },
  {
    href: "/bet-calculator",
    label: "Bet Calculator",
    description: "EV & Kelly criterion sizing",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 15.75V18m-7.5-6.75h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V13.5zm0 2.25h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V18zm2.498-6.75h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V13.5zm0 2.25h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V18zm2.504-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V13.5zm0 2.25h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V18zm2.498-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V13.5zM8.25 6h7.5v2.25h-7.5V6zM12 2.25c-1.892 0-3.758.11-5.593.322C5.307 2.7 4.5 3.65 4.5 4.757V19.5a2.25 2.25 0 002.25 2.25h10.5a2.25 2.25 0 002.25-2.25V4.757c0-1.108-.806-2.057-1.907-2.185A48.507 48.507 0 0012 2.25z" />
      </svg>
    ),
  },
];

const PIPELINE_STAGES = [
  "Retrieval",
  "Router",
  "Specialists",
  "Coordinator",
  "Prediction",
  "Critic",
];

const STATS = [
  { value: "16", label: "Specialist Agents" },
  { value: "888", label: "Tests Passing" },
  { value: "39", label: "API Endpoints" },
];

export default function HomePage() {
  const [query, setQuery] = useState("");

  return (
    <div className="relative">
      {/* Hero glow background */}
      <div className="absolute inset-0 bg-hero-glow pointer-events-none" />

      <div className="relative mx-auto max-w-3xl px-4 py-16 space-y-10">
        {/* Hero Section */}
        <div className="text-center space-y-4 animate-fade-in">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">
            <span className="text-gradient">Fight-Week</span> Level
            <br />
            UFC Analysis
          </h1>
          <p className="text-slate-400 text-sm sm:text-base max-w-lg mx-auto leading-relaxed">
            Multi-agent engine that routes through specialist agents, merges analysis,
            and returns unified breakdowns with structured predictions.
          </p>
        </div>

        {/* Stats Bar */}
        <div className="flex justify-center gap-8 animate-fade-in">
          {STATS.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-accent">{stat.value}</div>
              <div className="text-xs text-slate-500 mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Main Query Card */}
        <Card variant="glow" className="p-6 sm:p-8 animate-slide-up">
          <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">
            Your Question
          </label>
          <textarea
            className="w-full rounded-lg bg-black/50 border border-slate-800 px-4 py-3 text-sm outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/40 focus:shadow-[0_0_20px_rgba(0,224,255,0.1)] resize-none h-28 placeholder:text-slate-600"
            placeholder="Break down UFC 313 main event and tell me who you favor..."
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
            <span className="text-xs text-slate-600 hidden sm:block">
              Press Enter to analyze
            </span>
            <Link
              href={{
                pathname: "/analyze",
                query: query ? { q: query } : {},
              }}
            >
              <Button size="lg" disabled={!query.trim()}>
                Analyze Matchup
              </Button>
            </Link>
          </div>
        </Card>

        {/* Example Queries */}
        <div className="animate-slide-up">
          <h2 className="text-xs font-medium text-slate-500 mb-3 px-1 uppercase tracking-wider">
            Try an example
          </h2>
          <div className="grid gap-2.5 sm:grid-cols-2">
            {EXAMPLE_QUERIES.map((eq) => (
              <Link
                key={eq.query}
                href={{
                  pathname: "/analyze",
                  query: { q: eq.query },
                }}
              >
                <Card
                  variant="bordered"
                  className="px-4 py-3.5 cursor-pointer hover:bg-surface group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-xs font-medium text-slate-200 group-hover:text-white mb-1">
                        {eq.title}
                      </div>
                      <div className="text-xs text-slate-500 group-hover:text-slate-400 leading-relaxed">
                        {eq.query}
                      </div>
                    </div>
                    <span className="shrink-0 text-[10px] font-medium text-accent/60 bg-accent/5 rounded px-1.5 py-0.5 border border-accent/10">
                      {eq.tag}
                    </span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>

        {/* Feature Grid */}
        <div className="animate-slide-up">
          <h2 className="text-xs font-medium text-slate-500 mb-3 px-1 uppercase tracking-wider">
            Quick Access
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {FEATURES.map((feature) => (
              <Link key={feature.href} href={feature.href}>
                <Card
                  variant="bordered"
                  className="p-4 cursor-pointer hover:bg-surface/80 group text-center"
                >
                  <div className="text-slate-500 group-hover:text-accent mb-2 flex justify-center transition-colors">
                    {feature.icon}
                  </div>
                  <div className="text-xs font-medium text-slate-300 group-hover:text-white">
                    {feature.label}
                  </div>
                  <div className="text-[10px] text-slate-600 mt-0.5">
                    {feature.description}
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>

        {/* Pipeline Flow */}
        <div className="animate-fade-in">
          <h2 className="text-xs font-medium text-slate-500 mb-3 px-1 uppercase tracking-wider text-center">
            Analysis Pipeline
          </h2>
          <div className="flex items-center justify-center gap-1 flex-wrap">
            {PIPELINE_STAGES.map((stage, i) => (
              <div key={stage} className="flex items-center gap-1">
                <span className="text-[11px] text-slate-400 bg-surface border border-slate-800 rounded-md px-2.5 py-1 hover:border-accent/30 hover:text-accent transition-colors">
                  {stage}
                </span>
                {i < PIPELINE_STAGES.length - 1 && (
                  <svg className="w-3 h-3 text-slate-700" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
