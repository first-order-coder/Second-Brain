'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react'

interface ProcessingStatusProps {
  pdfId: string
  onComplete: () => void
  onError: () => void
}

interface Status {
  status: 'uploaded' | 'processing' | 'completed' | 'error' | 'quota_exceeded' | 'auth_error' | 'timeout' | 'service_error'
  error_message?: string
}

export default function ProcessingStatus({ pdfId, onComplete, onError }: ProcessingStatusProps) {
  const [status, setStatus] = useState<Status>({ status: 'processing' })
  const [dots, setDots] = useState('')

  // Animate dots
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.')
    }, 500)
    return () => clearInterval(interval)
  }, [])

  // Poll for status updates
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/status/${pdfId}`)
        const data = await response.json()
        setStatus(data)

        if (data.status === 'completed') {
          setTimeout(onComplete, 1000)
        } else if (['error', 'quota_exceeded', 'auth_error', 'timeout', 'service_error'].includes(data.status)) {
          setTimeout(onError, 1000)
        } else {
          // Continue polling
          setTimeout(pollStatus, 2000)
        }
      } catch (error) {
        console.error('Error polling status:', error)
        setTimeout(pollStatus, 5000) // Retry after 5 seconds
      }
    }

    pollStatus()
  }, [pdfId, onComplete, onError])

  const getStatusIcon = () => {
    switch (status.status) {
      case 'completed':
        return <CheckCircle className="w-16 h-16 text-green-500" />
      case 'quota_exceeded':
        return <AlertCircle className="w-16 h-16 text-yellow-500" />
      case 'auth_error':
        return <AlertCircle className="w-16 h-16 text-red-500" />
      case 'timeout':
        return <AlertCircle className="w-16 h-16 text-orange-500" />
      case 'service_error':
        return <AlertCircle className="w-16 h-16 text-purple-500" />
      case 'error':
        return <AlertCircle className="w-16 h-16 text-red-500" />
      default:
        return <Loader2 className="w-16 h-16 text-blue-500 animate-spin" />
    }
  }

  const getStatusMessage = () => {
    switch (status.status) {
      case 'completed':
        return 'Flashcards generated successfully!'
      case 'quota_exceeded':
        return status.error_message || 'AI quota exceeded, please try again later'
      case 'auth_error':
        return status.error_message || 'AI service authentication failed, please contact support'
      case 'timeout':
        return status.error_message || 'AI service timeout, please try again later'
      case 'service_error':
        return status.error_message || 'AI service temporarily unavailable, please try again later'
      case 'error':
        return status.error_message || 'Failed to generate flashcards, please try again later'
      default:
        return `Generating flashcards with AI${dots}`
    }
  }

  const getStatusColor = () => {
    switch (status.status) {
      case 'completed':
        return 'bg-green-50 border-green-200'
      case 'quota_exceeded':
        return 'bg-yellow-50 border-yellow-200'
      case 'auth_error':
        return 'bg-red-50 border-red-200'
      case 'timeout':
        return 'bg-orange-50 border-orange-200'
      case 'service_error':
        return 'bg-purple-50 border-purple-200'
      case 'error':
        return 'bg-red-50 border-red-200'
      default:
        return 'bg-blue-50 border-blue-200'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`max-w-md w-full mx-4 p-8 rounded-lg shadow-lg border-2 ${getStatusColor()}`}
      >
        <div className="text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            className="mb-6"
          >
            {getStatusIcon()}
          </motion.div>
          
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-2xl font-bold text-gray-900 mb-4"
          >
            {status.status === 'completed' ? 'Ready to Study!' : 
             ['error', 'quota_exceeded', 'auth_error', 'timeout', 'service_error'].includes(status.status) ? 'Oops!' : 
             'Processing Your PDF'}
          </motion.h2>
          
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="text-lg text-gray-600 mb-6"
          >
            {getStatusMessage()}
          </motion.p>

          {status.status === 'processing' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="space-y-4"
            >
              <div className="text-sm text-gray-500">
                <p>Our AI is analyzing your PDF and creating intelligent flashcards...</p>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-2">
                <motion.div
                  className="bg-blue-500 h-2 rounded-full"
                  animate={{ width: ['0%', '100%'] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                />
              </div>
            </motion.div>
          )}

          {['error', 'quota_exceeded', 'auth_error', 'timeout', 'service_error'].includes(status.status) && (
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              onClick={() => window.location.href = '/'}
              className="w-full px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
            >
              Try Again
            </motion.button>
          )}
        </div>
      </motion.div>
    </div>
  )
}
