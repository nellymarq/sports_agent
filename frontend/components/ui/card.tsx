import type { HTMLAttributes, ReactNode } from "react";
import clsx from "classnames";

type Props = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
};

export function Card({ children, className, ...rest }: Props) {
  return (
    <div
      className={clsx(
        "rounded-xl border border-slate-800 bg-surface/90 shadow-lg shadow-black/40",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
