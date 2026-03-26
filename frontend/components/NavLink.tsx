"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import clsx from "classnames";

type Props = {
  href: string;
  children: ReactNode;
};

export function NavLink({ href, children }: Props) {
  const pathname = usePathname();
  const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <Link
      href={href}
      className={clsx(
        "px-2.5 py-1 rounded-md transition-colors text-xs",
        isActive
          ? "text-accent bg-accent/10 font-medium"
          : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
      )}
    >
      {children}
    </Link>
  );
}
