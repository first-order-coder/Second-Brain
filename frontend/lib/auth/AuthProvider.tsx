"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import type { User, Session } from "@supabase/supabase-js";

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  accessToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const supabase = createClient();

  // Initialize session on mount
  useEffect(() => {
    const initSession = async () => {
      try {
        const { data: { session: initialSession } } = await supabase.auth.getSession();
        setSession(initialSession);
        setUser(initialSession?.user ?? null);
      } catch (error) {
        console.error("[AuthProvider] Error getting initial session:", error);
      } finally {
        setIsLoading(false);
      }
    };

    initSession();

    // Subscribe to auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, newSession) => {
        console.log("[AuthProvider] Auth state changed:", event);
        setSession(newSession);
        setUser(newSession?.user ?? null);
        setIsLoading(false);
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const signOut = useCallback(async () => {
    try {
      await supabase.auth.signOut();
      setSession(null);
      setUser(null);
    } catch (error) {
      console.error("[AuthProvider] Sign out error:", error);
    }
  }, [supabase]);

  const refreshSession = useCallback(async () => {
    try {
      const { data: { session: refreshedSession } } = await supabase.auth.refreshSession();
      setSession(refreshedSession);
      setUser(refreshedSession?.user ?? null);
    } catch (error) {
      console.error("[AuthProvider] Refresh session error:", error);
    }
  }, [supabase]);

  const value: AuthContextValue = {
    user,
    session,
    accessToken: session?.access_token ?? null,
    isLoading,
    isAuthenticated: !!session && !!user,
    signOut,
    refreshSession,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

/**
 * Hook to get the access token for API calls.
 * Returns null if not authenticated.
 */
export function useAccessToken(): string | null {
  const { accessToken } = useAuth();
  return accessToken;
}

/**
 * Hook to require authentication.
 * Throws an error if not authenticated (use with error boundary or check isAuthenticated first).
 */
export function useRequireAuth() {
  const { isAuthenticated, isLoading, user, accessToken } = useAuth();
  
  if (isLoading) {
    return { isLoading: true, user: null, accessToken: null };
  }
  
  if (!isAuthenticated) {
    return { isLoading: false, user: null, accessToken: null, requiresLogin: true };
  }
  
  return { isLoading: false, user, accessToken, requiresLogin: false };
}

