# Debug Guide: Deck Titles & Timezone Issues

## Where the Issues Are Most Likely Coming From

### 🔴 **ISSUE 1: Deck Titles Showing UUIDs**

**Most Likely Problem Points (in order):**

1. **SaveOnLoad Overwriting Good Titles** (90% likely)
   - **Location**: `frontend/app/flashcards/[id]/page.tsx` lines 155-177
   - **Problem**: When you navigate to flashcard page, if URL params are missing, `SaveOnLoad` runs with `title=null`
   - **Check**: Open browser console, look for `[SaveOnLoad]` logs - is it sending `title: null`?
   - **Fix**: Don't call SaveOnLoad if title is null, OR make SaveOnLoad skip saving if title is null

2. **Initial Save Not Happening** (5% likely)
   - **Location**: `frontend/app/page.tsx` line 13-37 (`saveDeckSilently`)
   - **Problem**: The initial save might be failing silently
   - **Check**: Browser console for `[Home] save-deck succeeded` - is it logging?
   - **Check**: Server logs for `[api/save-deck] Received:` - is title being received?

3. **Query Not Finding Decks** (5% likely)
   - **Location**: `frontend/app/saved/page.tsx` lines 36-59
   - **Problem**: The manual join might not be finding matching decks
   - **Check**: Browser console for `[saved] Raw data from Supabase:` - what does it show?
   - **Check**: Is `decksMap` finding the deck_ids?

### 🔴 **ISSUE 2: Timezone 2 Hours Behind**

**Most Likely Problem Points:**

1. **Timezone Fix Not Applied** (80% likely)
   - **Location**: `frontend/components/decks/SavedDecksList.tsx` lines 62-70
   - **Problem**: The timezone fix might not be working or browser is caching old code
   - **Check**: Is the code actually using `Intl.DateTimeFormat().resolvedOptions().timeZone`?
   - **Fix**: Hard refresh browser (Ctrl+Shift+R) to clear cache

2. **Date Stored in Wrong Timezone** (20% likely)
   - **Location**: Database `created_at` field
   - **Problem**: If dates are stored in UTC but displayed without conversion
   - **Check**: What timezone is your server/database in?

## How to Debug

### Step 1: Check Browser Console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Upload a PDF
4. Look for these logs:
   - `[Home] save-deck succeeded` - Does it show the title?
   - `[api/save-deck] Received:` - What title is received?
   - `[SaveOnLoad]` - Is it sending null title?
   - `[saved] Raw data from Supabase:` - What data structure is returned?
   - `[SavedDecksList] Deck structure:` - What does each deck look like?

### Step 2: Check Server Logs
1. Check Docker logs: `docker-compose logs frontend | grep save-deck`
2. Look for:
   - `[api/save-deck] Received:` - Is title being received?
   - `[saveDeck] Title decision:` - What title decision is made?
   - `[saveDeck] Failed to upsert` - Any errors?

### Step 3: Check Database Directly
1. Connect to Supabase dashboard
2. Check `decks` table - Do rows have proper `title` values?
3. Check `user_decks` table - Are deck_ids correct?

### Step 4: Test the Flow
1. Upload a PDF named "Test_Document.pdf"
2. Immediately check browser console - should see `[Home] save-deck succeeded` with title "Test_Document"
3. Navigate to `/saved` page
4. Check console - should see `[saved] Raw data` with titles
5. Check if title displays correctly

## Quick Fixes to Try

### Fix 1: Prevent SaveOnLoad from Overwriting
In `frontend/app/flashcards/[id]/page.tsx`, change line 172 to:
```tsx
{deckTitle && (
  <SaveOnLoad 
    deckId={pdfId} 
    title={deckTitle}
    sourceType={sourceType}
    sourceLabel={deckTitle}
  />
)}
```

### Fix 2: Make SaveOnLoad Skip if Title is Null
In `frontend/app/flashcards/[id]/SaveOnLoad.tsx`, add check:
```tsx
if (!deckId || done || !title) return null; // Skip if no title
```

### Fix 3: Force Timezone Display
In `frontend/components/decks/SavedDecksList.tsx`, ensure timezone is explicitly set:
```tsx
const savedDate = new Date(deck.created_at);
const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
const localTimeString = savedDate.toLocaleString('en-US', {
  timeZone: timezone,
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: true
});
```

