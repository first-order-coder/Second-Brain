/**
 * API Client for FastAPI Backend
 * 
 * This module provides a centralized way to make API calls to the FastAPI backend.
 * It uses the NEXT_PUBLIC_API_BASE_URL environment variable to determine the backend URL.
 * 
 * Environment Variables:
 * - Development: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
 * - Production: NEXT_PUBLIC_API_BASE_URL=https://<YOUR_RENDER_BACKEND>.onrender.com
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!API_BASE_URL) {
  console.warn(
    'NEXT_PUBLIC_API_BASE_URL is not set. API calls will fail. ' +
    'Set it in .env.local for development or in Vercel environment variables for production.'
  );
}

/**
 * Get the full URL for an API endpoint
 */
function getApiUrl(path: string): string {
  if (!API_BASE_URL) {
    throw new Error(
      'NEXT_PUBLIC_API_BASE_URL is not set. ' +
      'Set it to your FastAPI backend URL (e.g., http://localhost:8000 for dev or https://your-backend.onrender.com for prod).'
    );
  }

  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  
  // Remove trailing slash from base URL if present
  const baseUrl = API_BASE_URL.replace(/\/$/, '');
  
  return `${baseUrl}${normalizedPath}`;
}

/**
 * Base fetch function for API calls
 * Works in both client components and server components/actions
 */
export async function apiFetch(
  path: string,
  options?: RequestInit
): Promise<Response> {
  const url = getApiUrl(path);
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = `API request failed: ${response.status} ${response.statusText}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      // If response is not JSON, use the status text
    }
    throw new Error(errorMessage);
  }

  return response;
}

/**
 * Fetch JSON from API endpoint
 * Automatically sets Content-Type header and parses JSON response
 */
export async function apiJson<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await apiFetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  return response.json() as Promise<T>;
}

/**
 * POST JSON to API endpoint
 */
export async function apiPost<T>(
  path: string,
  body?: any,
  options?: RequestInit
): Promise<T> {
  return apiJson<T>(path, {
    method: 'POST',
    ...options,
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * GET JSON from API endpoint
 */
export async function apiGet<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  return apiJson<T>(path, {
    method: 'GET',
    ...options,
  });
}

/**
 * PUT JSON to API endpoint
 */
export async function apiPut<T>(
  path: string,
  body?: any,
  options?: RequestInit
): Promise<T> {
  return apiJson<T>(path, {
    method: 'PUT',
    ...options,
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * DELETE request to API endpoint
 */
export async function apiDelete(
  path: string,
  options?: RequestInit
): Promise<Response> {
  return apiFetch(path, {
    method: 'DELETE',
    ...options,
  });
}

/**
 * Upload file to API endpoint (multipart/form-data)
 */
export async function apiUpload<T>(
  path: string,
  formData: FormData,
  options?: RequestInit
): Promise<T> {
  const response = await apiFetch(path, {
    method: 'POST',
    ...options,
    body: formData,
    // Don't set Content-Type header - browser will set it with boundary
  });

  return response.json() as Promise<T>;
}

