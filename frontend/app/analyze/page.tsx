"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AnalysisLayout } from "@/components/analysis/analysis-layout";
import { AnalysisLoading } from "@/components/analysis/analysis-loading";
import { AnalysisResult } from "@/components/analysis/analysis-result";

export default function AnalyzePage() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [query] = useState(initialQuery);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");

  useEffect(() => {
    if (!query.trim()) {
      setLoading(false);
      setError("No query provided.");
      return;
    }

    const run = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch("http://localhost:8000/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_input: query,
            history: [],
            retrieved_context: "",
            test_mode: false, // flip to false when you plug in real LLM + tools
          }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || `Backend error (${res.status})`);
        }

        const data = (await res.json()) as { content: string };
        setContent(data.content || "");
      } catch (e: any) {
        setError(e.message || "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    void run();
  }, [query]);

  return (
    <AnalysisLayout query={query}>
      {loading && <AnalysisLoading />}
      {!loading && error && (
        <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}
      {!loading && !error && <AnalysisResult content={content} />}
    </AnalysisLayout>
  );
}
