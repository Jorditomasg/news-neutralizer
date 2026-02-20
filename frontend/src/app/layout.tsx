import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "News Neutralizer — Análisis neutral de noticias",
  description:
    "Compara noticias de múltiples fuentes, detecta sesgo informativo y genera resúmenes neutralizados basados en hechos verificables.",
  keywords: ["noticias", "sesgo", "neutral", "análisis", "medios", "bias detection"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="dark">
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} font-sans antialiased`}
      >
        <div className="flex flex-col min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 text-gray-100">
          {/* Navigation */}
          <nav className="sticky top-0 z-50 border-b border-white/5 bg-gray-950/80 backdrop-blur-2xl">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
              <a href="/" className="flex items-center gap-3">
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
              </a>

              <div className="flex items-center gap-6">
                <a
                  href="/history"
                  className="text-sm text-gray-400 transition-colors hover:text-white flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Historial
                </a>
                <a
                  href="/settings"
                  className="text-sm text-gray-400 transition-colors hover:text-white"
                >
                  Configuración
                </a>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main className="flex-1 w-full mx-auto max-w-7xl px-6 py-10">{children}</main>

          {/* Footer */}
          <footer className="border-t border-white/5 py-8 text-center text-xs text-gray-600">
            <p>
              News Neutralizer — Herramienta de análisis. Los resultados son
              orientativos, no verdades absolutas.
            </p>
          </footer>
        </div>
      </body>
    </html>
  );
}
