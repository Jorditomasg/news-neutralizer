import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { TaskProvider } from "@/context/TaskContext";
import { GlobalTaskTracker } from "@/components/GlobalTaskTracker";
import { NavBar } from "@/components/NavBar";
import { ThemeProvider } from "@/components/ThemeProvider";

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
    <html lang="es" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const storedTheme = localStorage.getItem('theme');
                if (storedTheme === 'dark') {
                  document.documentElement.classList.add('dark');
                } else if (storedTheme === 'light') {
                  document.documentElement.classList.remove('dark');
                } else {
                  // Default to light
                  document.documentElement.classList.remove('dark');
                }
              } catch (err) {}
            `,
          }}
        />
      </head>
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} font-sans antialiased`}
      >
        <ThemeProvider>
          <TaskProvider>
            <div className="flex flex-col min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-300">
              <NavBar />

              {/* Main Content */}
              <main className="flex-1 w-full mx-auto max-w-7xl px-6 py-10">{children}</main>

              {/* Footer */}
              <footer className="border-t border-gray-200 dark:border-white/5 py-8 text-center text-xs text-gray-500 dark:text-gray-600 transition-colors duration-300">
                <p>
                  News Neutralizer — Herramienta de análisis. Los resultados son
                  orientativos, no verdades absolutas.
                </p>
              </footer>
            </div>
            <GlobalTaskTracker />
          </TaskProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
