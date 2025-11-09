"use client"
import { useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { BookOpen, Sparkles, Layers, Upload, FileUp, Brain, Link as LinkIcon, Youtube, FileText } from 'lucide-react'
import PDFUpload from '@/components/PDFUpload'
import YTToCards from '@/components/YTToCards'
import { useRouter } from 'next/navigation'

export default function Page() {
  const [isUploading, setIsUploading] = useState(false)
  const router = useRouter()

  const saveDeckSilently = useCallback((deckId: string) => {
    fetch("/api/save-deck", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ deckId }),
    }).then(async (res) => {
      const json = await res.json().catch(() => ({}));
      if (!json?.ok) {
        console.warn("[Home] save-deck failed", { deckId, json });
      }
    }).catch((error) => {
      console.warn("[Home] save-deck error", { deckId, error });
    });
  }, []);

  const handleUploadSuccess = useCallback((pdfId: string) => {
    saveDeckSilently(pdfId)
    router.push(`/flashcards/${pdfId}`)
  }, [router, saveDeckSilently])

  const loadDemo = () => {
    // TODO: route to a seeded demo deck or query param
    router.push('/flashcards/demo')
  }

  return (
    <main>
      {/* Hero */}
      <section className="sb-section">
        <div className="mx-auto max-w-6xl px-4 sb-surface-0">
          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="text-4xl sm:text-5xl font-bold tracking-tight text-slate-900 dark:text-white"
          >
            Learn faster. Remember longer.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.05 }}
            className="mt-3 max-w-2xl text-base sm:text-lg leading-relaxed sb-muted dark:text-slate-300"
          >
            Second Brain turns PDFs, links, and videos into reliable notes and exam-ready flashcards—with spaced repetition built in.
          </motion.p>

          {/* New grid: uploader (left) + quick start (right) */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.1 }}
            className="mt-8 sb-section sb-band"
          >
            <div className="mx-auto max-w-6xl px-4 grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
            {/* LEFT: Upload Components */}
            <div className="space-y-6">
              <div className="sb-surface-2 sb-surface-hover p-5">
                <PDFUpload 
                  onUploadSuccess={handleUploadSuccess}
                  onUploadStart={() => setIsUploading(true)}
                  onUploadEnd={() => setIsUploading(false)}
                />
              </div>
              
              <div className="sb-surface-2 sb-surface-hover p-5">
                <YTToCards />
              </div>
            </div>

            {/* RIGHT: Quick Start */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.15 }}
              className="space-y-4"
            >
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Quick start</h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sb-surface-1 sb-surface-hover p-5">
                  <div className="sb-kicker">1. Import</div>
                  <p className="mt-2 text-sm sb-muted dark:text-slate-300">Drop a PDF, paste a link, or add a YouTube video.</p>
                </div>

                <div className="sb-surface-1 sb-surface-hover p-5">
                  <div className="sb-kicker">2. Generate</div>
                  <p className="mt-2 text-sm sb-muted dark:text-slate-300">We parse, cite, and create 10 study-ready flashcards.</p>
                </div>

                <div className="sb-surface-1 sb-surface-hover p-5">
                  <div className="sb-kicker">3. Review</div>
                  <p className="mt-2 text-sm sb-muted dark:text-slate-300">Reveal → grade (1–4) with spaced repetition.</p>
                </div>
              </div>

              {/* Supported sources */}
              <div className="mt-4">
                <div className="sb-kicker mb-2">Supported sources</div>
                <div className="flex flex-wrap gap-2">
                  <span className="sb-pill">
                    <LinkIcon className="w-4 h-4 text-blue-500" /> URL
                  </span>
                  <span className="sb-pill">
                    <FileText className="w-4 h-4 text-blue-500" /> PDF
                  </span>
                  <span className="sb-pill">
                    <Youtube className="w-4 h-4 text-blue-500" /> YouTube
                  </span>
                </div>
              </div>

              {/* Demo panel */}
              <div className="mt-4 sb-surface-2 sb-surface-hover sb-elevated p-6 flex items-center justify-between gap-4">
                <div>
                  <div className="font-semibold text-slate-900 dark:text-white">No file handy?</div>
                  <p className="mt-1 text-sm sb-muted dark:text-slate-300">Load a sample deck to see the review flow in action.</p>
                </div>
                <button onClick={loadDemo} className="inline-flex items-center rounded-xl px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-500">
                  See a live demo
                </button>
              </div>
            </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="sb-section sb-band-grad">
        <div className="mx-auto max-w-6xl px-4 grid grid-cols-1 md:grid-cols-3 gap-6">
          <motion.div 
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="sb-surface-2 sb-surface-hover sb-elevated p-6"
          >
            <div className="mb-3 text-blue-600 dark:text-blue-400">
              <BookOpen className="w-6 h-6" />
            </div>
            <div className="font-semibold text-slate-900 dark:text-white">Ingest anything</div>
            <p className="mt-2 text-sm sb-muted dark:text-slate-300">URLs, PDFs, YouTube—clean parsing and citations you can trust.</p>
          </motion.div>
          <motion.div 
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="sb-surface-2 sb-surface-hover sb-elevated p-6"
          >
            <div className="mb-3 text-blue-600 dark:text-blue-400">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="font-semibold text-slate-900 dark:text-white">Great flashcards</div>
            <p className="mt-2 text-sm sb-muted dark:text-slate-300">Auto-generated, editable, and validated against your sources.</p>
          </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.3 }}
                className="sb-surface-2 sb-surface-hover sb-elevated p-6"
              >
                <div className="mb-3 text-blue-600 dark:text-blue-400">
                  <Layers className="w-6 h-6" />
                </div>
                <div className="font-semibold text-slate-900 dark:text-white">Spaced repetition</div>
                <p className="mt-2 text-sm sb-muted dark:text-slate-300">SM-2 scheduling with a smooth daily review flow.</p>
                <div className="mt-4">
                  <a href="/sources/demo" className="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-300/90 dark:hover:text-blue-200 transition-colors">
                    View citation-backed summaries →
                  </a>
                </div>
              </motion.div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="sb-section">
        <div className="mx-auto max-w-6xl px-4 text-center sb-surface-1 p-8">
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Start your next study session</h2>
          <p className="mt-2 sb-muted dark:text-slate-300">Import a PDF or paste a link—your study queue will be ready in minutes.</p>
          <div className="mt-6">
            <a href="/signup" className="inline-flex items-center rounded-xl px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-500">
              Create free account
            </a>
          </div>
        </div>
      </section>
    </main>
  )
}
