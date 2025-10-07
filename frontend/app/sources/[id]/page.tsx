'use client'
import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { SummaryWithCitations } from '@/components/summary/SummaryWithCitations'
import { getSummary, refreshSummary } from '@/lib/api'
import { Summary } from '@/lib/types'
import { ArrowLeft, FileText, AlertCircle } from 'lucide-react'

export default function SourcePage() {
  const params = useParams()
  const router = useRouter()
  const sourceId = params.id as string
  
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)
  const [pollCount, setPollCount] = useState(0)

  useEffect(() => {
    loadSummary()
  }, [sourceId])

  const loadSummary = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getSummary(sourceId)
      setSummary(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load summary')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    try {
      setRefreshing(true)
      setError(null)
      setPollCount(0)
      
      const result = await refreshSummary(sourceId)
      
      if (result.status === 'queued') {
        // Start polling for completion
        setPolling(true)
        startPolling()
      } else if (result.status === 'ok') {
        // Inline completion, reload summary
        setTimeout(() => {
          loadSummary()
        }, 1000)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh summary')
      setPolling(false)
    } finally {
      setRefreshing(false)
    }
  }

  const startPolling = () => {
    const pollInterval = setInterval(async () => {
      if (pollCount >= 20) { // Max 20 polls (30 seconds)
        clearInterval(pollInterval)
        setPolling(false)
        setError('Summary generation timed out. Please try again.')
        return
      }
      
      try {
        await loadSummary()
        // Check if summary now has sentences
        if (summary && summary.sentences && summary.sentences.length > 0) {
          clearInterval(pollInterval)
          setPolling(false)
          return
        }
        setPollCount(prev => prev + 1)
      } catch (err) {
        console.error('Polling error:', err)
        setPollCount(prev => prev + 1)
      }
    }, 1500)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-slate-900 dark:to-slate-950">
      {/* Header */}
      <div className="bg-white/80 dark:bg-slate-900/70 backdrop-blur-sm shadow-sm border-b border-gray-200/60 dark:border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => router.push('/')}
              className="flex items-center text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Back to Upload
            </button>
            <div className="flex items-center text-gray-600 dark:text-gray-400">
              <FileText className="w-5 h-5 mr-2" />
              Source: {sourceId.slice(0, 8)}...
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Feature Info */}
          <div className="mb-8 rounded-2xl border border-white/10 bg-slate-900/60 p-6">
            <h1 className="text-2xl font-semibold text-white mb-2">
              Citation-Backed Summary
            </h1>
            <p className="text-slate-300 leading-relaxed">
              This summary shows each sentence backed by citations to specific source chunks. 
              Hover over citations to preview the supporting text, or click to jump to the source.
              Sentences without sufficient support are marked as "insufficient context".
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-6 rounded-2xl border border-red-500/20 bg-red-900/20 p-4 flex items-center">
              <AlertCircle className="w-5 h-5 text-red-400 mr-3" />
              <div>
                <h3 className="text-red-400 font-medium">Error</h3>
                <p className="text-red-300 text-sm mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Polling Status */}
          {polling && (
            <div className="mb-6 rounded-2xl border border-blue-500/20 bg-blue-900/20 p-4 flex items-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-400 mr-3"></div>
              <div>
                <h3 className="text-blue-400 font-medium">Building Summary...</h3>
                <p className="text-blue-300 text-sm mt-1">
                  Generating citation-backed summary (attempt {pollCount}/20)
                </p>
              </div>
            </div>
          )}

          {/* Summary Component */}
          {loading ? (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-8">
              <div className="animate-pulse">
                <div className="flex items-center justify-between mb-4">
                  <div className="h-6 bg-slate-700 rounded w-48"></div>
                  <div className="h-8 bg-slate-700 rounded w-24"></div>
                </div>
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="space-y-2">
                      <div className="h-4 bg-slate-700 rounded w-full"></div>
                      <div className="h-4 bg-slate-700 rounded w-3/4"></div>
                      <div className="h-6 bg-slate-700 rounded w-24"></div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : summary ? (
            <SummaryWithCitations 
              data={summary}
              onRefresh={handleRefresh}
              isRefreshing={refreshing || polling}
            />
          ) : (
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-8 text-center">
              <FileText className="w-12 h-12 text-slate-500 mx-auto mb-4" />
              <h3 className="text-white font-medium mb-2">No Summary Available</h3>
              <p className="text-slate-400 mb-4">
                Generate a citation-backed summary for this source.
              </p>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="btn btn-primary"
              >
                {refreshing ? 'Generating...' : 'Generate Summary'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

