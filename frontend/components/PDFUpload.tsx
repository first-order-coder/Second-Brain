'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface PDFUploadProps {
  onUploadSuccess: (pdfId: string) => void
  onUploadStart: () => void
  onUploadEnd: () => void
}

interface UploadStatus {
  type: 'idle' | 'uploading' | 'success' | 'error'
  message?: string
  pdfId?: string
}

export default function PDFUpload({ onUploadSuccess, onUploadStart, onUploadEnd }: PDFUploadProps) {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({ type: 'idle' })

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

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

      const response = await fetch('/api/upload/pdf', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        let errorMessage = 'Upload failed'
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || 'Upload failed'
        } catch (parseError) {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`
        }
        console.error('Upload error:', errorMessage, response.status)
        throw new Error(errorMessage)
      }

      const result = await response.json()
      
      setUploadStatus({ 
        type: 'success', 
        message: 'PDF uploaded successfully!', 
        pdfId: result.pdf_id 
      })
      
      // Start flashcard generation
      await generateFlashcards(result.pdf_id)
      
    } catch (error) {
      setUploadStatus({ 
        type: 'error', 
        message: error instanceof Error ? error.message : 'Upload failed' 
      })
      onUploadEnd()
    }
  }, [onUploadSuccess, onUploadStart, onUploadEnd])

  const generateFlashcards = async (pdfId: string) => {
    try {
      setUploadStatus({ 
        type: 'uploading', 
        message: 'Generating flashcards with AI...' 
      })

      const response = await fetch(`/api/generate-flashcards/${pdfId}`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Flashcard generation failed')
      }

      // Poll for completion
      const pollStatus = async () => {
        try {
          const statusResponse = await fetch(`/api/status/${pdfId}`)
          const statusData = await statusResponse.json()
          
          if (statusData.status === 'completed') {
            setUploadStatus({ 
              type: 'success', 
              message: 'Flashcards generated successfully!', 
              pdfId 
            })
            onUploadEnd()
            setTimeout(() => onUploadSuccess(pdfId), 1000)
          } else if (['error', 'quota_exceeded', 'auth_error', 'timeout', 'service_error'].includes(statusData.status)) {
            setUploadStatus({ 
              type: 'error', 
              message: statusData.error_message || 'Failed to generate flashcards. Please try again.' 
            })
            onUploadEnd()
          } else {
            // Still processing, poll again
            setTimeout(pollStatus, 2000)
          }
        } catch (error) {
          setUploadStatus({ 
            type: 'error', 
            message: 'Failed to check generation status.' 
          })
          onUploadEnd()
        }
      }

      pollStatus()
      
    } catch (error) {
      setUploadStatus({ 
        type: 'error', 
        message: error instanceof Error ? error.message : 'Generation failed' 
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
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`mt-4 p-3 rounded-lg text-sm text-center ${
              uploadStatus.type === 'success' 
                ? 'bg-green-100 text-green-700' 
                : uploadStatus.type === 'error'
                ? 'bg-red-100 text-red-700'
                : 'bg-blue-100 text-blue-700'
            }`}
          >
            {uploadStatus.message}
          </motion.div>
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
