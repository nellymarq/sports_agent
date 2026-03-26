import type { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "classnames";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
};

const variantStyles: Record<Variant, string> = {
  primary:
    "border-accent bg-accent/90 text-black hover:bg-accent font-medium",
  secondary:
    "border-slate-700 bg-surface text-slate-200 hover:bg-slate-800 hover:border-slate-600 font-medium",
  ghost:
    "border-transparent bg-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5",
  danger:
    "border-red-500/50 bg-red-500/10 text-red-400 hover:bg-red-500/20 font-medium",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-3 py-1 text-xs rounded-md",
  md: "px-4 py-1.5 text-sm rounded-lg",
  lg: "px-6 py-2.5 text-sm rounded-lg",
};

export function Button({
  children,
  className,
  variant = "primary",
  size = "md",
  ...rest
}: Props) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center border transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
