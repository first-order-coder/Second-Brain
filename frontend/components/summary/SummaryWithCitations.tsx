'use client'
import { useState } from 'react'
import { Summary } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  HoverCard, 
  HoverCardContent, 
  HoverCardTrigger 
} from '@/components/ui/hover-card'
import { RefreshCw } from 'lucide-react'

interface SummaryWithCitationsProps {
  data: Summary
  onRefresh: () => void
  isRefreshing?: boolean
}

export function SummaryWithCitations({ data, onRefresh, isRefreshing = false }: SummaryWithCitationsProps) {
  const [hoveredCitation, setHoveredCitation] = useState<string | null>(null)

  const handleCitationClick = (chunkId: string) => {
    // TODO: Implement scroll to source viewer when available
    console.log('Citation clicked:', chunkId)
  }

  const renderCitationPreview = (citation: any) => {
    // For now, show a placeholder - in a real implementation, you'd fetch the chunk text
    return (
      <div className="space-y-2">
        <div className="font-medium text-slate-100 mb-1">Source preview</div>
        <div className="text-slate-300 text-sm">
          <div className="mb-1">Chunk: {citation.chunk_id}</div>
          {citation.score && (
            <div className="text-xs text-slate-400">
              Similarity: {(citation.score * 100).toFixed(1)}%
            </div>
          )}
          {citation.start_char !== null && citation.end_char !== null && (
            <div className="text-xs text-slate-400">
              Span: {citation.start_char}-{citation.end_char}
            </div>
          )}
        </div>
        <div className="text-xs text-slate-400 italic">
          Click to view in source
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold">Summary with Citations</h3>
        <Button 
          size="sm" 
          variant="secondary" 
          onClick={onRefresh}
          disabled={isRefreshing}
          className="btn-neutral"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? 'Generating...' : 'Refresh'}
        </Button>
      </div>

      {data.sentences.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-slate-400 mb-4">No summary available yet.</p>
          <p className="text-sm text-slate-500">
            Click "Refresh" to generate a citation-backed summary of this source.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {data.sentences.map((sentence) => (
            <div key={sentence.id} className="text-slate-200 leading-relaxed">
              <span className="text-base">{sentence.sentence_text}</span>{' '}
              {sentence.support_status === 'supported' && sentence.citations && sentence.citations.length > 0 ? (
                <div className="inline-flex items-center gap-2 ml-2">
                  <HoverCard>
                    <HoverCardTrigger asChild>
                      <Badge 
                        variant="outline" 
                        className="cursor-pointer hover:bg-blue-600/20 hover:border-blue-500/50 transition-colors"
                        onClick={() => handleCitationClick(sentence.citations[0].chunk_id)}
                      >
                        {sentence.citations.length} citation{sentence.citations.length > 1 ? 's' : ''}
                      </Badge>
                    </HoverCardTrigger>
                    <HoverCardContent className="w-96 text-sm bg-slate-800 border-slate-700">
                      {renderCitationPreview(sentence.citations[0])}
                    </HoverCardContent>
                  </HoverCard>
                  {sentence.citations.length > 1 && (
                    <span className="text-xs text-slate-400">
                      +{sentence.citations.length - 1} more
                    </span>
                  )}
                </div>
              ) : (
                <Badge 
                  variant="secondary" 
                  className="ml-2 bg-slate-800/50 text-slate-400 border-slate-700"
                >
                  insufficient context
                </Badge>
              )}
            </div>
          ))}
        </div>
      )}

      {data.sentences.length > 0 && (
        <div className="mt-6 pt-4 border-t border-white/10">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>
              {data.sentences.filter(s => s.support_status === 'supported').length} of {data.sentences.length} sentences supported
            </span>
            <span className="text-xs">
              Generated {new Date().toLocaleDateString()}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
