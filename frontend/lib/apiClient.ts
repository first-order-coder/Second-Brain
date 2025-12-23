/**
 * API Client for FastAPI Backend
 * 
 * This module provides a centralized way to make API calls to the FastAPI backend.
 * It uses the NEXT_PUBLIC_API_BASE_URL environment variable to determine the backend URL.
 * 
 * SECURITY: Automatically attaches Authorization header when access token is available.
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

// Token storage - will be set by useApiAuth hook
let _accessToken: string | null = null;

/**
 * Set the access token for all API calls.
 * Called by useApiAuth hook when auth state changes.
 */
export function setApiAccessToken(token: string | null): void {
  _accessToken = token;
}

/**
 * Get the current access token (for debugging/testing).
 */
export function getApiAccessToken(): string | null {
  return _accessToken;
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
  errorCode?: string;
  nextSteps?: string[];
  raw?: any;
};

/**
 * Error class for authentication required errors
 */
export class AuthRequiredError extends Error {
  constructor(message: string = "Authentication required. Please sign in.") {
    super(message);
    this.name = "AuthRequiredError";
  }
}

/**
 * Get authentication headers.
 * Returns Authorization header if token is available.
 */
function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {};
  if (_accessToken) {
    headers['Authorization'] = `Bearer ${_accessToken}`;
  }
  return headers;
}

/**
 * Map HTTP status codes to user-friendly messages
 */
function getStatusMessage(status: number, errorCode?: string): string {
  switch (status) {
    case 401:
      return "Please sign in to continue.";
    case 403:
      return "You don't have permission to access this resource.";
    case 429:
      if (errorCode === "QUOTA_EXCEEDED") {
        return "You've reached your usage limit. Please try again later.";
      }
      return "Too many requests. Please slow down and try again.";
    case 413:
      return "File is too large. Please use a smaller file.";
    case 422:
      return "Invalid input. Please check your data and try again.";
    case 500:
      return "Server error. Please try again later.";
    case 502:
    case 503:
    case 504:
      return "Service temporarily unavailable. Please try again.";
    default:
      return `Request failed (${status})`;
  }
}

/**
 * Base fetch function for API calls
 * Works in both client components and server components/actions
 */
export async function apiFetch(
  path: string,
  options?: RequestInit & { requireAuth?: boolean }
): Promise<Response> {
  const { requireAuth = false, ...fetchOptions } = options || {};
  
  // Check if auth is required but token is missing
  if (requireAuth && !_accessToken) {
    throw new AuthRequiredError();
  }
  
  const url = getApiUrl(path);
  
  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      ...getAuthHeaders(),
      ...fetchOptions?.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = `API request failed: ${response.status} ${response.statusText}`;
    let errorData: any = null;
    let errorCode: string | undefined = undefined;
    let nextSteps: string[] | undefined = undefined;
    
    try {
      errorData = await response.json();
      
      // Extract error_code if present
      if (errorData.error_code) {
        errorCode = errorData.error_code;
      } else if (errorData.detail?.error_code) {
        errorCode = errorData.detail.error_code;
      }
      
      // Handle different error response formats
      if (errorData.detail) {
        // Check if detail is an object with nested detail and next_steps
        if (typeof errorData.detail === 'object' && !Array.isArray(errorData.detail)) {
          if (errorData.detail.message) {
            errorMessage = errorData.detail.message;
          } else if (errorData.detail.detail) {
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
      
      // Use user-friendly message for known status codes
      const userFriendlyMessage = getStatusMessage(response.status, errorCode);
      if (response.status === 401 || response.status === 403 || response.status === 429) {
        errorMessage = userFriendlyMessage;
      }
      
      // Build standard error object
      const apiError: ApiError = {
        status: response.status,
        url: url,
        message: errorMessage,
        errorCode: errorCode,
        nextSteps: nextSteps,
        raw: errorData
      };
      
      // Log concise but helpful error
      console.error('[apiClient] Error', {
        status: apiError.status,
        url: apiError.url,
        errorCode: apiError.errorCode,
        message: apiError.message,
      });
      
      // Throw error with extended properties
      const err = new Error(errorMessage) as Error & ApiError;
      err.status = apiError.status;
      err.url = apiError.url;
      err.errorCode = apiError.errorCode;
      err.nextSteps = apiError.nextSteps;
      err.raw = apiError.raw;
      throw err;
      
    } catch (parseError) {
      // If we already threw an error with status, re-throw it
      if (parseError instanceof Error && 'status' in parseError) {
        throw parseError;
      }
      
      // If response is not JSON, use user-friendly status message
      const userFriendlyMessage = getStatusMessage(response.status);
      const apiError: ApiError = {
        status: response.status,
        url: url,
        message: userFriendlyMessage,
        raw: { statusText: response.statusText }
      };
      
      console.error('[apiClient] Non-JSON error response:', {
        status: apiError.status,
        statusText: response.statusText,
        url: apiError.url,
      });
      
      const err = new Error(userFriendlyMessage) as Error & ApiError;
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
  options?: RequestInit & { requireAuth?: boolean }
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
  options?: RequestInit & { requireAuth?: boolean }
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
  options?: RequestInit & { requireAuth?: boolean }
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
  options?: RequestInit & { requireAuth?: boolean }
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
  options?: RequestInit & { requireAuth?: boolean }
): Promise<Response> {
  return apiFetch(path, {
    method: 'DELETE',
    ...options,
  });
}

/**
 * Upload file to API endpoint (multipart/form-data)
 * IMPORTANT: Do NOT set Content-Type header - browser will set it with boundary
 */
export async function apiUpload<T>(
  path: string,
  formData: FormData,
  options?: RequestInit & { requireAuth?: boolean }
): Promise<T> {
  const { headers: customHeaders, ...restOptions } = options || {};
  
  // Extract only non-Content-Type headers from customHeaders
  const safeHeaders: HeadersInit = {};
  if (customHeaders) {
    const headerEntries = customHeaders instanceof Headers 
      ? Array.from(customHeaders.entries())
      : Object.entries(customHeaders as Record<string, string>);
    
    for (const [key, value] of headerEntries) {
      // Skip Content-Type - let browser set it with boundary
      if (key.toLowerCase() !== 'content-type') {
        safeHeaders[key] = value;
      }
    }
  }
  
  const response = await apiFetch(path, {
    method: 'POST',
    ...restOptions,
    headers: safeHeaders,
    body: formData,
    // Don't set Content-Type header - browser will set it with boundary
  });

  return response.json() as Promise<T>;
}
