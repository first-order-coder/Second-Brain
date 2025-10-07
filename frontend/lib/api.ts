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

export async function refreshSummary(sourceId: string): Promise<{status: string, task_id?: string, summary_id?: string}> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/summaries/${sourceId}/refresh`, { 
    method: 'POST' 
  });
  const text = await res.text();
  
  if (!res.ok) {
    console.error('Refresh failed:', res.status, text);
    let errorMessage = 'Failed to refresh summary';
    try {
      const errorData = JSON.parse(text);
      if (errorData.detail) {
        errorMessage = errorData.detail;
      } else if (errorData.error) {
        errorMessage = errorData.error;
      }
    } catch (e) {
      // Use default error message if parsing fails
    }
    throw new Error(errorMessage);
  }
  
  try {
    return JSON.parse(text);
  } catch (e) {
    throw new Error('Invalid response from server');
  }
}

// ============ Inline editor helpers (additive) ============
 

