import type { HTMLAttributes, ReactNode } from "react";
import clsx from "classnames";

type Variant = "default" | "glass" | "glow" | "bordered";

type Props = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  variant?: Variant;
};

const variantStyles: Record<Variant, string> = {
  default: "border-slate-800 bg-surface/90 shadow-lg shadow-black/40",
  glass: "border-slate-700/50 bg-surface/40 backdrop-blur-xl shadow-lg shadow-black/30",
  glow: "border-slate-800 bg-surface/90 shadow-lg shadow-black/40 glow-subtle",
  bordered: "border-slate-700 bg-surface/90 shadow-lg shadow-black/40 hover:border-accent/40 transition-all duration-200",
};

export function Card({ children, className, variant = "default", ...rest }: Props) {
  return (
    <div
      className={clsx(
        "rounded-xl border",
        variantStyles[variant],
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
