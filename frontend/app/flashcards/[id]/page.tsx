'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import FlashcardViewer from '@/components/FlashcardViewer'
import SaveOnLoad from './SaveOnLoad'
import ProcessingStatus from '@/components/ProcessingStatus'

interface Flashcard {
  id: number
  question: string
  answer: string
  card_number: number
}

interface FlashcardData {
  pdf_id: string
  status: string
  flashcards: Flashcard[]
}

export default function FlashcardPage() {
  const params = useParams()
  const pdfId = params.id as string
  const [flashcardData, setFlashcardData] = useState<FlashcardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchFlashcards()
  }, [pdfId])

  const fetchFlashcards = async () => {
    try {
      const response = await fetch(`/api/flashcards/${pdfId}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch flashcards')
      }
      
      const data = await response.json()
      setFlashcardData(data)
      setLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setLoading(false)
    }
  }

  const handleProcessingComplete = () => {
    // Refresh the flashcards data
    fetchFlashcards()
  }

  const handleProcessingError = () => {
    setError('Failed to generate flashcards. Please try again.')
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading flashcards...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-md w-full mx-4 p-8 bg-red-50 border border-red-200 rounded-lg shadow-lg">
          <div className="text-center">
            <div className="text-red-500 text-4xl mb-4">⚠️</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Error</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <button
              onClick={() => window.location.href = '/'}
              className="w-full px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
            >
              Back to Home
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!flashcardData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No data available</p>
        </div>
      </div>
    )
  }

  // Show processing status if still processing
  if (flashcardData.status === 'processing') {
    return (
      <ProcessingStatus
        pdfId={pdfId}
        onComplete={handleProcessingComplete}
        onError={handleProcessingError}
      />
    )
  }

  // Show error if processing failed
  if (flashcardData.status === 'error') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-md w-full mx-4 p-8 bg-red-50 border border-red-200 rounded-lg shadow-lg">
          <div className="text-center">
            <div className="text-red-500 text-4xl mb-4">⚠️</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Processing Failed</h2>
            <p className="text-gray-600 mb-6">
              We couldn't process your PDF. This might be due to:
            </p>
            <ul className="text-left text-gray-600 mb-6 space-y-2">
              <li>• PDF is encrypted or corrupted</li>
              <li>• No text content found in the PDF</li>
              <li>• AI service temporarily unavailable</li>
            </ul>
            <button
              onClick={() => window.location.href = '/'}
              className="w-full px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Show flashcards if completed
  if (flashcardData.status === 'completed' && flashcardData.flashcards.length > 0) {
    return (
      <>
        <SaveOnLoad deckId={pdfId} />
        <FlashcardViewer pdfId={pdfId} flashcards={flashcardData.flashcards} />
      </>
    )
  }

  // No flashcards available
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="max-w-md w-full mx-4 p-8 bg-white border border-gray-200 rounded-lg shadow-lg">
        <div className="text-center">
          <div className="text-gray-400 text-4xl mb-4">📚</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">No Flashcards Found</h2>
          <p className="text-gray-600 mb-6">
            We couldn't generate flashcards from your PDF. Please try uploading a different file.
          </p>
          <button
            onClick={() => window.location.href = '/'}
            className="w-full px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Upload New PDF
          </button>
        </div>
      </div>
    </div>
  )
}
