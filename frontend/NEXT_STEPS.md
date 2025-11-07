# Next Steps After Setting Up Supabase

## ✅ Step 1: Update Environment Variables (DONE)
Your `frontend/env.local` is configured with Supabase credentials.

⚠️ **Important Note**: Make sure your `SUPABASE_SERVICE_ROLE_KEY` is the actual service role key (not the anon key). 
- Go to Supabase Dashboard → Settings → API
- Look for "service_role" key (different from "anon public" key)
- The service role key has `"role":"service_role"` in the JWT, not `"role":"anon"`

## 📋 Step 2: Create Database Schema

1. **Open Supabase SQL Editor**
   - Go to https://app.supabase.com
   - Select your project: `xhqakujyyaczjgljkgwk`
   - Click on **SQL Editor** in the left sidebar
   - Click **New Query**

2. **Run the Schema**
   - Copy the entire contents of `frontend/db/schema.sql`
   - Paste into the SQL Editor
   - Click **Run** (or press Ctrl+Enter)
   - Wait for success message

3. **Verify Tables Created**
   - Go to **Table Editor** in Supabase
   - You should see these tables:
     - `profiles`
     - `notebooks`
     - `notes`
     - `tasks`
     - `tags`
     - `note_tags`

## 🔐 Step 3: Configure Authentication

1. **Enable Email Provider**
   - Go to **Authentication → Providers** in Supabase
   - Make sure **Email** is enabled
   - Configure magic link settings

2. **Set Redirect URLs**
   - Go to **Authentication → URL Configuration**
   - **Site URL**: `http://localhost:3000`
   - **Redirect URLs**: Add:
     - `http://localhost:3000/auth/callback`
     - `http://localhost:3000/**`

## 🚀 Step 4: Start the Frontend Server

```bash
cd frontend
npm run dev
```

## 🧪 Step 5: Test Everything

1. **Test Authentication**
   - Visit: `http://localhost:3000/auth/signin`
   - Enter your email
   - Check your email for the magic link
   - Click the link to sign in
   - You should be redirected back to the app

2. **Test Notebooks Feature**
   - Visit: `http://localhost:3000/app/notebooks`
   - Create a new notebook
   - Click on a notebook to open it
   - Create notes and tasks
   - Verify everything works!

3. **Check Supabase Dashboard**
   - Go to **Table Editor** → `notebooks`
   - You should see your created notebooks
   - Check `notes` and `tasks` tables too

## 🔧 Troubleshooting

### "Not authenticated" errors
- Make sure you're signed in
- Check browser console for errors
- Verify middleware is working (check Network tab for cookies)

### Database errors
- Verify schema was run successfully
- Check that RLS is enabled on all tables
- Ensure policies are created (check in Supabase dashboard)

### Magic link not working
- Check email spam folder
- Verify redirect URLs are configured
- Check Supabase logs for errors

### Service role key issues
- The service role key should be different from anon key
- Get the correct one from Supabase Dashboard → Settings → API
- Look for the key that says "service_role" (not "anon")

## ✨ Success Indicators

✅ You can sign in with magic link
✅ You can create notebooks
✅ You can create notes and tasks
✅ Data appears in Supabase dashboard
✅ Each user only sees their own data (RLS working)




