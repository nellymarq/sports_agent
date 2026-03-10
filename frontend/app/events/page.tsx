"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";

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
  venue?: string;
  location?: string;
  main_event_display: string;
  bout_count: number;
  main_event?: Bout;
  co_main_event?: Bout;
  card: Bout[];
};

function BoutRow({ bout }: { bout: Bout }) {
  const names = bout.fighters.map((f) => f.name).filter(Boolean);
  const display = names.length >= 2 ? `${names[0]} vs ${names[1]}` : names.join(", ") || "TBA";

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
      {bout.weight_class && (
        <span className="text-xs text-slate-500">{bout.weight_class}</span>
      )}
    </div>
  );
}

function EventCard({ event }: { event: EventData }) {
  const [expanded, setExpanded] = useState(false);

  const allBouts: Bout[] = [];
  if (event.main_event) allBouts.push(event.main_event);
  if (event.co_main_event) allBouts.push(event.co_main_event);
  allBouts.push(...(event.card || []));

  return (
    <Card className="overflow-hidden">
      <div
        className="p-4 cursor-pointer hover:bg-slate-800/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-sm">{event.name || event.code}</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {event.main_event_display}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-500">
              {event.bout_count} bout{event.bout_count !== 1 ? "s" : ""}
            </p>
            {event.date && (
              <p className="text-xs text-slate-500">{event.date}</p>
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

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/events`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((d) => setEvents(d.events || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Upcoming Events</h1>
        <Link href="/" className="text-xs text-accent hover:underline">
          &larr; Home
        </Link>
      </div>

      {loading && (
        <Card className="p-5">
          <p className="text-sm text-slate-400 animate-pulse">
            Loading events...
          </p>
        </Card>
      )}

      {error && (
        <Card className="p-5 border-red-500/40 bg-red-500/10">
          <p className="text-sm text-red-200">{error}</p>
        </Card>
      )}

      {!loading && !error && events.length === 0 && (
        <Card className="p-5">
          <p className="text-sm text-slate-400">
            No events loaded yet. Run the event ingestion pipeline to populate event data.
          </p>
        </Card>
      )}

      <div className="space-y-3">
        {events.map((ev) => (
          <EventCard key={ev.id} event={ev} />
        ))}
      </div>
    </div>
  );
}
