# Syncing Supabase Environment Variables

Since you already have Supabase configured for your backend, you can use the **same Supabase project** for the frontend authentication and notes/tasks feature.

## Steps to Sync Your Environment Variables

### Backend Supabase Variables (already configured)
Your backend uses:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `POSTGRES_URL`

### Frontend Supabase Variables (need to be set)
Your frontend needs:
- `NEXT_PUBLIC_SUPABASE_URL` - Same as backend's `SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Get this from Supabase Dashboard
- `SUPABASE_SERVICE_ROLE_KEY` - Same as backend's (for server actions)

## Quick Setup

1. **Get your Supabase credentials** (if you don't have them written down):
   - Go to your Supabase Dashboard: https://app.supabase.com
   - Select your project
   - Go to **Settings → API**
   - Copy:
     - **Project URL** → Use for `NEXT_PUBLIC_SUPABASE_URL`
     - **Anon public key** → Use for `NEXT_PUBLIC_SUPABASE_ANON_KEY`
     - **Service role key** → Use for `SUPABASE_SERVICE_ROLE_KEY` (same as backend)

2. **Update `frontend/env.local`**:
   ```env
   NEXT_PUBLIC_API_URL=http://backend:8000
   ENABLE_DEBUG_ENDPOINTS=false
   NEXT_PUBLIC_FEATURE_SUMMARY_CITATIONS=true

   # Supabase Configuration (use same project as backend)
   NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

## Important Notes

- ✅ **Same Supabase Project**: You can use the same Supabase project for both backend (PDF/flashcards data) and frontend (auth + notes/tasks)
- ✅ **Anon Key**: The `NEXT_PUBLIC_SUPABASE_ANON_KEY` is safe to expose in the browser - it's restricted by RLS policies
- ⚠️ **Service Role Key**: Keep `SUPABASE_SERVICE_ROLE_KEY` server-side only - it bypasses RLS
- 📝 **Different Tables**: Your backend uses `pdfs` and `flashcards` tables, while the new frontend uses `notebooks`, `notes`, `tasks` tables (both can coexist)

## After Updating env.local

1. Restart your frontend dev server:
   ```bash
   cd frontend
   npm run dev
   ```

2. Run the database schema (if not already done):
   - Go to Supabase SQL Editor
   - Copy contents from `frontend/db/schema.sql`
   - Execute it to create the notes/tasks tables

3. Test authentication:
   - Visit `http://localhost:3000/auth/signin`
   - Sign in with magic link
   - Visit `http://localhost:3000/app/notebooks`

## Troubleshooting

If you get "Not authenticated" errors:
- Verify `NEXT_PUBLIC_SUPABASE_URL` matches your backend `SUPABASE_URL`
- Check that the Anon key is correct (different from service role key)
- Ensure middleware is working (check browser console for cookie errors)




