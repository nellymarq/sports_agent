"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { CardSkeleton } from "@/components/ui/skeleton";

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

function Countdown({ date }: { date: string }) {
  const [timeLeft, setTimeLeft] = useState("");
  const [isPast, setIsPast] = useState(false);

  useEffect(() => {
    const update = () => {
      const target = new Date(date + "T23:00:00Z");
      const now = new Date();
      const diff = target.getTime() - now.getTime();

      if (diff <= 0) {
        setIsPast(true);
        setTimeLeft("Event passed");
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

      if (days > 0) {
        setTimeLeft(`${days}d ${hours}h`);
      } else {
        const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        setTimeLeft(`${hours}h ${mins}m`);
      }
    };

    update();
    const interval = setInterval(update, 60000);
    return () => clearInterval(interval);
  }, [date]);

  if (isPast) return null;

  return (
    <span className="text-[10px] font-mono bg-accent/10 text-accent px-1.5 py-0.5 rounded border border-accent/20">
      {timeLeft}
    </span>
  );
}

function StatusBadge({ status, date }: { status?: string; date?: string }) {
  if (status === "completed") {
    return (
      <span className="text-[10px] bg-slate-700/50 text-slate-400 px-1.5 py-0.5 rounded">
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
        <span className="text-[10px] bg-slate-700/50 text-slate-400 px-1.5 py-0.5 rounded">
          COMPLETED
        </span>
      );
    }
    if (daysUntil <= 7) {
      return (
        <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded animate-pulse">
          THIS WEEK
        </span>
      );
    }
    if (daysUntil <= 14) {
      return (
        <span className="text-[10px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">
          UPCOMING
        </span>
      );
    }
  }

  return null;
}

function BoutRow({ bout }: { bout: Bout }) {
  const names = bout.fighters.map((f) => f.name).filter(Boolean);
  const display =
    names.length >= 2 ? `${names[0]} vs ${names[1]}` : names.join(", ") || "TBA";

  return (
    <div className="flex items-center justify-between py-2 px-3 border-b border-slate-800/40 last:border-0">
      <div className="flex items-center gap-2">
        {bout.is_title_fight && (
          <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-medium">
            TITLE
          </span>
        )}
        {bout.is_main_event && (
          <span className="text-[10px] bg-accent/20 text-accent px-1.5 py-0.5 rounded font-medium">
            MAIN
          </span>
        )}
        {bout.is_co_main_event && (
          <span className="text-[10px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded font-medium">
            CO-MAIN
          </span>
        )}
        <span className="text-sm">{display}</span>
      </div>
      <div className="flex items-center gap-2">
        {bout.weight_class && (
          <span className="text-xs text-slate-500">{bout.weight_class}</span>
        )}
        {names.length >= 2 && (
          <Link
            href={`/compare?a=${encodeURIComponent(names[0])}&b=${encodeURIComponent(names[1])}`}
            className="text-[10px] text-accent hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            Compare
          </Link>
        )}
      </div>
    </div>
  );
}

function EventCard({ event }: { event: EventData }) {
  const [expanded, setExpanded] = useState(false);

  const allBouts: Bout[] = [];
  if (event.main_event) allBouts.push(event.main_event);
  if (event.co_main_event) allBouts.push(event.co_main_event);
  allBouts.push(...(event.card || []));

  const isCompleted = event.status === "completed" || (event.date && new Date(event.date + "T23:00:00Z") < new Date());

  return (
    <Card className={`overflow-hidden ${isCompleted ? "opacity-60" : ""}`}>
      <div
        className="p-4 cursor-pointer hover:bg-slate-800/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-sm">
                {event.name || event.code}
              </h3>
              <StatusBadge status={event.status} date={event.date} />
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {event.main_event_display}
            </p>
          </div>
          <div className="text-right flex flex-col items-end gap-1">
            {event.date && !isCompleted && <Countdown date={event.date} />}
            <p className="text-xs text-slate-500">
              {event.bout_count} bout{event.bout_count !== 1 ? "s" : ""}
            </p>
            {event.date && (
              <p className="text-[10px] text-slate-600">
                {new Date(event.date).toLocaleDateString("en-US", {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            )}
          </div>
        </div>
        {event.location && (
          <p className="text-xs text-slate-500 mt-1">{event.location}</p>
        )}
        <div className="flex gap-2 mt-2">
          <Link
            href={`/analyze?q=${encodeURIComponent(`Break down ${event.code} main event`)}`}
            className="text-[10px] text-accent hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            Analyze Main Event
          </Link>
          <Link
            href={`/analyze?q=${encodeURIComponent(`Full card breakdown for ${event.code}`)}`}
            className="text-[10px] text-accent hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            Full Card Analysis
          </Link>
          <span
            className="text-[10px] text-slate-500 ml-auto"
          >
            {expanded ? "Collapse" : "Expand card"}
          </span>
        </div>
      </div>

      {expanded && allBouts.length > 0 && (
        <div className="border-t border-slate-800 bg-black/20">
          {allBouts.map((bout) => (
            <BoutRow key={bout.bout_id} bout={bout} />
          ))}
        </div>
      )}
    </Card>
  );
}

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
        // Sort: upcoming first (by date asc), then completed
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
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Events</h1>
        <div className="flex gap-3 items-center">
          <Link
            href="/dashboard"
            className="text-xs text-accent hover:underline"
          >
            Dashboard
          </Link>
          <Link href="/" className="text-xs text-accent hover:underline">
            Home
          </Link>
        </div>
      </div>

      {loading && (
        <div className="space-y-3">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      )}

      {error && (
        <Card className="p-5 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {!loading && !error && events.length === 0 && (
        <Card className="p-5">
          <p className="text-sm text-slate-400">
            No events loaded yet. Run the event ingestion pipeline to populate
            event data.
          </p>
        </Card>
      )}

      {/* Upcoming Events */}
      {upcoming.length > 0 && (
        <>
          <h2 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Upcoming ({upcoming.length})
          </h2>
          <div className="space-y-3">
            {upcoming.map((ev) => (
              <EventCard key={ev.id} event={ev} />
            ))}
          </div>
        </>
      )}

      {/* Completed Events */}
      {completed.length > 0 && (
        <>
          <button
            onClick={() => setShowCompleted(!showCompleted)}
            className="text-xs text-slate-400 hover:text-slate-300 transition-colors mt-4"
          >
            {showCompleted ? "Hide" : "Show"} completed events (
            {completed.length})
          </button>
          {showCompleted && (
            <div className="space-y-3">
              {completed.map((ev) => (
                <EventCard key={ev.id} event={ev} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
