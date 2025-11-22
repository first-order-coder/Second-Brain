/**
 * Get the API base URL from environment variables
 * Uses NEXT_PUBLIC_API_BASE_URL (new) with fallback to NEXT_PUBLIC_API_URL (legacy)
 */
export function getApiBase(): string {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || 
                  process.env.NEXT_PUBLIC_API_URL?.trim();
  
  if (!apiBase) {
    throw new Error(
      'NEXT_PUBLIC_API_BASE_URL is not set. ' +
      'Set it to your FastAPI backend URL (e.g., http://localhost:8000 for dev or https://your-backend.onrender.com for prod).'
    );
  }
  
  return apiBase;
}

export function isAbsoluteUrl(url?: string | null): boolean {
  if (!url) return false;
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

