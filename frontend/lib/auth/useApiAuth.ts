"use client";

import { useEffect } from "react";
import { useAuth } from "./AuthProvider";
import { setApiAccessToken } from "@/lib/apiClient";

/**
 * Hook to sync auth state with apiClient.
 * Must be used within AuthProvider.
 * 
 * This hook automatically updates the API client's access token
 * whenever the auth session changes.
 */
export function useApiAuth(): void {
  const { accessToken } = useAuth();
  
  useEffect(() => {
    // Update apiClient token whenever it changes
    setApiAccessToken(accessToken);
    
    // Debug log (remove in production)
    if (process.env.NODE_ENV === 'development') {
      console.log('[useApiAuth] Token updated:', accessToken ? 'present' : 'null');
    }
  }, [accessToken]);
}

