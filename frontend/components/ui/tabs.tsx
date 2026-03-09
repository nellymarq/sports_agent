"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import clsx from "classnames";

export type TabItem = {
  id: string;
  label: string;
  content: ReactNode;
};

type TabsProps = {
  items: TabItem[];
  initialId?: string;
};

export function Tabs({ items, initialId }: TabsProps) {
  const [active, setActive] = useState<string>(
    initialId || (items[0]?.id ?? "")
  );

  return (
    <div className="w-full">
      <div className="flex gap-2 border-b border-slate-800 mb-3 overflow-x-auto">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => setActive(item.id)}
            className={clsx(
              "px-3 py-1.5 text-xs font-medium rounded-t-md border-b-2",
              active === item.id
                ? "border-accent text-accent"
                : "border-transparent text-slate-400 hover:text-slate-200"
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="mt-2">
        {items.map(
          (item) =>
            item.id === active && (
              <div key={item.id} className="text-sm text-slate-100">
                {item.content}
              </div>
            )
        )}
      </div>
    </div>
  );
}
