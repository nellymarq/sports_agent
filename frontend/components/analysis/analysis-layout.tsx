import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";

type Props = {
  query: string;
  children: ReactNode;
};

export function AnalysisLayout({ query, children }: Props) {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 space-y-6">
      <Card className="p-5">
        <h1 className="text-lg font-semibold mb-1">Analysis request</h1>
        <p className="text-sm text-slate-300 whitespace-pre-wrap">{query}</p>
      </Card>
      {children}
    </div>
  );
}
