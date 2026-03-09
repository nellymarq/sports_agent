import type { HTMLAttributes } from "react";
import clsx from "classnames";

export function Skeleton({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "animate-pulse rounded-md bg-slate-800/70",
        className
      )}
      {...rest}
    />
  );
}
