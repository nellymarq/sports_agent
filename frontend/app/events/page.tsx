"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type FighterRef = {
  name: string;
  record?: string;
  rank?: string;
  is_champion?: boolean;
};

type Bout = {
  bout_id: string;
  order: number;
  weight_class?: string;
  is_title_fight?: boolean;
  is_main_event?: boolean;
  is_co_main_event?: boolean;
  fighters: FighterRef[];
};

type EventData = {
  id: string;
  code: string;
  name: string;
  date?: string;
  status?: string;
  venue?: string;
  location?: string;
  main_event_display: string;
  bout_count: number;
  main_event?: Bout;
  co_main_event?: Bout;
  card: Bout[];
};

/* ── countdown timer ───────────────────────────────────── */

function Countdown({ date }: { date: string }) {
  const [parts, setParts] = useState<{
    days: number;
    hours: number;
    mins: number;
  } | null>(null);
  const [isPast, setIsPast] = useState(false);

  useEffect(() => {
    const update = () => {
      const target = new Date(date + "T23:00:00Z");
      const now = new Date();
      const diff = target.getTime() - now.getTime();

      if (diff <= 0) {
        setIsPast(true);
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor(
        (diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
      );
      const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      setParts({ days, hours, mins });
    };

    update();
    const interval = setInterval(update, 60000);
    return () => clearInterval(interval);
  }, [date]);

  if (isPast || !parts) return null;

  return (
    <div className="flex items-center gap-1">
      {[
        { val: parts.days, label: "D" },
        { val: parts.hours, label: "H" },
        { val: parts.mins, label: "M" },
      ].map((seg, i) => (
        <div
          key={i}
          className="flex flex-col items-center bg-black/40 border border-accent/20 rounded-md px-2 py-1 min-w-[2rem]"
        >
          <span className="text-sm font-bold font-mono text-accent leading-none">
            {String(seg.val).padStart(2, "0")}
          </span>
          <span className="text-[8px] text-accent/50 uppercase">{seg.label}</span>
        </div>
      ))}
    </div>
  );
}

/* ── status badge ──────────────────────────────────────── */

function StatusBadge({ status, date }: { status?: string; date?: string }) {
  if (status === "completed") {
    return (
      <span className="text-[10px] bg-slate-700/50 text-slate-400 px-2 py-0.5 rounded-full font-medium">
        COMPLETED
      </span>
    );
  }

  if (date) {
    const eventDate = new Date(date + "T23:00:00Z");
    const now = new Date();
    const daysUntil = Math.ceil(
      (eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (daysUntil <= 0) {
      return (
        <span className="text-[10px] bg-slate-700/50 text-slate-400 px-2 py-0.5 rounded-full font-medium">
          COMPLETED
        </span>
      );
    }
    if (daysUntil <= 7) {
      return (
        <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-medium border border-emerald-500/30 animate-pulse">
          THIS WEEK
        </span>
      );
    }
    if (daysUntil <= 14) {
      return (
        <span className="text-[10px] bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full font-medium border border-amber-500/30">
          UPCOMING
        </span>
      );
    }
  }

  return (
    <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full font-medium border border-blue-500/30">
      SCHEDULED
    </span>
  );
}

/* ── bout row ──────────────────────────────────────────── */

function BoutRow({ bout }: { bout: Bout }) {
  const names = bout.fighters.map((f) => f.name).filter(Boolean);
  const display =
    names.length >= 2
      ? `${names[0]} vs ${names[1]}`
      : names.join(", ") || "TBA";

  return (
    <div className="flex items-center justify-between py-2.5 px-4 border-b border-slate-800/30 last:border-0 hover:bg-white/[0.02] transition-colors">
      <div className="flex items-center gap-2">
        {bout.is_title_fight && (
          <span className="text-[9px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-full font-bold tracking-wide border border-amber-500/30">
            TITLE
          </span>
        )}
        {bout.is_main_event && (
          <span className="text-[9px] bg-accent/20 text-accent px-1.5 py-0.5 rounded-full font-bold tracking-wide border border-accent/30">
            MAIN
          </span>
        )}
        {bout.is_co_main_event && (
          <span className="text-[9px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded-full font-bold tracking-wide border border-blue-500/30">
            CO-MAIN
          </span>
        )}
        <span className="text-sm text-slate-200">{display}</span>
      </div>
      <div className="flex items-center gap-3">
        {bout.weight_class && (
          <span className="text-[10px] text-slate-600 font-mono">
            {bout.weight_class}
          </span>
        )}
        {names.length >= 2 && (
          <Link
            href={`/compare?a=${encodeURIComponent(names[0])}&b=${encodeURIComponent(names[1])}`}
            className="text-[10px] text-accent/70 hover:text-accent transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            Compare
          </Link>
        )}
      </div>
    </div>
  );
}

/* ── date badge ────────────────────────────────────────── */

function DateBadge({ date }: { date: string }) {
  const d = new Date(date);
  const month = d.toLocaleDateString("en-US", { month: "short" }).toUpperCase();
  const day = d.getDate();

  return (
    <div className="flex flex-col items-center justify-center bg-accent/10 border border-accent/20 rounded-lg w-14 h-14 shrink-0">
      <span className="text-[9px] font-bold text-accent/70 uppercase tracking-wider leading-none">
        {month}
      </span>
      <span className="text-xl font-black text-accent leading-none mt-0.5">
        {day}
      </span>
    </div>
  );
}

/* ── event card ────────────────────────────────────────── */

function EventCard({ event }: { event: EventData }) {
  const [expanded, setExpanded] = useState(false);

  const allBouts: Bout[] = [];
  if (event.main_event) allBouts.push(event.main_event);
  if (event.co_main_event) allBouts.push(event.co_main_event);
  allBouts.push(...(event.card || []));

  const isCompleted =
    event.status === "completed" ||
    (event.date && new Date(event.date + "T23:00:00Z") < new Date());

  // Extract main event fighters
  const mainFighters = event.main_event?.fighters
    .map((f) => f.name)
    .filter(Boolean);

  return (
    <Card
      variant={isCompleted ? "default" : "glass"}
      className={`overflow-hidden group transition-all duration-300 ${
        isCompleted
          ? "opacity-50 hover:opacity-70"
          : "hover:border-accent/30 hover:shadow-[0_0_30px_rgba(0,224,255,0.06)]"
      }`}
    >
      <div
        className="p-5 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-4">
          {/* Date badge */}
          {event.date && !isCompleted && <DateBadge date={event.date} />}

          {/* Main content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-bold text-sm text-slate-100 group-hover:text-white transition-colors">
                {event.name || event.code}
              </h3>
              <StatusBadge status={event.status} date={event.date} />
            </div>

            {/* Main event headline */}
            {mainFighters && mainFighters.length >= 2 ? (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-200">
                  {mainFighters[0]}
                </span>
                <span className="text-[10px] font-bold text-slate-600 uppercase">
                  vs
                </span>
                <span className="text-sm font-semibold text-slate-200">
                  {mainFighters[1]}
                </span>
                {event.main_event?.is_title_fight && (
                  <span className="text-[9px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-full font-bold border border-amber-500/30 ml-1">
                    TITLE
                  </span>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-400 mt-1">
                {event.main_event_display}
              </p>
            )}

            {/* Venue / Location */}
            {(event.venue || event.location) && (
              <p className="text-[10px] text-slate-600 mt-1.5 flex items-center gap-1">
                <span className="opacity-60">{"\u{1F4CD}"}</span>
                {[event.venue, event.location].filter(Boolean).join(" \u2014 ")}
              </p>
            )}

            {/* Date for completed */}
            {event.date && isCompleted && (
              <p className="text-[10px] text-slate-600 mt-1">
                {new Date(event.date).toLocaleDateString("en-US", {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            )}
          </div>

          {/* Right side: countdown + bout count */}
          <div className="flex flex-col items-end gap-2 shrink-0">
            {event.date && !isCompleted && <Countdown date={event.date} />}
            <span className="text-[10px] text-slate-600 font-mono">
              {event.bout_count} bout{event.bout_count !== 1 ? "s" : ""}
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-800/30">
          <Link
            href={`/analyze?q=${encodeURIComponent(`Break down ${event.code} main event`)}`}
            className="text-[10px] px-3 py-1.5 rounded-lg bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 hover:border-accent/40 transition-all font-medium"
            onClick={(e) => e.stopPropagation()}
          >
            Analyze
          </Link>
          <Link
            href={`/simulate?event=${encodeURIComponent(event.code)}`}
            className="text-[10px] px-3 py-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 hover:bg-purple-500/20 hover:border-purple-500/40 transition-all font-medium"
            onClick={(e) => e.stopPropagation()}
          >
            Simulate
          </Link>
          <Link
            href={`/analyze?q=${encodeURIComponent(`Full card breakdown for ${event.code}`)}`}
            className="text-[10px] px-3 py-1.5 rounded-lg bg-surface/60 text-slate-400 border border-slate-700/50 hover:text-slate-200 hover:border-slate-600 transition-all font-medium"
            onClick={(e) => e.stopPropagation()}
          >
            Full Card
          </Link>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors ml-auto flex items-center gap-1"
          >
            {expanded ? "Collapse" : "Expand"}{" "}
            <span
              className={`inline-block transition-transform duration-200 ${
                expanded ? "rotate-180" : ""
              }`}
            >
              {"\u25BC"}
            </span>
          </button>
        </div>
      </div>

      {/* Expanded fight card */}
      {expanded && allBouts.length > 0 && (
        <div className="border-t border-slate-800/40 bg-black/30 animate-slide-up">
          {allBouts.map((bout) => (
            <BoutRow key={bout.bout_id} bout={bout} />
          ))}
        </div>
      )}
    </Card>
  );
}

/* ── loading skeleton ──────────────────────────────────── */

function EventSkeleton() {
  return (
    <div className="rounded-xl border border-slate-800 bg-surface/60 backdrop-blur p-5 space-y-4 animate-pulse">
      <div className="flex gap-4">
        <Skeleton className="w-14 h-14 rounded-lg" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-3 w-64" />
          <Skeleton className="h-2 w-32" />
        </div>
        <div className="flex flex-col items-end gap-2">
          <Skeleton className="h-8 w-24 rounded-md" />
          <Skeleton className="h-2 w-12" />
        </div>
      </div>
      <div className="flex gap-2 pt-2 border-t border-slate-800/30">
        <Skeleton className="h-6 w-16 rounded-lg" />
        <Skeleton className="h-6 w-16 rounded-lg" />
        <Skeleton className="h-6 w-20 rounded-lg" />
      </div>
    </div>
  );
}

/* ── page ──────────────────────────────────────────────── */

export default function EventsPage() {
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCompleted, setShowCompleted] = useState(false);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/events`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((d) => {
        const sorted = (d.events || []).sort(
          (a: EventData, b: EventData) => {
            const aCompleted =
              a.status === "completed" ||
              (a.date && new Date(a.date) < new Date());
            const bCompleted =
              b.status === "completed" ||
              (b.date && new Date(b.date) < new Date());
            if (aCompleted !== bCompleted) return aCompleted ? 1 : -1;
            if (!a.date) return 1;
            if (!b.date) return -1;
            return new Date(a.date).getTime() - new Date(b.date).getTime();
          }
        );
        setEvents(sorted);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const upcoming = events.filter(
    (e) =>
      e.status !== "completed" &&
      (!e.date || new Date(e.date + "T23:00:00Z") >= new Date())
  );
  const completed = events.filter(
    (e) =>
      e.status === "completed" ||
      (e.date && new Date(e.date + "T23:00:00Z") < new Date())
  );

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 space-y-6">
      {/* ── Header ────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Events</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {upcoming.length} upcoming &middot; {completed.length} completed
          </p>
        </div>
        <div className="flex gap-3 items-center">
          <Link
            href="/dashboard"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-all"
          >
            Dashboard
          </Link>
          <Link
            href="/"
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-all"
          >
            Home
          </Link>
        </div>
      </div>

      {/* ── Loading ───────────────────────────────────────── */}
      {loading && (
        <div className="space-y-4">
          <EventSkeleton />
          <EventSkeleton />
          <EventSkeleton />
        </div>
      )}

      {/* ── Error ─────────────────────────────────────────── */}
      {error && (
        <Card variant="glass" className="p-5 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
          <p className="text-xs text-red-300/60 mt-1">
            Check backend connection and try again.
          </p>
        </Card>
      )}

      {/* ── Empty State ───────────────────────────────────── */}
      {!loading && !error && events.length === 0 && (
        <Card variant="glass" className="p-10 text-center">
          <div className="text-4xl mb-3 opacity-30">{"\uD83C\uDFAA"}</div>
          <p className="text-sm text-slate-400 mb-1">No events loaded yet</p>
          <p className="text-xs text-slate-600 mb-4">
            Run the event ingestion pipeline to populate event data.
          </p>
          <Link
            href="/analyze?q=ingest+upcoming+UFC+events"
            className="inline-block text-xs px-4 py-2 rounded-lg bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-all font-medium"
          >
            Ingest Events
          </Link>
        </Card>
      )}

      {/* ── Upcoming Events ───────────────────────────────── */}
      {upcoming.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-xs font-bold text-accent uppercase tracking-wider">
              Upcoming
            </h2>
            <span className="text-[10px] bg-accent/10 text-accent px-2 py-0.5 rounded-full border border-accent/20 font-mono">
              {upcoming.length}
            </span>
            <div className="flex-1 h-px bg-gradient-to-r from-accent/20 to-transparent" />
          </div>
          <div className="space-y-3">
            {upcoming.map((ev) => (
              <EventCard key={ev.id} event={ev} />
            ))}
          </div>
        </div>
      )}

      {/* ── Completed Events ──────────────────────────────── */}
      {completed.length > 0 && (
        <div className="space-y-4">
          <button
            onClick={() => setShowCompleted(!showCompleted)}
            className="flex items-center gap-3 group w-full"
          >
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider group-hover:text-slate-400 transition-colors">
              Completed
            </h2>
            <span className="text-[10px] bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full font-mono">
              {completed.length}
            </span>
            <div className="flex-1 h-px bg-gradient-to-r from-slate-800 to-transparent" />
            <span
              className={`text-[10px] text-slate-600 transition-transform duration-200 ${
                showCompleted ? "rotate-180" : ""
              }`}
            >
              {"\u25BC"}
            </span>
          </button>
          {showCompleted && (
            <div className="space-y-3 animate-slide-up">
              {completed.map((ev) => (
                <EventCard key={ev.id} event={ev} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
