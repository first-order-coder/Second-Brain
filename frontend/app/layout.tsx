import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeToggle } from '@/components/ThemeToggle'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Second Brain',
  description: 'AI-powered learning & knowledge platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-200 antialiased`}>
        <header className="sticky top-0 z-40 border-b border-white/10 backdrop-blur supports-[backdrop-filter]:bg-slate-950/70">
          <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
            <div className="font-semibold tracking-tight text-white">Second Brain</div>
            <nav className="flex items-center gap-3">
              <a href="/docs" className="text-sm text-slate-300 hover:text-white transition-colors">Docs</a>
              <a href="/login" className="text-sm text-slate-300 hover:text-white transition-colors">Log in</a>
              <ThemeToggle />
              <a href="/signup" className="ml-2 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-500 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500/40 focus:ring-offset-slate-900">
                Get started
              </a>
            </nav>
          </div>
        </header>
        {children}
        <footer className="border-t border-white/10 mt-20">
          <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-slate-400">
            © {new Date().getFullYear()} Second Brain. All rights reserved.
          </div>
        </footer>
      </body>
    </html>
  )
}
