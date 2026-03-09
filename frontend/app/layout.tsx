import "./../styles/globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "UFC Analytics Engine",
  description: "Multi-agent UFC analysis with unified event pipeline.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-slate-100">
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-slate-800 bg-black/40 backdrop-blur">
            <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-accentSoft border border-accent" />
                <span className="font-semibold tracking-tight">
                  UFC Analytics Engine
                </span>
              </div>
              <span className="text-xs text-slate-400">
                Unified Event · Multi-Agent · Memory-Aware
              </span>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-slate-900 text-xs text-slate-500">
            <div className="mx-auto max-w-5xl px-4 py-3 flex justify-between">
              <span>© {new Date().getFullYear()} UFC Analytics Engine</span>
              <span>Built on multi-agent orchestration + unified events</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
