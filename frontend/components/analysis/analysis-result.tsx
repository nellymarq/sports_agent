import { Card } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";

type Props = {
  content: string;
};

/**
 * For now we treat the orchestrator output as a single block of text.
 * Later you can parse sections (Summary, Style, Grappling, etc.) and
 * map them into separate tabs/cards.
 */
export function AnalysisResult({ content }: Props) {
  const tabs = [
    {
      id: "full",
      label: "Full Analysis",
      content: (
        <div className="prose prose-invert max-w-none text-sm">
          {content.split("\n\n").map((para, idx) => (
            <p key={idx} className="mb-3 whitespace-pre-wrap">
              {para}
            </p>
          ))}
        </div>
      ),
    },
  ];

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Engine output</h2>
        <span className="text-xs text-slate-400">
          Router → Supervisor → Orchestrator → Critic
        </span>
      </div>
      <Tabs items={tabs} />
    </Card>
  );
}
