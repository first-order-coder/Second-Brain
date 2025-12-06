'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ChevronLeft, ChevronRight, RotateCcw, Upload, ArrowLeft } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface Flashcard {
  id: number
  question: string
  answer: string
  card_number: number
}

interface FlashcardViewerProps {
  pdfId: string
  flashcards: Flashcard[]
}

export default function FlashcardViewer({ pdfId, flashcards }: FlashcardViewerProps) {
  const router = useRouter()
  const [currentCardIndex, setCurrentCardIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [autoAdvance, setAutoAdvance] = useState(true)
 

  const totalCards = flashcards.length
  const currentCard = flashcards[currentCardIndex]

  // Button style constants for consistent premium styling
  const baseBtn = "inline-flex items-center gap-2 px-5 py-2.5 rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-slate-900"
  const primaryBtn = `${baseBtn} bg-blue-600 text-white shadow-sm hover:bg-blue-700 hover:shadow-md focus:ring-blue-500/40 hover:translate-y-[-1px]`
  const neutralBtn = `${baseBtn} border border-gray-300 dark:border-white/20 bg-white/70 text-gray-900 hover:bg-white dark:bg-slate-900/50 dark:text-white hover:translate-y-[-1px]`
  const secondaryBtn = `${baseBtn} bg-gray-100 text-gray-900 hover:bg-gray-200 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-900 hover:translate-y-[-1px]`

  // Grading button styles (Again button removed from UI)
  const hardBtn = `${baseBtn} bg-amber-600 text-white hover:bg-amber-700 hover:translate-y-[-1px]`
  const goodBtn = `${baseBtn} bg-emerald-600 text-white hover:bg-emerald-700 hover:translate-y-[-1px]`
  const easyBtn = `${baseBtn} bg-sky-600 text-white hover:bg-sky-700 hover:translate-y-[-1px]`

  useEffect(() => {
    // Optional: scroll to top when changing cards
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [currentCardIndex])

  // Keyboard shortcuts for accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable) return
      
      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault()
        if (!revealed) {
          setRevealed(true)
        } else {
          setRevealed(false)
        }
      }
      
      if (!revealed) {
        if (e.key === 'ArrowLeft') {
          e.preventDefault()
          prevCard()
        }
        if (e.key === 'ArrowRight') {
          e.preventDefault()
          nextCard()
        }
        return
      }
      
      if (revealed) {
        if (e.key === '1') {
          e.preventDefault()
          onGrade(1)
        }
        if (e.key === '2') {
          e.preventDefault()
          onGrade(2)
        }
        if (e.key === '3') {
          e.preventDefault()
          onGrade(3)
        }
        if (e.key === '4') {
          e.preventDefault()
          onGrade(4)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [revealed, currentCardIndex, autoAdvance, totalCards])

  if (totalCards === 0 || !currentCard) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-slate-900 dark:to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">No Flashcards Available</h1>
          <p className="text-gray-600 dark:text-gray-300 mb-8">Please upload a PDF to generate flashcards.</p>
          <button
            onClick={() => router.push('/')}
            className={primaryBtn}
          >
            <Upload className="w-5 h-5" />
            Upload PDF
          </button>
        </div>
      </div>
    )
  }

  const handleReveal = (e?: React.MouseEvent) => {
    e?.stopPropagation?.()
    setRevealed(true)
  }

  const handleHide = (e?: React.MouseEvent) => {
    e?.stopPropagation?.()
    setRevealed(false)
  }

  const onGrade = (score: 1 | 2 | 3 | 4) => {
    console.log('graded', { index: currentCardIndex, score, card: currentCard.id })
    // TODO: POST /reviews later
    
    if (autoAdvance && currentCardIndex < totalCards - 1) {
      setCurrentCardIndex(i => i + 1)
      setRevealed(false)
    }
  }

  const prevCard = () => {
    if (currentCardIndex > 0) {
      setCurrentCardIndex(i => i - 1)
      setRevealed(false) // Reset to hidden state when navigating
    }
  }

  const nextCard = () => {
    if (currentCardIndex < totalCards - 1) {
      setCurrentCardIndex(i => i + 1)
      setRevealed(false) // Reset to hidden state when navigating
    }
  }

  const resetCards = () => {
    setCurrentCardIndex(0)
    setRevealed(false) // Reset to hidden state when resetting
  }

  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-slate-900 dark:to-slate-950">
      {/* Header */}
      <header className="px-4 pt-4 pb-2">
        <div className="bg-white/80 dark:bg-slate-900/70 backdrop-blur-sm shadow-sm border-b border-gray-200/60 dark:border-white/10 rounded-b-lg">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <button
                onClick={() => router.push('/')}
                className="flex items-center text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Back to Upload
              </button>
              <div className="text-sm text-gray-600 dark:text-gray-300">
                Card {currentCardIndex + 1} of {totalCards}
              </div>
            </div>

            {/* Progress Bar */}
            <div className="mt-4">
              <div className="w-full bg-gray-200/70 dark:bg-white/10 rounded-full h-2 overflow-hidden">
                <motion.div
                  className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full shadow-[0_2px_6px_rgba(37,99,235,0.45)]"
                  initial={{ width: 0 }}
                  animate={{ width: `${((currentCardIndex + 1) / totalCards) * 100}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main - Card and controls with consistent button positioning */}
      <main className="flex-1 px-4 pb-6">
        <div className="mx-auto flex min-h-[calc(100vh-170px)] max-w-4xl flex-col justify-between gap-6">
          {/* Card area - vertically centered within its slot */}
          <div className="flex-1 flex items-center">
            <div className="w-full">
              {/* Flashcard with premium styling */}
              <motion.div
                key={`card-${currentCardIndex}`}
                initial={{ opacity: 0, y: 16, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
                onClick={!revealed ? handleReveal : undefined}
                className="bg-white/80 dark:bg-slate-900/70 border border-gray-200/60 dark:border-white/10 rounded-2xl shadow-[0_10px_30px_-10px_rgba(2,6,23,0.25)] p-8 sm:p-10 text-center select-none cursor-pointer hover:shadow-lg transition-shadow flex flex-col justify-center max-h-[calc(100vh-280px)] overflow-y-auto"
              >
                <span className="inline-block mb-3 bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-200 text-xs font-medium px-3 py-1 rounded-full">
                  Question
                </span>
                <h2 className="text-center text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-white leading-relaxed break-words">
                  {currentCard.question}
                </h2>
                
                {!revealed && (
                  <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">
                    Click to reveal answer
                  </p>
                )}
                
                {revealed && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className="mt-4"
                  >
                    <div className="p-5 rounded-xl border bg-emerald-50/80 border-emerald-200/70 text-emerald-900 dark:bg-emerald-900/20 dark:border-emerald-700/40 dark:text-emerald-100">
                      <span className="inline-block mb-2 bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200 text-xs font-medium px-3 py-1 rounded-full">
                        Answer
                      </span>
                      <p className="text-lg sm:text-xl leading-relaxed break-words">{currentCard.answer}</p>
                    </div>
                  </motion.div>
                )}
                
              </motion.div>

              {/* Accessibility - Live region for screen readers */}
              <div className="sr-only" aria-live="polite">
                {revealed ? 'Answer revealed' : 'Answer hidden'}
              </div>
            </div>
          </div>

          {/* Controls - anchored near bottom with consistent spacing */}
          <div className="pb-2">
            <div className="flex flex-wrap items-center justify-center gap-3 sm:justify-between">
              <button 
                onClick={prevCard} 
                disabled={currentCardIndex === 0} 
                className={`${secondaryBtn} disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0`}
              >
                <ChevronLeft className="w-5 h-5" /> 
                Previous
              </button>

              <div className="flex flex-wrap items-center justify-center gap-3">
                {!revealed ? (
                  <button onClick={handleReveal} className={primaryBtn}>
                    Reveal Answer
                  </button>
                ) : (
                  <>
                    {/* Again (1) button removed from UI */}
                    <button onClick={() => onGrade(2)} className={hardBtn}>
                      Hard (2)
                    </button>
                    <button onClick={() => onGrade(3)} className={goodBtn}>
                      Good (3)
                    </button>
                    <button onClick={() => onGrade(4)} className={easyBtn}>
                      Easy (4)
                    </button>
                  </>
                )}
                <button onClick={resetCards} className={neutralBtn}>
                  <RotateCcw className="w-5 h-5" /> 
                  Reset
                </button>
              </div>

              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-gray-300 dark:border-white/20"
                    checked={autoAdvance}
                    onChange={(e) => setAutoAdvance(e.target.checked)}
                  />
                  Auto-advance
                </label>

                <button 
                  onClick={nextCard} 
                  disabled={currentCardIndex === totalCards - 1} 
                  className={`${secondaryBtn} disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0`}
                >
                  Next 
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
      
    </div>
  )
}