# API Client Migration Summary

This document summarizes all changes made to migrate the frontend to use `NEXT_PUBLIC_API_BASE_URL` for backend communication.

## Summary

The frontend now uses a centralized API client that reads the backend URL from `NEXT_PUBLIC_API_BASE_URL`. All client components call the backend directly, and Next.js API routes have been updated for backward compatibility.

## New Files Created

### 1. `frontend/lib/apiClient.ts`
Centralized API client with helper functions:
- `apiFetch()` - Base fetch function
- `apiJson<T>()` - Fetch and parse JSON
- `apiGet<T>()` - GET request
- `apiPost<T>()` - POST request with JSON body
- `apiPut<T>()` - PUT request with JSON body
- `apiDelete()` - DELETE request
- `apiUpload<T>()` - File upload (FormData)

**Key Features:**
- Reads `NEXT_PUBLIC_API_BASE_URL` from environment
- Automatic error handling
- Works in both client and server components
- Type-safe with TypeScript generics

### 2. `frontend/lib/getApiBase.ts`
Helper utility for API routes:
- `getApiBase()` - Gets API base URL with fallback support
- `isAbsoluteUrl()` - Validates URL format
- Supports both `NEXT_PUBLIC_API_BASE_URL` (new) and `NEXT_PUBLIC_API_URL` (legacy)

### 3. `frontend/API_CLIENT_SETUP.md`
Complete setup and usage documentation

## Files Modified

### Client Components

#### `components/PDFUpload.tsx`
**Before:**
```typescript
const response = await fetch('/api/upload/pdf', {
  method: 'POST',
  body: formData,
});
const result = await response.json();
```

**After:**
```typescript
import { apiUpload } from '@/lib/apiClient';

const result = await apiUpload<{ pdf_id: string }>('/upload-pdf', formData);
```

**Changes:**
- Direct backend call using `apiUpload()`
- Removed manual error handling (handled by API client)
- Cleaner, more concise code

#### `components/YTToCards.tsx`
**Before:**
```typescript
const r = await fetch("/api/youtube/flashcards", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
});
const data = await r.json();
```

**After:**
```typescript
import { apiGet, apiPost, apiPut } from "@/lib/apiClient";

const data = await apiPost<YouTubeFlashcardsResponse>("/youtube/flashcards", payload);
```

**Changes:**
- Direct backend calls for YouTube tracks, flashcards, and save
- Type-safe responses
- Simplified error handling

#### `components/ProcessingStatus.tsx`
**Before:**
```typescript
const response = await fetch(`/api/status/${pdfId}`);
const data = await response.json();
```

**After:**
```typescript
import { apiGet } from '@/lib/apiClient';

const data = await apiGet<Status>(`/status/${pdfId}`);
```

#### `app/flashcards/[id]/page.tsx`
**Before:**
```typescript
const response = await fetch(`/api/flashcards/${pdfId}`);
const data = await response.json();
```

**After:**
```typescript
import { apiGet } from '@/lib/apiClient';

const data = await apiGet<FlashcardData>(`/flashcards/${pdfId}`);
```

### Library Files

#### `lib/api.ts`
**Before:**
```typescript
const res = await fetch(`/api/summaries/${sourceId}`, { 
  cache: 'no-store' 
});
return res.json();
```

**After:**
```typescript
import { apiGet, apiPost } from './apiClient';

return await apiGet<Summary>(`/summaries/${sourceId}`);
```

**Changes:**
- All summary and YouTube ingest functions now use API client
- Consistent error handling
- Type-safe responses

### API Route Handlers (Updated for Backward Compatibility)

All API routes in `app/api/` have been updated to use `NEXT_PUBLIC_API_BASE_URL`:

- `app/api/upload/pdf/route.ts`
- `app/api/flashcards/[pdfId]/route.ts`
- `app/api/generate-flashcards/[pdfId]/route.ts`
- `app/api/status/[pdfId]/route.ts`
- `app/api/youtube/tracks/route.ts`
- `app/api/youtube/flashcards/route.ts`
- `app/api/summaries/[sourceId]/route.ts`
- `app/api/summaries/[sourceId]/refresh/route.ts`
- `app/api/ingest/url/route.ts`

**Pattern:**
```typescript
// Before
const API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim();

// After
import { getApiBase, isAbsoluteUrl } from '@/lib/getApiBase';

let API_BASE: string;
try {
  API_BASE = getApiBase();
} catch (error) {
  return NextResponse.json(
    { detail: error instanceof Error ? error.message : "NEXT_PUBLIC_API_BASE_URL is not set." },
    { status: 500 }
  );
}
```

## Environment Variable Configuration

### Development (`frontend/.env.local`)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Production (Vercel)
```
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com
```

**Note:** The old `NEXT_PUBLIC_API_URL` is still supported as a fallback for backward compatibility, but `NEXT_PUBLIC_API_BASE_URL` is preferred.

## What Changed

### ✅ Direct Backend Calls
- Client components now call the FastAPI backend directly
- No longer going through Next.js API routes (except for `/api/save-deck` which uses Supabase)

### ✅ Centralized API Client
- Single source of truth for API calls
- Consistent error handling
- Type-safe with TypeScript

### ✅ Environment Variable
- New variable: `NEXT_PUBLIC_API_BASE_URL`
- Old variable: `NEXT_PUBLIC_API_URL` (still supported as fallback)

### ✅ Updated API Routes
- All Next.js API route handlers updated to use new env var
- Maintained for backward compatibility

## What Stayed the Same

### ✅ API Endpoints
- All backend endpoints remain unchanged
- Request/response formats identical
- No breaking changes to the API

### ✅ `/api/save-deck`
- Still uses Next.js server actions (not FastAPI backend)
- Saves to Supabase, not affected by this migration

### ✅ Types and Interfaces
- All TypeScript types remain the same
- Component props unchanged
- No breaking changes to component APIs

## Migration Checklist

- [x] Create `lib/apiClient.ts` with helper functions
- [x] Create `lib/getApiBase.ts` for API routes
- [x] Update `components/PDFUpload.tsx`
- [x] Update `components/YTToCards.tsx`
- [x] Update `components/ProcessingStatus.tsx`
- [x] Update `app/flashcards/[id]/page.tsx`
- [x] Update `lib/api.ts`
- [x] Update all API route handlers
- [x] Create documentation
- [x] Update `.env.local` example

## Testing

### Local Development
1. Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `.env.local`
2. Start backend: `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`
3. Start frontend: `cd frontend && npm run dev`
4. Test PDF upload, YouTube cards, and flashcard viewing

### Production
1. Set `NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com` in Vercel
2. Deploy frontend
3. Verify all API calls work correctly

## Next Steps

1. **Update `.env.local`** with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
2. **Set Vercel environment variable** for production
3. **Test thoroughly** in both dev and prod environments
4. **Remove old `NEXT_PUBLIC_API_URL`** once migration is confirmed working (optional)

## Files Summary

**Created:**
- `frontend/lib/apiClient.ts` (150 lines)
- `frontend/lib/getApiBase.ts` (30 lines)
- `frontend/API_CLIENT_SETUP.md` (documentation)
- `frontend/API_CLIENT_MIGRATION_SUMMARY.md` (this file)

**Modified:**
- 4 client components
- 1 library file (`lib/api.ts`)
- 9 API route handlers
- `.env.local` (example updated)

**Total Changes:**
- ~500 lines modified
- ~200 lines added
- No breaking changes
- Fully backward compatible

