import { Summary } from './types';
import { apiGet, apiPost } from './apiClient';

export async function getSummary(sourceId: string): Promise<Summary> {
  try {
    return await apiGet<Summary>(`/summaries/${sourceId}`);
  } catch (error) {
    // Return empty summary if not found (404) or other errors
    if (error instanceof Error && error.message.includes('404')) {
      return {
        summary_id: '',
        source_id: sourceId,
        sentences: []
      };
    }
    throw error;
  }
}

export async function refreshSummary(sourceId: string): Promise<{status: string, task_id?: string, summary_id?: string}> {
  try {
    return await apiPost<{status: string, task_id?: string, summary_id?: string}>(`/summaries/${sourceId}/refresh`);
  } catch (error) {
    console.error('Refresh failed:', error);
    throw error;
  }
}

// ============ Inline editor helpers (additive) ============

// ============ YouTube ingest helper (additive) ============
export async function ingestYoutube(url: string) {
  return await apiPost('/ingest/url', { url, kind: 'youtube' });
}
