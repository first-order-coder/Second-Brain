'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { createClient } from '@/lib/supabase/client';

function AuthPageContent() {
  const supabase = createClient();
  const searchParams = useSearchParams();
  
  // Read `next` param to redirect after login
  const nextPath = searchParams.get('next') || '/';

  const onGoogle = async () => {
    const base = process.env.NEXT_PUBLIC_APP_URL || window.location.origin;
    // Pass the `next` param to callback so it redirects to the intended page after login
    const callbackUrl = `${base}/auth/callback?next=${encodeURIComponent(nextPath)}`;
    
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: callbackUrl },
    });
    if (error) alert(error.message);
  };

  return (
    <div className="mx-auto max-w-sm px-4 py-10">
      <h1 className="mb-2 text-xl font-semibold">Welcome</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Sign in to save and access your decks.
      </p>
      <button
        onClick={onGoogle}
        className="w-full rounded-md bg-black py-2 text-sm text-white dark:bg-white dark:text-black hover:opacity-90 transition-opacity"
      >
        Continue with Google
      </button>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="mx-auto max-w-sm px-4 py-10">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-24 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-48 mb-6"></div>
          <div className="h-10 bg-gray-200 rounded w-full"></div>
        </div>
      </div>
    }>
      <AuthPageContent />
    </Suspense>
  );
}
