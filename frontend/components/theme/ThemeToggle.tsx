'use client'
import { useTheme } from './ThemeProvider'
import { Sun, Moon } from 'lucide-react'

export function ThemeToggle() {
  const { theme, setTheme, mounted } = useTheme()
  if (!mounted) return null

  const isDark = theme === 'dark'
  const Icon = isDark ? Sun : Moon
  const label = isDark ? 'Light' : 'Dark'

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-sm
                 border-black/10 bg-white/60 text-slate-700 hover:bg-white
                 dark:border-white/10 dark:bg-slate-900/60 dark:text-slate-300 dark:hover:bg-slate-900
                 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:ring-offset-2
                 focus:ring-offset-white dark:focus:ring-offset-slate-950"
      aria-label={`Switch to ${label} theme`}
      title={`Switch to ${label} theme`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  )
}


