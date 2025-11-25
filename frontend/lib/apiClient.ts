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
 * Standard API error structure
 */
export type ApiError = {
  status: number;
  url: string;
  message: string;
  nextSteps?: string[];
  raw?: any;
};

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
    let errorData: any = null;
    let nextSteps: string[] | undefined = undefined;
    
    try {
      errorData = await response.json();
      
      // Handle different error response formats
      if (errorData.detail) {
        // Check if detail is an object with nested detail and next_steps
        if (typeof errorData.detail === 'object' && !Array.isArray(errorData.detail)) {
          if (errorData.detail.detail) {
            errorMessage = errorData.detail.detail;
          } else if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          }
          
          // Extract next_steps if available
          if (errorData.detail.next_steps && Array.isArray(errorData.detail.next_steps)) {
            nextSteps = errorData.detail.next_steps;
          }
        } else if (Array.isArray(errorData.detail)) {
          // Pydantic validation errors - format them nicely
          const validationErrors = errorData.detail.map((err: any) => {
            const field = err.loc?.join('.') || 'unknown';
            return `${field}: ${err.msg}`;
          }).join('; ');
          errorMessage = `Validation error: ${validationErrors}`;
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        }
      } else if (errorData.message) {
        errorMessage = errorData.message;
      }
      
      // Build standard error object
      const apiError: ApiError = {
        status: response.status,
        url: url,
        message: errorMessage,
        nextSteps: nextSteps,
        raw: errorData
      };
      
      // Log concise but helpful error
      console.error('[apiClient] Error', {
        status: apiError.status,
        url: apiError.url,
        message: apiError.message,
        nextSteps: apiError.nextSteps,
        raw: apiError.raw
      });
      
      // Throw error with extended properties
      const err = new Error(errorMessage) as Error & ApiError;
      err.status = apiError.status;
      err.url = apiError.url;
      err.nextSteps = apiError.nextSteps;
      err.raw = apiError.raw;
      throw err;
      
    } catch (parseError) {
      // If response is not JSON, use the status text
      const apiError: ApiError = {
        status: response.status,
        url: url,
        message: errorMessage,
        raw: { statusText: response.statusText }
      };
      
      console.error('[apiClient] Non-JSON error response:', {
        status: apiError.status,
        statusText: response.statusText,
        url: apiError.url,
        parseError: parseError
      });
      
      const err = new Error(errorMessage) as Error & ApiError;
      err.status = apiError.status;
      err.url = apiError.url;
      err.raw = apiError.raw;
      throw err;
    }
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

