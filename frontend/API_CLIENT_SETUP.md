# API Client Setup Guide

This document explains how the frontend communicates with the FastAPI backend and how to configure the environment variables.

## Overview

The frontend uses a centralized API client (`lib/apiClient.ts`) to make all calls to the FastAPI backend. This client reads the backend URL from the `NEXT_PUBLIC_API_BASE_URL` environment variable.

## Environment Variable

### `NEXT_PUBLIC_API_BASE_URL`

This environment variable specifies the base URL of your FastAPI backend.

**Development (Local):**
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**Production (Vercel):**
```bash
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com
```

Replace `your-backend` with your actual Render service name.

## Setup Instructions

### Local Development

1. Create or update `frontend/.env.local`:
   ```bash
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

2. Make sure your FastAPI backend is running on `http://localhost:8000`

3. Restart your Next.js dev server:
   ```bash
   npm run dev
   ```

### Production (Vercel)

1. Go to your Vercel project settings
2. Navigate to **Environment Variables**
3. Add a new variable:
   - **Name**: `NEXT_PUBLIC_API_BASE_URL`
   - **Value**: `https://your-backend.onrender.com` (replace with your actual Render URL)
   - **Environment**: Production (and Preview if needed)

4. Redeploy your application

## API Client Usage

The API client provides several helper functions:

### Basic Functions

```typescript
import { apiGet, apiPost, apiPut, apiDelete, apiUpload } from '@/lib/apiClient';

// GET request
const data = await apiGet<ResponseType>('/endpoint');

// POST request with JSON body
const result = await apiPost<ResponseType>('/endpoint', { key: 'value' });

// PUT request with JSON body
const updated = await apiPut<ResponseType>('/endpoint', { key: 'value' });

// DELETE request
await apiDelete('/endpoint');

// File upload (FormData)
const formData = new FormData();
formData.append('file', file);
const uploaded = await apiUpload<ResponseType>('/upload', formData);
```

### Error Handling

The API client automatically throws errors for non-OK responses. Handle them with try/catch:

```typescript
try {
  const data = await apiGet('/endpoint');
  // Use data
} catch (error) {
  if (error instanceof Error) {
    console.error('API error:', error.message);
  }
}
```

## Files Updated

The following files now use the new API client:

### Client Components
- `components/PDFUpload.tsx` - PDF upload and flashcard generation
- `components/YTToCards.tsx` - YouTube flashcard generation
- `components/ProcessingStatus.tsx` - Status polling
- `app/flashcards/[id]/page.tsx` - Flashcard fetching
- `app/page.tsx` - Save deck calls (still uses `/api/save-deck` for Supabase)

### Library Files
- `lib/api.ts` - Summary and YouTube ingest functions

### API Routes (Proxies)
All Next.js API route handlers in `app/api/` have been updated to use `NEXT_PUBLIC_API_BASE_URL`:
- `app/api/upload/pdf/route.ts`
- `app/api/flashcards/[pdfId]/route.ts`
- `app/api/generate-flashcards/[pdfId]/route.ts`
- `app/api/status/[pdfId]/route.ts`
- `app/api/youtube/tracks/route.ts`
- `app/api/youtube/flashcards/route.ts`
- `app/api/summaries/[sourceId]/route.ts`
- `app/api/summaries/[sourceId]/refresh/route.ts`
- `app/api/ingest/url/route.ts`

**Note**: The API routes are kept for backward compatibility, but client components now call the backend directly using the API client.

## Migration Notes

### Backward Compatibility

The API routes still support the old `NEXT_PUBLIC_API_URL` environment variable as a fallback, but `NEXT_PUBLIC_API_BASE_URL` is preferred.

### What Changed

1. **Client components** now call the backend directly instead of going through Next.js API routes
2. **Environment variable** changed from `NEXT_PUBLIC_API_URL` to `NEXT_PUBLIC_API_BASE_URL`
3. **Centralized API client** provides consistent error handling and URL construction

### What Stayed the Same

- All API endpoints remain unchanged
- Request/response formats are identical
- `/api/save-deck` still uses Next.js server actions (not the FastAPI backend)

## Troubleshooting

### "NEXT_PUBLIC_API_BASE_URL is not set" Error

**Solution**: Make sure you've set the environment variable:
- In development: Add it to `frontend/.env.local`
- In production: Add it to Vercel environment variables

### CORS Errors

**Solution**: Make sure your backend CORS configuration includes your frontend URL:
- Development: `http://localhost:3000`
- Production: `https://your-vercel-app.vercel.app`

Update `CORS_ORIGINS` in your backend environment variables.

### Network Errors

**Solution**: 
1. Verify your backend is running and accessible
2. Check that the URL in `NEXT_PUBLIC_API_BASE_URL` is correct
3. For production, ensure your Render service is deployed and running

## Example Configuration

### `.env.local` (Development)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Vercel Environment Variables (Production)
```
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com
```

## Additional Resources

- Backend deployment guide: `backend/RENDER_DEPLOYMENT.md`
- API client source: `frontend/lib/apiClient.ts`
- Helper utilities: `frontend/lib/getApiBase.ts`

