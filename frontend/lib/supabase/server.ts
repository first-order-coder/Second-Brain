import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

export const createClient = () => {
  const cookieStore = cookies();
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Supabase environment variables are not configured. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY."
    );
  }

  return createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      get(name: string) {
        return cookieStore.get(name)?.value;
      },
      set(name: string, value: string, options: any) {
        try {
          const cookieOptions = options ?? {};
          cookieStore.set({ name, value, ...cookieOptions });
        } catch {
          // In React Server Components cookies() is read-only; ignore writes.
        }
      },
      remove(name: string, options: any) {
        try {
          const cookieOptions = options ?? {};
          cookieStore.set({ name, value: "", ...cookieOptions });
        } catch {
          // Same as above – swallow write attempts in RSC contexts.
        }
      },
    },
  });
};
