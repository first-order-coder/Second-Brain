'use client'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { BookOpen, Sparkles, Layers, Upload, FileUp, Brain, Link as LinkIcon, Youtube, FileText } from 'lucide-react'
import PDFUpload from '@/components/PDFUpload'
import { useRouter } from 'next/navigation'

export default function Page() {
  const [isUploading, setIsUploading] = useState(false)
  const router = useRouter()

  const handleUploadSuccess = (pdfId: string) => {
    router.push(`/flashcards/${pdfId}`)
  }

  const loadDemo = () => {
    // TODO: route to a seeded demo deck or query param
    router.push('/flashcards/demo')
  }

  return (
    <main>
      {/* Hero */}
      <section className="relative">
        <div className="mx-auto max-w-6xl px-4 py-24 sm:py-28">
          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="text-4xl sm:text-5xl font-semibold tracking-tight text-white"
          >
            Learn faster. Remember longer.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.05 }}
            className="mt-4 max-w-2xl text-base sm:text-lg leading-relaxed text-slate-300"
          >
            Second Brain turns PDFs, links, and videos into reliable notes and exam-ready flashcards—with spaced repetition built in.
          </motion.p>
          
          {/* New grid: uploader (left) + quick start (right) */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.1 }}
            className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-8 items-start"
          >
            {/* LEFT: Upload Component */}
            <div>
              <PDFUpload 
                onUploadSuccess={handleUploadSuccess}
                onUploadStart={() => setIsUploading(true)}
                onUploadEnd={() => setIsUploading(false)}
              />
            </div>

            {/* RIGHT: Quick Start */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.15 }}
              className="space-y-4"
            >
              <h3 className="text-lg font-semibold text-white">Quick start</h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
                  <div className="flex items-center gap-2 text-slate-300">
                    <FileUp className="w-4 h-4 text-blue-300/90" />
                    <span className="text-sm font-medium text-white">1. Import</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">Drop a PDF, paste a link, or add a YouTube video.</p>
                </div>

                <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Sparkles className="w-4 h-4 text-blue-300/90" />
                    <span className="text-sm font-medium text-white">2. Generate</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">We parse, cite, and create 10 study-ready flashcards.</p>
                </div>

                <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Brain className="w-4 h-4 text-blue-300/90" />
                    <span className="text-sm font-medium text-white">3. Review</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">Reveal → grade (1–4) with spaced repetition for retention.</p>
                </div>
              </div>

              {/* Supported sources */}
              <div className="mt-4">
                <p className="text-sm text-slate-400 mb-2">Supported sources</p>
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-slate-900/60 text-slate-300 text-sm">
                    <LinkIcon className="w-4 h-4 text-blue-300/90" /> URL
                  </span>
                  <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-slate-900/60 text-slate-300 text-sm">
                    <FileText className="w-4 h-4 text-blue-300/90" /> PDF
                  </span>
                  <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-slate-900/60 text-slate-300 text-sm">
                    <Youtube className="w-4 h-4 text-blue-300/90" /> YouTube
                  </span>
                  <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-slate-900/60 text-slate-500 text-sm">
                    <BookOpen className="w-4 h-4" /> Notion (soon)
                  </span>
                  <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-slate-900/60 text-slate-500 text-sm">
                    <BookOpen className="w-4 h-4" /> Obsidian (soon)
                  </span>
                </div>
              </div>

              {/* Demo panel */}
              <div className="mt-4 rounded-2xl border border-white/10 bg-slate-900/60 p-6 flex items-center justify-between gap-4">
                <div>
                  <h4 className="text-white font-semibold">No file handy?</h4>
                  <p className="text-sm text-slate-400">Load a sample deck to see the review flow in action.</p>
                </div>
                <button
                  onClick={loadDemo}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-500 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500/40 focus:ring-offset-slate-900"
                >
                  See a live demo
                </button>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 sm:py-20">
        <div className="mx-auto max-w-6xl px-4 grid grid-cols-1 sm:grid-cols-3 gap-6">
          <motion.div 
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="card-dark p-6 sm:p-8"
          >
            <BookOpen className="w-6 h-6 text-blue-300/90" />
            <h3 className="mt-4 text-xl font-semibold text-white">Ingest anything</h3>
            <p className="mt-2 text-slate-400">URLs, PDFs, YouTube—clean parsing and citations you can trust.</p>
          </motion.div>
          <motion.div 
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="card-dark p-6 sm:p-8"
          >
            <Sparkles className="w-6 h-6 text-blue-300/90" />
            <h3 className="mt-4 text-xl font-semibold text-white">Great flashcards</h3>
            <p className="mt-2 text-slate-400">Auto-generated, editable, and validated against your sources.</p>
          </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.3 }}
                className="card-dark p-6 sm:p-8"
              >
                <Layers className="w-6 h-6 text-blue-300/90" />
                <h3 className="mt-4 text-xl font-semibold text-white">Spaced repetition</h3>
                <p className="mt-2 text-slate-400">SM-2 scheduling with a smooth daily review flow.</p>
                <div className="mt-4">
                  <a 
                    href="/sources/demo" 
                    className="text-sm text-blue-300/90 hover:text-blue-200 transition-colors"
                  >
                    View citation-backed summaries →
                  </a>
                </div>
              </motion.div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-16 sm:py-20 border-t border-white/10">
        <div className="mx-auto max-w-6xl px-4 text-center">
          <h2 className="text-2xl sm:text-3xl font-semibold text-white">Start your next study session</h2>
          <p className="mt-3 text-slate-400">Import a PDF or paste a link—your study queue will be ready in minutes.</p>
          <div className="mt-6">
            <a href="/signup" className="btn btn-primary">Create free account</a>
          </div>
        </div>
      </section>
    </main>
  )
}
