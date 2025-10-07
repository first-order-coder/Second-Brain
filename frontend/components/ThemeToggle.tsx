'use client'
import { useEffect, useState } from 'react'

export function ThemeToggle() {
  const [dark, setDark] = useState(true)
  
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])
  
  return (
    <button
      onClick={() => setDark(v => !v)}
      className="text-sm text-slate-300 hover:text-white transition-colors"
      aria-label="Toggle theme"
    >
      {dark ? 'Light' : 'Dark'}
    </button>
  )
}
