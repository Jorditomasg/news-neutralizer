import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { TaskProvider } from "@/context/TaskContext";
import { GlobalTaskTracker } from "@/components/GlobalTaskTracker";
import { NavBar } from "@/components/NavBar";

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
        <TaskProvider>
          <div className="flex flex-col min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 text-gray-100">
            <NavBar />

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
          <GlobalTaskTracker />
        </TaskProvider>
      </body>
    </html>
  );
}
