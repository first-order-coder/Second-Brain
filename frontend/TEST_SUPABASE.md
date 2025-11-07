# Testing Supabase Features - Step by Step Guide

## Prerequisites Checklist

- [x] Supabase credentials configured in `frontend/env.local`
- [x] Docker services running
- [ ] Database schema created in Supabase
- [ ] Authentication configured in Supabase

---

## Step 1: Create Database Schema (REQUIRED)

1. **Open Supabase Dashboard**
   - Go to https://app.supabase.com
   - Sign in and select your project: `xhqakujyyaczjgljkgwk`

2. **Open SQL Editor**
   - Click on **SQL Editor** in the left sidebar
   - Click **New Query** button

3. **Run the Schema**
   - Open `frontend/db/schema.sql` in your editor
   - Copy the **ENTIRE** contents (all 126 lines)
   - Paste into Supabase SQL Editor
   - Click **Run** button (or press `Ctrl+Enter` / `Cmd+Enter`)

4. **Verify Tables Created**
   - Go to **Table Editor** in Supabase
   - You should see these tables:
     - ✅ `profiles`
     - ✅ `notebooks`
     - ✅ `notes`
     - ✅ `tasks`
     - ✅ `tags`
     - ✅ `note_tags`
   - Each table should have a lock icon 🔒 (indicating RLS is enabled)

---

## Step 2: Configure Authentication

1. **Enable Email Provider**
   - Go to **Authentication → Providers** in Supabase
   - Find **Email** provider
   - Make sure it's **Enabled**
   - Configure if needed (email templates, etc.)

2. **Set Redirect URLs**
   - Go to **Authentication → URL Configuration**
   - **Site URL**: `http://localhost:3000`
   - **Redirect URLs**: Click **Add URL** and add:
     - `http://localhost:3000/auth/callback`
     - `http://localhost:3000/**` (wildcard for all routes)

---

## Step 3: Test Authentication

1. **Visit Sign In Page**
   - Open browser: `http://localhost:3000/auth/signin`
   - You should see a form with email input

2. **Sign In with Magic Link**
   - Enter your email address
   - Click **Send magic link**
   - Check your email inbox
   - Look for email from Supabase (might be in spam)
   - Click the magic link in the email

3. **Verify Sign In**
   - You should be redirected back to `http://localhost:3000`
   - Check browser console (F12) - should see no errors
   - You're now authenticated! 🎉

---

## Step 4: Test Notebooks Feature

1. **Navigate to Notebooks**
   - Visit: `http://localhost:3000/app/notebooks`
   - If not signed in, you'll be redirected to `/auth/signin`
   - If signed in, you'll see the notebooks page

2. **Create a Notebook**
   - You should see a form: "New notebook name..."
   - Enter a name like "My First Notebook"
   - Click **Create**
   - The notebook should appear in the list below

3. **View Notebook in Supabase**
   - Go to Supabase Dashboard → **Table Editor** → `notebooks`
   - You should see your newly created notebook
   - Verify it has your user ID as the `owner`

---

## Step 5: Test Notes Feature

1. **Open a Notebook**
   - Click on the notebook you just created
   - URL should be: `http://localhost:3000/app/notebooks/[notebook-id]`
   - You should see two columns: "Notes" (left) and "Tasks" (right)

2. **Create a Note**
   - In the Notes section, you'll see a form:
     - Title field
     - Content textarea
   - Enter:
     - Title: "My First Note"
     - Content: "This is a test note to verify everything works!"
   - Click **Create Note**
   - The note should appear in the notes list

3. **Verify in Supabase**
   - Go to Supabase → **Table Editor** → `notes`
   - You should see your note
   - Verify `owner` matches your user ID
   - Verify `notebook_id` matches the notebook you created

---

## Step 6: Test Tasks Feature

1. **Create a Task**
   - In the Tasks section (right column), find the task form
   - Enter:
     - Title: "Complete testing"
     - Description: "Finish testing all Supabase features"
     - Due date: Select a date (optional)
   - Click **Create Task**
   - Task should appear in the tasks list

2. **Mark Task as Done**
   - Find your task in the list
   - Click the checkbox next to the task
   - Task should be marked as completed (line-through style)

3. **Delete a Task**
   - Click **Delete** button on any task
   - Confirm deletion
   - Task should be removed

4. **Verify in Supabase**
   - Go to Supabase → **Table Editor** → `tasks`
   - You should see your tasks
   - Check that `is_done` field updates when you check/uncheck

---

## Step 7: Test Row Level Security (RLS)

This verifies users can only see their own data:

1. **Create Test Data**
   - Create a notebook, note, and task (as above)
   - Note the IDs if possible

2. **Sign Out** (if there's a sign out button) or use a different browser/incognito

3. **Sign In with Different Email**
   - Sign in with a completely different email address
   - Navigate to `/app/notebooks`
   - You should see **NO** notebooks (empty list or "No notebooks yet" message)
   - This proves RLS is working! 🎯

4. **Verify in Supabase**
   - In Supabase → **Table Editor** → `notebooks`
   - You can see ALL notebooks (you're using service role)
   - But in the app, users only see their own - that's RLS working!

---

## Troubleshooting

### "Not authenticated" errors
- **Check**: Are you signed in? Visit `/auth/signin` first
- **Check**: Is middleware working? Check browser Network tab for cookie headers
- **Fix**: Clear browser cookies and try signing in again

### "Table doesn't exist" errors
- **Check**: Did you run the schema.sql in Supabase SQL Editor?
- **Fix**: Go back to Step 1 and run the schema

### Magic link not working
- **Check**: Is Email provider enabled in Supabase?
- **Check**: Are redirect URLs configured correctly?
- **Check**: Look in spam folder for the email
- **Fix**: Check Supabase → Authentication → Email Templates

### Can see other users' data
- **Problem**: RLS policies not working
- **Check**: In Supabase → Table Editor, click on a table → "Policies" tab
- **Verify**: Policies should show "Enabled" with green checkmarks
- **Fix**: Re-run the policy creation section from schema.sql

### Environment variables not working
- **Check**: `docker-compose logs frontend` for Supabase errors
- **Check**: Are credentials correct in `frontend/env.local`?
- **Fix**: Restart frontend: `docker-compose restart frontend`

---

## Expected Behavior Summary

✅ **Authentication**
- Can sign in with email magic link
- Redirected back to app after clicking link
- Session persists across page refreshes

✅ **Notebooks**
- Can create notebooks
- See only your own notebooks
- Notebooks appear in Supabase dashboard

✅ **Notes**
- Can create notes within notebooks
- Notes appear immediately after creation
- Can delete notes

✅ **Tasks**
- Can create tasks with title, description, due date
- Can mark tasks as done (checkbox)
- Can delete tasks
- Tasks sorted by due date

✅ **Security (RLS)**
- Each user sees only their own data
- Cannot access other users' notebooks/notes/tasks
- Database enforces security at the row level

---

## Next Steps After Testing

Once everything works:
- ✅ Consider adding a sign-out button
- ✅ Add note editing functionality
- ✅ Add search/filter for notebooks
- ✅ Add tags to notes
- ✅ Add task filtering (completed, due soon, etc.)

---

## Quick Test Checklist

- [ ] Schema run successfully in Supabase
- [ ] Auth redirect URLs configured
- [ ] Can sign in with magic link
- [ ] Can create a notebook
- [ ] Can create a note
- [ ] Can create a task
- [ ] Can mark task as done
- [ ] Can delete note/task
- [ ] Second user sees different data (RLS working)
- [ ] Data appears in Supabase Table Editor

If all checked ✅, **Supabase integration is working perfectly!** 🎉




