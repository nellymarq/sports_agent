"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { AnalysisLayout } from "@/components/analysis/analysis-layout";
import { AnalysisLoading } from "@/components/analysis/analysis-loading";
import { AnalysisResult } from "@/components/analysis/analysis-result";

function AnalyzeContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [query] = useState(initialQuery);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [stage, setStage] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!query.trim()) {
      setLoading(false);
      setError("No query provided.");
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const runStream = async () => {
      try {
        setLoading(true);
        setError(null);
        setStage("");

        const res = await fetch(`${apiUrl}/analyze/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_input: query }),
          signal: controller.signal,
        });

        if (!res.ok) {
          throw new Error(`Backend error (${res.status})`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") break;

            try {
              const msg = JSON.parse(payload);
              if (msg.type === "stage") {
                setStage(msg.stage);
              } else if (msg.type === "result") {
                setContent(msg.content || "");
                setElapsed(msg.elapsed_seconds ?? null);
              } else if (msg.type === "error") {
                throw new Error(msg.detail || "Pipeline error");
              }
            } catch (parseErr: any) {
              if (
                parseErr.message?.includes("Pipeline error") ||
                parseErr.message?.includes("Backend error")
              ) {
                throw parseErr;
              }
            }
          }
        }
      } catch (e: any) {
        if (e.name === "AbortError") return;

        // Fallback to non-streaming endpoint
        try {
          const res = await fetch(`${apiUrl}/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_input: query }),
            signal: controller.signal,
          });

          if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || `Backend error (${res.status})`);
          }

          const data = (await res.json()) as {
            content: string;
            elapsed_seconds?: number;
          };
          setContent(data.content || "");
          setElapsed(data.elapsed_seconds ?? null);
        } catch (fallbackErr: any) {
          if (fallbackErr.name === "AbortError") return;
          setError(fallbackErr.message || "Unknown error");
        }
      } finally {
        setLoading(false);
      }
    };

    void runStream();

    return () => {
      controller.abort();
    };
  }, [query]);

  return (
    <AnalysisLayout query={query}>
      {loading && <AnalysisLoading stage={stage} />}
      {!loading && error && (
        <div className="space-y-3">
          <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
          <Link
            href="/"
            className="inline-block text-xs text-accent hover:underline"
          >
            &larr; Back to home
          </Link>
        </div>
      )}
      {!loading && !error && (
        <div className="space-y-3">
          <AnalysisResult content={content} elapsedSeconds={elapsed} />
          <Link
            href="/"
            className="inline-block text-xs text-accent hover:underline"
          >
            &larr; New analysis
          </Link>
        </div>
      )}
    </AnalysisLayout>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<AnalysisLoading />}>
      <AnalyzeContent />
    </Suspense>
  );
}
