import { Summary } from './types';

export async function getSummary(sourceId: string): Promise<Summary> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/summaries/${sourceId}`, { 
    cache: 'no-store' 
  });
  if (!res.ok) {
    if (res.status === 404) {
      // Return empty summary if not found
      return {
        summary_id: '',
        source_id: sourceId,
        sentences: []
      };
    }
    throw new Error('Failed to fetch summary');
  }
  return res.json();
}

export async function refreshSummary(sourceId: string): Promise<void> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/summaries/${sourceId}/refresh`, { 
    method: 'POST' 
  });
  if (!res.ok) {
    throw new Error('Failed to refresh summary');
  }
}

// ============ Inline editor helpers (additive) ============
 

