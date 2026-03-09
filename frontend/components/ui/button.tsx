import type { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "classnames";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
};

export function Button({ children, className, ...rest }: Props) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-lg border border-accent bg-accent/90 px-4 py-1.5 text-sm font-medium text-black",
        "hover:bg-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
