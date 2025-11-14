import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import Header from "@/components/app/Header";

const inter = Inter({ subsets: ["latin"] });

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Second Brain",
  description: "AI-powered learning & knowledge platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        className={`${inter.className} antialiased bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-200`}
      >
        <ThemeProvider>
          <Header />
          <main className="pt-6">{children}</main>
          <footer className="mt-16 border-t border-black/10 dark:border-white/10">
            <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-slate-500 dark:text-slate-400">
              © {new Date().getFullYear()} Second Brain
            </div>
          </footer>
        </ThemeProvider>
      </body>
    </html>
  );
}
