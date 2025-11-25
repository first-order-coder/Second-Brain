'use client'

import { useCallback, useState, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { apiUpload, apiPost, apiGet, ApiError } from '@/lib/apiClient'
import { createClient } from '@/lib/supabase/client'
import { ErrorAlert } from '@/components/ui/ErrorAlert'

interface PDFUploadProps {
  onUploadSuccess: (pdfId: string, filename?: string | null) => void
  onUploadStart: () => void
  onUploadEnd: () => void
}

interface UploadStatus {
  type: 'idle' | 'uploading' | 'success' | 'error'
  message?: string
  pdfId?: string
  details?: string[]
}

export default function PDFUpload({ onUploadSuccess, onUploadStart, onUploadEnd }: PDFUploadProps) {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({ type: 'idle' })
  const [currentFilename, setCurrentFilename] = useState<string | null>(null)
  const [userId, setUserId] = useState<string | null>(null)

  // Get user ID from Supabase on mount
  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) {
        setUserId(user.id)
      }
    })
  }, [])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return
    const filename = file.name.replace(/\.pdf$/i, '') // Remove .pdf extension for title
    console.log("[PDFUpload] File dropped:", { originalName: file.name, extractedFilename: filename });
    setCurrentFilename(filename)

    // Validate file type
    if (file.type !== 'application/pdf') {
      setUploadStatus({ 
        type: 'error', 
        message: 'Please upload a PDF file only.' 
      })
      return
    }

    // Validate file size (10MB default client guard)
    if (file.size > 10 * 1024 * 1024) {
      setUploadStatus({ 
        type: 'error', 
        message: 'File size must be less than 10MB.' 
      })
      return
    }

    setUploadStatus({ type: 'uploading', message: 'Uploading PDF...' })
    onUploadStart()

    try {
      const formData = new FormData()
      formData.append('file', file)

      // Add user_id header if available
      const headers: HeadersInit = {}
      if (userId) {
        headers['X-User-Id'] = userId
      }

      const result = await apiUpload<{ pdf_id: string; filename: string; status: string }>('/upload-pdf', formData, { headers })
      
      setUploadStatus({ 
        type: 'success', 
        message: 'PDF uploaded successfully!', 
        pdfId: result.pdf_id 
      })
      
      // Start flashcard generation - pass filename so it's available when completion happens
      await generateFlashcards(result.pdf_id, filename)
      
    } catch (error) {
      setUploadStatus({ 
        type: 'error', 
        message: error instanceof Error ? error.message : 'Upload failed' 
      })
      onUploadEnd()
    }
  }, [onUploadSuccess, onUploadStart, onUploadEnd])

  const generateFlashcards = async (pdfId: string, filename: string) => {
    try {
      setUploadStatus({ 
        type: 'uploading', 
        message: 'Generating flashcards with AI...' 
      })

      // Add user_id header if available
      const headers: HeadersInit = {}
      if (userId) {
        headers['X-User-Id'] = userId
      }

      await apiPost(`/generate-flashcards/${pdfId}`, undefined, { headers })

      // Poll for completion - capture filename in closure
      const pollStatus = async () => {
        try {
          const statusData = await apiGet<{ 
            pdf_id: string; 
            status: string; 
            deck_id?: string;
            deck_title?: string;
            error_message?: string 
          }>(`/status/${pdfId}`)
          
          if (statusData.status === 'completed') {
            // Use deckId from response if available, otherwise fall back to pdfId
            const deckId = statusData.deck_id || pdfId
            setUploadStatus({ 
              type: 'success', 
              message: 'Flashcards generated successfully!', 
              pdfId: deckId 
            })
            onUploadEnd()
            console.log("[PDFUpload] Processing complete:", { 
              pdfId, 
              deckId, 
              deckTitle: statusData.deck_title || filename,
              filename 
            });
            // Use deckId for navigation (which is the same as pdfId for PDFs)
            setTimeout(() => onUploadSuccess(deckId, statusData.deck_title || filename), 1000)
          } else if (['error', 'quota_exceeded', 'auth_error', 'timeout', 'service_error'].includes(statusData.status)) {
            // Use the error_message from backend, which should be user-friendly
            // If it looks like raw LLM output (contains markdown or is too long), sanitize it
            let errorMsg = statusData.error_message || 'Failed to generate flashcards. Please try again.'
            
            // Sanitize error messages that look like raw LLM output
            if (errorMsg.length > 200 || errorMsg.includes('```') || errorMsg.includes('First:') || errorMsg.includes('Then:')) {
              errorMsg = 'Failed to generate flashcards. The AI service returned an invalid response. Please try again.'
            }
            
            setUploadStatus({ 
              type: 'error', 
              message: errorMsg
            })
            onUploadEnd()
          } else {
            // Still processing, poll again
            setTimeout(pollStatus, 2000)
          }
        } catch (error) {
          setUploadStatus({ 
            type: 'error', 
            message: error instanceof Error ? error.message : 'Failed to check generation status.' 
          })
          onUploadEnd()
        }
      }

      pollStatus()
      
    } catch (error) {
      let errorMessage = 'Generation failed';
      let errorDetails: string[] | undefined = undefined;
      
      if (error instanceof Error) {
        errorMessage = error.message;
        
        // Check if error has nextSteps (from ApiError)
        if ('nextSteps' in error && Array.isArray(error.nextSteps)) {
          errorDetails = error.nextSteps;
        }
        
        // Provide helpful details for common generation errors
        if (errorMessage.includes('quota') || errorMessage.includes('429')) {
          errorDetails = ['AI service quota exceeded', 'Please try again later or contact support'];
        } else if (errorMessage.includes('timeout') || errorMessage.includes('504')) {
          errorDetails = ['The request took too long', 'Please try again with a smaller PDF'];
        } else if (errorMessage.includes('auth') || errorMessage.includes('401')) {
          errorDetails = ['AI service authentication failed', 'Please contact support'];
        }
      }
      
      setUploadStatus({ 
        type: 'error', 
        message: errorMessage,
        details: errorDetails
      })
      onUploadEnd()
    }
  }

  const { getRootProps: getRootPropsOriginal, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false,
    disabled: uploadStatus.type === 'uploading' || uploadStatus.type === 'success'
  })

  const rootProps = getRootPropsOriginal()

  const getStatusIcon = () => {
    switch (uploadStatus.type) {
      case 'uploading':
        return <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      case 'success':
        return <CheckCircle className="w-8 h-8 text-green-500" />
      case 'error':
        return <AlertCircle className="w-8 h-8 text-red-500" />
      default:
        return isDragActive ? (
          <Upload className="w-8 h-8 text-blue-500" />
        ) : (
          <FileText className="w-8 h-8 text-gray-400" />
        )
    }
  }

  const getStatusColor = () => {
    switch (uploadStatus.type) {
      case 'uploading':
        return 'border-blue-300 bg-blue-50'
      case 'success':
        return 'border-green-300 bg-green-50'
      case 'error':
        return 'border-red-300 bg-red-50'
      default:
        return isDragActive 
          ? 'border-blue-300 bg-blue-50' 
          : 'border-gray-300 bg-white'
    }
  }


  return (
    <div className="w-full">
      <motion.div
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-all duration-200 hover:border-blue-400 hover:bg-blue-50
          ${getStatusColor()}
          ${(uploadStatus.type === 'uploading' || uploadStatus.type === 'success') ? 'cursor-not-allowed' : ''}
        `}
        whileHover={uploadStatus.type === 'idle' ? { scale: 1.02 } : undefined}
        whileTap={uploadStatus.type === 'idle' ? { scale: 0.98 } : undefined}
        onClick={rootProps.onClick}
        onKeyDown={rootProps.onKeyDown}
        role={rootProps.role}
        tabIndex={rootProps.tabIndex}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center space-y-4">
          {getStatusIcon()}
          
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {uploadStatus.type === 'idle' && (isDragActive ? 'Drop your PDF here' : 'Upload a PDF file')}
              {uploadStatus.type === 'uploading' && 'Processing...'}
              {uploadStatus.type === 'success' && 'Success!'}
              {uploadStatus.type === 'error' && 'Upload Failed'}
            </h3>
            
            {uploadStatus.type === 'idle' && (
              <p className="text-gray-500">
                Drag and drop a PDF file here, or click to browse
                <br />
                <span className="text-sm">Maximum file size: 10MB</span>
              </p>
            )}
          </div>
        </div>
      </motion.div>

      <AnimatePresence>
        {uploadStatus.message && (
          uploadStatus.type === 'error' ? (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4"
            >
              <ErrorAlert
                title="PDF upload failed"
                message={uploadStatus.message}
                details={uploadStatus.details}
              />
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`mt-4 p-3 rounded-lg text-sm text-center ${
                uploadStatus.type === 'success' 
                  ? 'bg-green-100 text-green-700' 
                  : 'bg-blue-100 text-blue-700'
              }`}
            >
              {uploadStatus.message}
            </motion.div>
          )
        )}
      </AnimatePresence>

      {uploadStatus.type === 'error' && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => setUploadStatus({ type: 'idle' })}
          className="mt-4 w-full py-2 px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          Try Again
        </motion.button>
      )}
    </div>
  )
}
