'use client';

import { createClient } from '@/lib/supabase/client';

export default function AuthPage() {
  const supabase = createClient();

  const onGoogle = async () => {
    const base = process.env.NEXT_PUBLIC_APP_URL || window.location.origin;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${base}/auth/callback` },
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
        className="w-full rounded-md bg-black py-2 text-sm text-white"
      >
        Continue with Google
      </button>
    </div>
  );
}
