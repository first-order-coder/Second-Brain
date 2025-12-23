"use client";

import { useApiAuth } from "@/lib/auth";

/**
 * Component that syncs auth state with apiClient.
 * Place this inside AuthProvider to enable automatic token management.
 */
export function AuthSync({ children }: { children: React.ReactNode }) {
  useApiAuth();
  return <>{children}</>;
}

