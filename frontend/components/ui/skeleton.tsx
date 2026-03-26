import type { HTMLAttributes } from "react";
import clsx from "classnames";

export function Skeleton({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "relative rounded-md bg-slate-800/70 overflow-hidden",
        className
      )}
      {...rest}
    >
      {/* Shimmer overlay */}
      <div
        className="absolute inset-0 shimmer"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, rgba(0,224,255,0.04) 50%, transparent 100%)",
          backgroundSize: "200% 100%",
          animation: "shimmer 2s ease-in-out infinite",
        }}
      />
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-800 bg-surface p-6 space-y-4">
      <Skeleton className="h-5 w-2/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-4/6" />
      <div className="pt-2 space-y-3">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
      </div>
    </div>
  );
}

export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="rounded-lg border border-slate-800 bg-surface p-3 space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-6 w-12" />
        </div>
      ))}
    </div>
  );
}
