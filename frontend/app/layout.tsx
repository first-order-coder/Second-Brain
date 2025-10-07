import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/theme/ThemeProvider'
import { ThemeToggle } from '@/components/theme/ThemeToggle'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Second Brain',
  description: 'AI-powered learning & knowledge platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-200`}>
        <ThemeProvider>
          <header className="sticky top-0 z-50 border-b
                              bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/70
                              dark:bg-slate-950/80 dark:border-white/10">
            <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
              <div className="font-semibold tracking-tight">Second Brain</div>
              <nav className="flex items-center gap-4">
                <a className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white" href="/docs">Docs</a>
                <a className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white" href="/login">Log in</a>
                <a className="inline-flex items-center rounded-xl px-3 py-1.5 text-sm bg-blue-600 text-white hover:bg-blue-500" href="/signup">Get started</a>
                <ThemeToggle />
              </nav>
            </div>
          </header>
          <main className="pt-6">
            {children}
          </main>
          <footer className="mt-16 border-t border-black/10 dark:border-white/10">
            <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-slate-500 dark:text-slate-400">
              © {new Date().getFullYear()} Second Brain
            </div>
          </footer>
        </ThemeProvider>
      </body>
    </html>
  )
}
