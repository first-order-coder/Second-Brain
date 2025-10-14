# Troubleshooting Guide

This document provides solutions to common issues when working with the Second Brain application.

## PDF Upload Issues

### "PDF upload returns 415/422"
**Symptoms:** Frontend shows 415 Unsupported Media Type or 422 Unprocessable Entity errors.

**Causes & Solutions:**
- **Content-Type boundary issue**: The Next.js proxy must NOT set `Content-Type` manually. Let fetch handle the multipart boundary.
  ```typescript
  // ❌ Wrong - breaks boundary
  headers: { "Content-Type": "multipart/form-data" }
  
  // ✅ Correct - let fetch set boundary
  // No Content-Type header
  ```
- **Edge runtime issue**: PDF uploads must use Node.js runtime for reliable multipart streaming.
  ```typescript
  // ✅ Required for multipart
  export const runtime = "nodejs";
  ```

### "Network error" during PDF upload
**Symptoms:** Frontend shows "Network error" or "Proxy could not reach" messages.

**Solutions:**
1. **Check NEXT_PUBLIC_API_URL**: Must be set to absolute URL
   - Local dev: `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - Docker: `NEXT_PUBLIC_API_URL=http://backend:8000`
2. **Restart Next.js**: Environment variables are build-time, not runtime
3. **Verify backend binding**: FastAPI must bind to `0.0.0.0:8000`, not `localhost:8000`

### "Empty file on backend"
**Symptoms:** Backend receives empty file or 0-byte uploads.

**Solutions:**
1. **Rebuild FormData in proxy**: Don't read the stream twice
   ```typescript
   const incoming = await req.formData();
   const fd = new FormData();
   // Rebuild to avoid ReadableStream issues
   for (const [key, value] of incoming.entries()) {
     fd.append(key, value);
   }
   ```

## YouTube Flashcards Issues

### "No transcript available" errors
**Symptoms:** YouTube videos fail with "No transcript available" messages.

**Solutions:**
1. **Check available tracks**: Use `/api/youtube/tracks?url=<video>` to see available languages
2. **Enable fallback**: Set `enable_fallback=true` in request
3. **Provide cookies**: Set `use_cookies=true` and configure `YT_COOKIES_PATH`
4. **Adjust language hints**: Try different language codes or enable auto-generated captions

### "Age/consent restricted" errors
**Symptoms:** Videos return 422 with gated=true or consent errors.

**Solutions:**
1. **Use cookies**: Provide `YT_COOKIES_PATH` with valid Netscape cookies.txt
2. **Try different video**: Some videos have stricter access controls
3. **Enable fallback**: Use yt-dlp with `enable_fallback=true`

## Environment Configuration

### NEXT_PUBLIC_API_URL Issues
**Symptoms:** Frontend can't reach backend, shows "not set" errors.

**Solutions:**
1. **Local Development**:
   ```bash
   # frontend/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
2. **Docker Compose**:
   ```yaml
   # docker-compose.yml
   services:
     frontend:
       environment:
         - NEXT_PUBLIC_API_URL=http://backend:8000
   ```
3. **Rebuild containers**: Environment variables are build-time in Next.js

### Backend Connection Issues
**Symptoms:** 502 Bad Gateway, connection refused errors.

**Solutions:**
1. **Check backend binding**: Must bind to `0.0.0.0:8000` in Docker
   ```dockerfile
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```
2. **Verify container networking**: Frontend and backend must be on same Docker network
3. **Check backend logs**: `docker logs 2nd_brain-backend-1`

## DNS Resolution Issues

### "net::ERR_NAME_NOT_RESOLVED" for backend:8000
**Symptoms:** Browser shows DNS resolution errors when trying to access `http://backend:8000/...` URLs.

**Cause:** Browser is trying to call Docker service DNS names directly, which are not resolvable from the client.

**Solutions:**
1. **Use Next.js API proxies**: All browser requests must go through `/api/*` routes
   ```typescript
   // ❌ Wrong - direct backend call from browser
   fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload-pdf`)
   
   // ✅ Correct - use Next.js proxy
   fetch('/api/upload/pdf')
   ```
2. **Check ESLint rules**: Ensure no direct backend calls in client code
3. **Verify proxy routes**: All backend endpoints must have corresponding `/api/*` proxies

### Backend URLs in JSON responses
**Symptoms:** UI renders links that point to `http://backend:8000/...` causing DNS errors.

**Solutions:**
1. **Use URL rewriter**: Process backend responses to convert URLs to proxy paths
   ```typescript
   import { rewriteBackendUrlsToProxy } from '@/lib/rewriteBackendUrls';
   const safeData = rewriteBackendUrlsToProxy(data);
   ```
2. **Check response processing**: Ensure all API responses are processed before rendering

## API Endpoint Issues

### Missing API Routes
**Symptoms:** 404 errors for `/api/*` endpoints.

**Solutions:**
1. **Check file structure**: API routes must be in `app/api/` directory
2. **Verify route.ts files**: Each endpoint needs `route.ts` file
3. **Rebuild frontend**: Changes to API routes require rebuild

### CORS Issues
**Symptoms:** Browser CORS errors when calling backend directly.

**Solutions:**
1. **Use proxy pattern**: Always call `/api/*` routes, not backend directly
2. **Check backend CORS**: Verify CORS middleware is configured
3. **Same-origin requests**: Frontend → Next.js → FastAPI (no CORS needed)

## Dependencies

### Python Multipart Issues
**Symptoms:** 422 errors on file uploads, "multipart not installed" errors.

**Solutions:**
1. **Install python-multipart**: Must be in requirements.txt
   ```txt
   python-multipart>=0.0.6
   ```
2. **Rebuild backend**: `docker compose build backend`

### Missing Dependencies
**Symptoms:** Import errors, missing modules.

**Solutions:**
1. **Check requirements.txt**: All dependencies must be listed
2. **Rebuild containers**: `docker compose build`
3. **Check logs**: Look for specific import errors

## Performance Issues

### Slow PDF Processing
**Symptoms:** PDF uploads take very long or timeout.

**Solutions:**
1. **Check file size**: Limit to 10MB or less
2. **Monitor backend logs**: Look for processing bottlenecks
3. **Check Redis**: Ensure Redis is running for background tasks

### YouTube API Rate Limits
**Symptoms:** YouTube requests fail with rate limit errors.

**Solutions:**
1. **Use cookies**: Authenticated requests have higher limits
2. **Implement backoff**: Add delays between requests
3. **Check quotas**: Monitor YouTube API usage

## Debugging Commands

### Check Container Status
```bash
docker compose ps
docker compose logs frontend
docker compose logs backend
```

### Test Endpoints Directly
```bash
# Test backend directly
curl -F "file=@test.pdf" http://localhost:8000/upload-pdf

# Test frontend proxy
curl -F "file=@test.pdf" http://localhost:3000/api/upload/pdf

# Test YouTube endpoints
curl "http://localhost:3000/api/youtube/tracks?url=https://youtu.be/VIDEO_ID"
```

### Check Environment Variables
```bash
# Check frontend env
curl http://localhost:3000/api/debug/env

# Check backend env (if debug endpoint exists)
curl http://localhost:8000/debug/env
```

## Common Fixes

### Full Reset
If all else fails, try a complete reset:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Clear Uploads
If PDF uploads are stuck:
```bash
docker exec 2nd_brain-backend-1 rm -rf uploads/*
```

### Reset Database
If database is corrupted:
```bash
docker exec 2nd_brain-backend-1 rm -f pdf_flashcards.db
docker compose restart backend
```
