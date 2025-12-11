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

  const saveDeckSilently = useCallback((deckId: string, filename?: string | null) => {
    // PDFUpload already removes .pdf extension, but handle any remaining extensions just in case
    const title = filename ? filename.replace(/\.[^/.]+$/, "") : null;
    console.log("[saveDeckSilently] Payload:", {
      deckId,
      filename,
      extractedTitle: title,
      sourceType: "pdf",
      sourceLabel: title,
    });
    
    // CRITICAL: Only save if we have a title - don't send null for new decks
    if (!title) {
      console.warn("[Home] No title available, skipping save. Filename was:", filename);
      return;
    }
    
    fetch("/api/save-deck", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        deckId,
        title, // Always send a real title, never null
        sourceType: "pdf",
        sourceLabel: title,
      }),
    }).then(async (res) => {
      const json = await res.json().catch(() => ({}));
      if (!json?.ok) {
        console.warn("[Home] save-deck failed", { deckId, json });
      } else {
        console.log("[Home] save-deck succeeded", { deckId, title });
      }
    }).catch((error) => {
      console.warn("[Home] save-deck error", { deckId, error });
    });
  }, []);

  const handleUploadSuccess = useCallback((pdfId: string, filename?: string | null) => {
    // Extract title (PDFUpload already removed .pdf, but be defensive)
    // CRITICAL: Always derive a clean title from filename
    const cleanTitle = filename ? filename.replace(/\.[^/.]+$/, "").trim() : null;
    
    if (!cleanTitle) {
      console.error("[Home] No title available from filename", { pdfId, filename });
      // Still navigate but without title - SaveOnLoad won't run, which is fine
      router.push(`/flashcards/${pdfId}`);
      return;
    }
    
    // Use original filename (with extension) as sourceLabel
    const sourceLabel = filename || cleanTitle;
    
    console.log("[PDFUpload] onGenerate success:", {
      deckId: pdfId,
      deckTitle: cleanTitle,
      sourceLabel,
    });
    
    // Save deck with title and sourceLabel
    saveDeckSilently(pdfId, filename);
    
    // Pass ALL params via URL so flashcard page can use them
    const query = new URLSearchParams({
      title: cleanTitle,
      sourceType: 'pdf',
      sourceLabel: sourceLabel,
    });
    
    console.log("[Home] Navigating to flashcard page:", { 
      pdfId, 
      title: cleanTitle, 
      sourceLabel,
      query: query.toString() 
    });
    router.push(`/flashcards/${pdfId}?${query.toString()}`);
  }, [router, saveDeckSilently])

  return (
    <main className="flex-1">
      {/* HERO SECTION: Centered heading + large upload area */}
      <section className="pt-8 pb-6 sm:pt-10 sm:pb-8">
        <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
          {/* Centered Hero Text */}
          <div className="text-center">
            <motion.h1
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white"
            >
              Learn faster. Remember longer.
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.05 }}
              className="mt-3 text-base sm:text-lg leading-relaxed sb-muted dark:text-slate-300 max-w-2xl mx-auto"
            >
              Second Brain turns PDFs, links, and videos into reliable notes and exam-ready flashcards—with spaced repetition built in.
            </motion.p>
          </div>

          {/* Large, Full-Width PDF Upload Area */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.1 }}
            className="mt-6 w-full"
          >
            <div className="sb-surface-2 sb-surface-hover p-3 sm:p-4">
              <PDFUpload 
                onUploadSuccess={handleUploadSuccess}
                onUploadStart={() => setIsUploading(true)}
                onUploadEnd={() => setIsUploading(false)}
              />
            </div>
          </motion.div>
        </div>
      </section>

      {/* HOW IT WORKS SECTION: Three steps - directly below upload */}
      <section className="border-t border-slate-200 dark:border-slate-700/50 sb-band">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
          <motion.h2
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
            className="text-center text-lg sm:text-xl font-semibold text-slate-900 dark:text-white"
          >
            How Second Brain Works
          </motion.h2>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.2 }}
            className="mt-6 grid gap-4 sm:gap-6 md:grid-cols-3"
          >
            <div className="sb-surface-1 sb-surface-hover p-4 sm:p-5 text-center">
              <div className="sb-kicker">1. Import</div>
              <p className="mt-2 text-sm sb-muted dark:text-slate-300">Drop a PDF, paste a link, or add a YouTube video.</p>
            </div>

            <div className="sb-surface-1 sb-surface-hover p-4 sm:p-5 text-center">
              <div className="sb-kicker">2. Generate</div>
              <p className="mt-2 text-sm sb-muted dark:text-slate-300">We parse, cite, and create 10 study-ready flashcards.</p>
            </div>

            <div className="sb-surface-1 sb-surface-hover p-4 sm:p-5 text-center">
              <div className="sb-kicker">3. Review</div>
              <p className="mt-2 text-sm sb-muted dark:text-slate-300">Reveal → grade (1–4) with spaced repetition.</p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* SUPPORTING SECTION: Supported sources */}
      <section className="border-t border-slate-200 dark:border-slate-700/50">
        <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
          {/* Supported sources */}
          <div>
            <div className="sb-kicker mb-3">Supported sources</div>
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
        </div>
      </section>

      {/* YOUTUBE IMPORT SECTION */}
      <section className="border-t border-slate-200 dark:border-slate-700/50">
        <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.15 }}
            className="w-full"
          >
            <div className="sb-surface-2 sb-surface-hover p-3 sm:p-4">
              <YTToCards />
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="sb-section sb-band-grad">
        <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-3 gap-6">
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
        <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8 text-center sb-surface-1 p-8">
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
