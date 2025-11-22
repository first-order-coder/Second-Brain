# Render Deployment Guide

This document outlines the changes made to prepare the FastAPI backend for deployment on Render as a Web Service.

## Summary of Changes

### 1. Entry Point & Startup
- **File**: `backend/main.py`
- **Entry Point**: `backend/main.py` with `app = FastAPI()`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- The app is already properly structured with `app` exported at the root of `backend/`

### 2. Database Configuration
**Changed Files**:
- `backend/main.py`
- `backend/services/summary_builder.py`
- `backend/worker_tasks.py`

**Changes**:
- Replaced hardcoded `sqlite:///pdf_flashcards.db` with `DATABASE_URL` environment variable
- Added fallback to SQLite for local development: `os.getenv("DATABASE_URL", "sqlite:///pdf_flashcards.db")`
- Updated SQLAlchemy engine initialization to use `DATABASE_URL` with `pool_pre_ping=True`
- Modified database health checks to work with both SQLite and Postgres
- Updated `init_db()` to only initialize SQLite-specific tables when using SQLite

**Environment Variable**:
- `DATABASE_URL`: Postgres connection string from Render (e.g., `postgresql://user:pass@host:port/db`)

### 3. CORS Configuration
**Changed File**: `backend/main.py`

**Changes**:
- Replaced hardcoded `allow_origins=["http://localhost:3000"]` with environment variable
- Added `CORS_ORIGINS` environment variable support (comma-separated list)
- Defaults to `http://localhost:3000` for local development
- Supports multiple origins: `http://localhost:3000,https://your-app.vercel.app`

**Environment Variable**:
- `CORS_ORIGINS`: Comma-separated list of allowed origins

### 4. Health Check Endpoint
**Changed File**: `backend/main.py`

**Changes**:
- Added simple `/health` endpoint for Render healthchecks
- Returns `{"status": "ok", "database": "sqlite"|"postgres"}`
- Checks database connectivity (SQLite or Postgres)
- Returns 500 on error
- Existing `/healthz` and `/readyz` endpoints remain unchanged

### 5. Environment Variables
**Changed File**: `backend/env.example`

**Added/Updated Variables**:
- `DATABASE_URL`: Database connection string
- `CORS_ORIGINS`: Comma-separated allowed origins
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `POSTGRES_URL`: For Supabase integration
- All existing variables preserved with clear documentation

### 6. Requirements.txt
**File**: `backend/requirements.txt`
- Already complete with all necessary dependencies
- Includes: `fastapi`, `uvicorn[standard]`, `psycopg2-binary`, `sqlalchemy`, etc.
- No changes needed

### 7. Redis Configuration
**Changed File**: `backend/main.py`
- Updated Redis connection in `/readyz` endpoint to use `REDIS_URL` environment variable
- Uses `redis.from_url()` instead of hardcoded localhost

## Render Deployment Instructions

### Step 1: Create a New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your repository
4. Select the repository and branch

### Step 2: Configure Build & Start Commands

**Root Directory**: `backend`

**Build Command**:
```bash
pip install -r requirements.txt
```

**Start Command**:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Note**: Render automatically sets the `$PORT` environment variable. The `--host 0.0.0.0` is required to accept connections from outside the container.

### Step 3: Set Environment Variables

In Render's Environment tab, set the following variables:

#### Required Variables
```
OPENAI_API_KEY=sk-...your-key-here
DATABASE_URL=postgresql://user:password@host:port/database
CORS_ORIGINS=http://localhost:3000,https://YOUR_VERCEL_PROJECT.vercel.app
```

**Important**: Replace `YOUR_VERCEL_PROJECT` with your actual Vercel project URL.

#### Optional Variables (for Supabase integration)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
POSTGRES_URL=postgresql://user:password@host:port/database
```

#### Optional Feature Flags
```
FEATURE_SUMMARY_CITATIONS=true
FEATURE_YOUTUBE_INGEST=true
USE_CELERY=false
SUMMARY_MODEL=gpt-4o-mini
```

#### Optional Redis (if using Celery)
```
REDIS_URL=redis://host:port/db
```

### Step 4: Database Setup

#### Option A: Use Render's Postgres Database
1. Create a new Postgres database in Render
2. Copy the Internal Database URL
3. Set `DATABASE_URL` to this URL
4. Run migrations if needed (the app will create tables on startup via SQLAlchemy)

#### Option B: Use Supabase
1. Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `POSTGRES_URL`
2. The app will use dual-write to both SQLite (fallback) and Supabase

### Step 5: Health Check Configuration

In Render's settings, set:
- **Health Check Path**: `/health`
- Render will ping this endpoint to verify the service is running

### Step 6: Deploy

1. Click "Create Web Service"
2. Render will build and deploy your service
3. Monitor the logs for any issues
4. Once deployed, your API will be available at `https://your-service.onrender.com`

## Verification

After deployment, verify:

1. **Health Check**: `curl https://your-service.onrender.com/health`
   - Should return: `{"status":"ok","database":"postgres"}`

2. **Root Endpoint**: `curl https://your-service.onrender.com/`
   - Should return: `{"message":"PDF to Flashcards API is running"}`

3. **CORS**: Test from your frontend to ensure CORS is working
   - Update your frontend's API URL to point to the Render service

## File Changes Summary

### Modified Files
1. `backend/main.py`
   - Added `DATABASE_URL` environment variable support
   - Updated CORS to use `CORS_ORIGINS` environment variable
   - Added `/health` endpoint
   - Updated database initialization and health checks
   - Fixed Redis connection to use `REDIS_URL`

2. `backend/services/summary_builder.py`
   - Added `DATABASE_URL` environment variable support
   - Updated database connection to use SQLAlchemy with `DATABASE_URL`
   - Replaced direct SQLite connections with SQLAlchemy sessions

3. `backend/worker_tasks.py`
   - Added `DATABASE_URL` environment variable support
   - Updated database connection to use SQLAlchemy

4. `backend/env.example`
   - Added comprehensive documentation
   - Added `DATABASE_URL` and `CORS_ORIGINS`
   - Organized variables into sections
   - Added clear placeholders for Render deployment

### Unchanged Files (No Breaking Changes)
- All API endpoints remain the same
- All request/response schemas unchanged
- Frontend integration remains compatible
- `backend/requirements.txt` - already complete
- `backend/repo/dual_repo.py` - already handles both SQLite and Postgres

## Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` is set correctly
- Check that the Postgres database is accessible from Render
- Ensure `pool_pre_ping=True` is set (already configured)

### CORS Issues
- Verify `CORS_ORIGINS` includes your frontend URL
- Check that URLs don't have trailing slashes
- Ensure `allow_credentials=True` is set (already configured)

### Port Issues
- Render sets `$PORT` automatically - don't hardcode it
- The start command uses `--port $PORT` to respect Render's port

### Health Check Failing
- Check logs for database connection errors
- Verify `DATABASE_URL` is correct
- Ensure Postgres is accessible from Render's network

## Notes

- The app maintains backward compatibility with SQLite for local development
- All existing endpoints and functionality remain unchanged
- The dual-repo system continues to work with both SQLite and Supabase
- Feature flags allow you to enable/disable features via environment variables
- Celery/Redis are optional - set `USE_CELERY=false` if not using background tasks


