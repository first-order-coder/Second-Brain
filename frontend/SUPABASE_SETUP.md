# Supabase Integration Setup Guide

This guide will help you set up Supabase authentication and the Notes/Tasks feature for your 2nd Brain application.

## Step 1: Create & Configure Your Supabase Project

1. **Create a Supabase Project**
   - Go to [Supabase Dashboard](https://app.supabase.com)
   - Click "New Project"
   - Choose your organization and a region close to your users
   - Set a strong database password (save this securely!)

2. **Get Your Credentials**
   - Go to **Settings → API** in your Supabase project
   - Copy the following:
     - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
     - **Anon public key** → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
     - **Service role key** (server only) → `SUPABASE_SERVICE_ROLE_KEY`

3. **Configure Environment Variables**
   - Update `frontend/env.local` with your actual Supabase credentials:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
   ```

## Step 2: Set Up Database Schema

1. **Open Supabase SQL Editor**
   - In your Supabase dashboard, go to **SQL Editor**
   - Click "New Query"

2. **Run the Schema Script**
   - Copy the contents of `frontend/db/schema.sql`
   - Paste into the SQL Editor
   - Click "Run" to execute

   This will create:
   - `profiles` table (linked to auth.users)
   - `notebooks` table (user's notebooks)
   - `notes` table (notes within notebooks)
   - `tasks` table (tasks within notebooks)
   - `tags` table (optional, for tagging notes)
   - Row Level Security (RLS) policies to ensure users only see their own data

3. **Verify Tables Created**
   - Go to **Table Editor** in Supabase
   - You should see all the tables listed
   - Check that RLS is enabled (lock icon) on each table

## Step 3: Configure Authentication

1. **Enable Email Authentication**
   - Go to **Authentication → Providers** in Supabase
   - Enable **Email** provider
   - Configure magic link settings

2. **Set Redirect URLs**
   - Go to **Authentication → URL Configuration**
   - Set **Site URL** to: `http://localhost:3000` (for development)
   - Add **Redirect URLs**:
     - `http://localhost:3000/auth/callback`
     - `http://localhost:3000/**` (for production, replace with your domain)

## Step 4: Test the Integration

1. **Start Your Development Server**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Test Authentication**
   - Navigate to `http://localhost:3000/auth/signin`
   - Enter your email
   - Check your email for the magic link
   - Click the link to sign in

3. **Test Notes & Tasks**
   - Navigate to `http://localhost:3000/app/notebooks`
   - Create a new notebook
   - Open the notebook and create notes and tasks
   - Verify that data appears in Supabase dashboard

## Files Created

### Supabase Clients
- `frontend/lib/supabase/client.ts` - Browser client
- `frontend/lib/supabase/server.ts` - Server client
- `frontend/lib/supabase/middleware.ts` - Session middleware
- `frontend/middleware.ts` - Next.js middleware

### Authentication
- `frontend/components/auth/MagicLinkForm.tsx` - Sign in form
- `frontend/app/auth/signin/page.tsx` - Sign in page
- `frontend/app/auth/callback/route.ts` - Auth callback handler

### Database Schema
- `frontend/db/schema.sql` - Complete database schema with RLS

### Server Actions (CRUD)
- `frontend/app/actions/create-notebook.ts`
- `frontend/app/actions/create-note.ts`
- `frontend/app/actions/update-note.ts`
- `frontend/app/actions/delete-note.ts`
- `frontend/app/actions/tasks.ts` (create, update, delete tasks)

### UI Components
- `frontend/components/notebooks/NotebookList.tsx`
- `frontend/components/notebooks/NotebookForm.tsx`
- `frontend/components/notebooks/NotebookDetail.tsx`
- `frontend/components/notebooks/NoteForm.tsx`
- `frontend/components/notebooks/NotesList.tsx`
- `frontend/components/notebooks/TaskForm.tsx`
- `frontend/components/notebooks/TasksList.tsx`
- `frontend/components/notebooks/TaskItem.tsx`
- `frontend/components/notebooks/DeleteButton.tsx`

### Pages
- `frontend/app/app/notebooks/page.tsx` - Notebooks list
- `frontend/app/app/notebooks/[id]/page.tsx` - Notebook detail with notes & tasks

## Security Notes

1. **Never expose service role key** - Keep `SUPABASE_SERVICE_ROLE_KEY` server-side only
2. **RLS is enabled** - All tables have Row Level Security policies
3. **User isolation** - Users can only see their own notebooks, notes, and tasks
4. **Middleware** - Session is automatically refreshed via middleware

## Troubleshooting

### "Failed to initialize Supabase engine"
- Check that environment variables are set correctly
- Verify your Supabase project URL and keys are correct
- Restart your development server after updating env vars

### "Not authenticated" errors
- Ensure you're signed in (check `/auth/signin`)
- Verify middleware is working (check browser Network tab for cookies)
- Check Supabase dashboard → Authentication → Users to see if user exists

### RLS Policy Errors
- Verify RLS is enabled on all tables
- Check that policies are created correctly in `schema.sql`
- Ensure `owner` field is populated on inserts

### Magic Link Not Working
- Check email provider is enabled in Supabase
- Verify redirect URLs are configured correctly
- Check spam folder for the magic link email

## Next Steps

- Add user profile editing
- Implement note editing (currently only create/delete)
- Add task due date filtering
- Implement tag system fully
- Add search functionality
- Add sharing/collaboration features




