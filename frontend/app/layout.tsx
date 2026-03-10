import "./../styles/globals.css";
import type { ReactNode } from "react";
import Link from "next/link";
import { MobileNav } from "@/components/MobileNav";

const NAV_LINKS = [
  { href: "/", label: "Analyze" },
  { href: "/compare", label: "Compare" },
  { href: "/events", label: "Events" },
  { href: "/predictions", label: "Predictions" },
  { href: "/value-bets", label: "Value Bets" },
  { href: "/calibration", label: "Calibration" },
];

export const metadata = {
  title: "UFC Analytics Engine",
  description: "Multi-agent UFC analysis with unified event pipeline.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-slate-100">
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-slate-800 bg-black/40 backdrop-blur sticky top-0 z-50">
            <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                  <div className="h-7 w-7 rounded-lg bg-accentSoft border border-accent" />
                  <span className="font-semibold tracking-tight">
                    UFC Analytics Engine
                  </span>
                </Link>
                <nav className="hidden sm:flex items-center gap-3 text-xs text-slate-400">
                  {NAV_LINKS.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className="hover:text-slate-200 transition-colors"
                    >
                      {link.label}
                    </Link>
                  ))}
                </nav>
              </div>
              <span className="text-xs text-slate-400 hidden sm:block">
                14 Specialists · Memory-Aware · Prediction Tracking
              </span>
              <MobileNav links={NAV_LINKS} />
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-slate-900 text-xs text-slate-500">
            <div className="mx-auto max-w-5xl px-4 py-3 flex justify-between">
              <span>© {new Date().getFullYear()} UFC Analytics Engine</span>
              <span className="hidden sm:block">Built on multi-agent orchestration + unified events</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
