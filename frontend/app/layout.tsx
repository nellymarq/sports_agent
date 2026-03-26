import "./../styles/globals.css";
import type { ReactNode } from "react";
import Link from "next/link";
import { MobileNav } from "@/components/MobileNav";
import { NavLink } from "@/components/NavLink";

const NAV_LINKS = [
  { href: "/", label: "Analyze" },
  { href: "/compare", label: "Compare" },
  { href: "/simulate", label: "Simulate" },
  { href: "/fighters", label: "Fighters" },
  { href: "/events", label: "Events" },
  { href: "/predictions", label: "Predictions" },
  { href: "/value-bets", label: "Value Bets" },
  { href: "/bet-calculator", label: "Bet Calc" },
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
          <header className="border-b border-slate-800/80 bg-black/60 backdrop-blur-xl sticky top-0 z-50">
            <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity group">
                  <div className="h-7 w-7 rounded-lg bg-accent/15 border border-accent/60 group-hover:border-accent transition-colors flex items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-accent animate-pulse-slow" />
                  </div>
                  <span className="font-semibold tracking-tight text-gradient">
                    UFC Analytics Engine
                  </span>
                </Link>
                <nav className="hidden sm:flex items-center gap-1 text-xs text-slate-400">
                  {NAV_LINKS.map((link) => (
                    <NavLink key={link.href} href={link.href}>
                      {link.label}
                    </NavLink>
                  ))}
                </nav>
              </div>
              <span className="text-xs text-slate-500 hidden md:flex items-center gap-1.5">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse-slow" />
                <span>16 Specialists Online</span>
              </span>
              <MobileNav links={NAV_LINKS} />
            </div>
            {/* Accent gradient line */}
            <div className="h-px bg-gradient-to-r from-transparent via-accent/30 to-transparent" />
          </header>

          <main className="flex-1">{children}</main>

          <footer className="border-t border-slate-800/60">
            <div className="mx-auto max-w-5xl px-4 py-4 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-slate-500">
              <div className="flex items-center gap-3">
                <span>&copy; {new Date().getFullYear()} UFC Analytics Engine</span>
                <span className="text-slate-700">|</span>
                <span>v2.0</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="hidden sm:block">Built on multi-agent orchestration + unified events</span>
                <a
                  href="https://github.com/nmarq/sports_agent"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-slate-300 transition-colors"
                >
                  GitHub
                </a>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
