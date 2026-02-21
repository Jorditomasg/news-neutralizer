"use client";

import Link from "next/link";
import { NotificationCenter } from "@/components/NotificationCenter";

export function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-white/5 bg-gray-950/80 backdrop-blur-2xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-teal-400 to-cyan-500">
            <svg
              className="h-5 w-5 text-gray-950"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z"
              />
            </svg>
          </div>
          <span className="font-display text-lg font-bold tracking-tight">
            News Neutralizer
          </span>
        </Link>

        <div className="flex items-center gap-4">
          <Link
            href="/analyzed"
            className="text-sm font-semibold rounded-xl bg-white/5 border border-white/10 px-4 py-2 text-teal-400 transition-all hover:bg-white/10 hover:text-teal-300 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Noticias Analizadas
          </Link>
          <Link
            href="/generated"
            className="text-sm font-semibold rounded-xl bg-gradient-to-r from-teal-500/10 to-cyan-500/10 border border-teal-500/20 px-4 py-2 text-teal-400 transition-all hover:bg-teal-500/20 hover:border-teal-500/40 hover:text-teal-300 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2m-2-1m-4 5V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h4" />
            </svg>
            Noticias Generadas
          </Link>
          
          <div className="flex items-center gap-2 ml-2 pl-4 border-l border-white/10">
            <NotificationCenter />
            <Link
              href="/settings"
              className="p-2 text-gray-400 transition-colors hover:text-white rounded-lg hover:bg-white/5"
              aria-label="Configuración"
              title="Configuración"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
