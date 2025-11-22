# Render Deployment - Changes Summary

This document shows the specific code changes made to prepare the backend for Render deployment.

## File Changes Overview

### Modified Files
1. `backend/main.py` - Main entry point
2. `backend/services/summary_builder.py` - Summary service
3. `backend/worker_tasks.py` - Celery worker tasks
4. `backend/env.example` - Environment variables template

### Unchanged Files (No Breaking Changes)
- All API endpoints remain the same
- All request/response schemas unchanged
- `backend/requirements.txt` - Already complete
- All route files remain unchanged

---

## 1. backend/main.py

### Change 1: Database URL Configuration

**Before:**
```python
# SQLAlchemy database setup
engine = create_engine('sqlite:///pdf_flashcards.db')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**After:**
```python
# Database configuration - use environment variable or fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pdf_flashcards.db")
# For Render/Postgres, DATABASE_URL will be provided. For local dev, use SQLite.

# SQLAlchemy database setup
# Use DATABASE_URL from environment, fallback to SQLite for local development
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Change 2: CORS Configuration

**Before:**
```python
# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**After:**
```python
# CORS middleware for frontend communication
# Get allowed origins from environment variable, with fallback to localhost
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Change 3: Database Initialization

**Before:**
```python
# Database initialization
def init_db():
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    # ... create tables ...
    conn.commit()
    conn.close()
```

**After:**
```python
# Database initialization
def init_db():
    """Initialize database tables. Works with both SQLite and Postgres."""
    # Only initialize SQLite-specific tables if using SQLite
    if DATABASE_URL.startswith("sqlite"):
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        # ... create tables ...
        conn.commit()
        conn.close()
    # For Postgres, tables are managed via migrations or Supabase schema
```

### Change 4: Added /health Endpoint

**Added:**
```python
@app.get("/health")
def health():
    """Simple health check endpoint for Render"""
    try:
        # Check database connectivity
        if DATABASE_URL.startswith("sqlite"):
            conn = sqlite3.connect("pdf_flashcards.db")
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            db_type = "sqlite"
        else:
            # For Postgres, use SQLAlchemy engine
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_type = "postgres"
        
        return {"status": "ok", "database": db_type}
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
```

### Change 5: Updated Health Check Endpoints

**Before (in /healthz and /readyz):**
```python
# Check SQLite connectivity
conn = sqlite3.connect("pdf_flashcards.db")
cursor = conn.cursor()
cursor.execute("SELECT 1")
conn.close()
status["sqlite"] = "healthy"
```

**After:**
```python
# Check primary database
try:
    if DATABASE_URL.startswith("sqlite"):
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        status["database"] = "healthy"
    else:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()  # Consume the result
        status["database"] = "healthy"
except Exception as e:
    status["ok"] = False
    status["database"] = f"error: {str(e)}"
```

### Change 6: Updated Redis Connection

**Before:**
```python
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()
```

**After:**
```python
import redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url)
r.ping()
```

### Change 7: Updated PDF Status Check

**Before:**
```python
# Check if PDF exists
conn = sqlite3.connect("pdf_flashcards.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM pdfs WHERE id = ?", (pdf_id,))
pdf_record = cursor.fetchone()
conn.close()
```

**After:**
```python
# Check if PDF exists using dual-repo
pdf_status = get_pdf_status(pdf_id)
if not pdf_status:
    raise HTTPException(status_code=404, detail="PDF not found")
```

---

## 2. backend/services/summary_builder.py

### Change: Database URL Configuration

**Before:**
```python
# Database setup
engine = create_engine('sqlite:///pdf_flashcards.db')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**After:**
```python
# Database setup - use environment variable or fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pdf_flashcards.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Change: Database Query Method

**Before:**
```python
def get_chunks_for_source(source_id: str) -> List[Dict]:
    """Get chunks for a source"""
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM pdfs WHERE id = ?", (source_id,))
    pdf_record = cursor.fetchone()
    conn.close()
```

**After:**
```python
def get_chunks_for_source(source_id: str) -> List[Dict]:
    """Get chunks for a source"""
    # Use SQLAlchemy session for database-agnostic access
    session = SessionLocal()
    try:
        from sqlalchemy import text
        result = session.execute(text("SELECT filename FROM pdfs WHERE id = :id"), {"id": source_id})
        pdf_record = result.fetchone()
        if not pdf_record:
            raise RuntimeError("No chunks found for this source")
    finally:
        session.close()
```

---

## 3. backend/worker_tasks.py

### Change: Database URL Configuration

**Before:**
```python
# Database setup
engine = create_engine('sqlite:///pdf_flashcards.db')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**After:**
```python
# Database setup - use environment variable or fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pdf_flashcards.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Change: Database Query in Celery Task

**Before:**
```python
# Check if source exists
conn = sqlite3.connect("pdf_flashcards.db")
cursor = conn.cursor()
cursor.execute("SELECT filename FROM pdfs WHERE id = ?", (source_id,))
pdf_record = cursor.fetchone()
```

**After:**
```python
# Check if source exists using SQLAlchemy
session = SessionLocal()
try:
    from sqlalchemy import text
    result = session.execute(text("SELECT filename FROM pdfs WHERE id = :id"), {"id": source_id})
    pdf_record = result.fetchone()
    
    if not pdf_record:
        print(f"PDF not found for source_id: {source_id}")
        return {"error": "PDF not found"}
finally:
    session.close()
```

---

## 4. backend/env.example

### Change: Comprehensive Environment Variables

**Before:** Basic environment variables with minimal documentation

**After:** Comprehensive environment variables organized into sections:
- Required for Render Deployment
- Optional Feature Flags
- YouTube Ingestion Configuration
- Clear placeholders for `YOUR_VERCEL_PROJECT`
- Documentation for each variable

Key additions:
- `DATABASE_URL` - Database connection string
- `CORS_ORIGINS` - Comma-separated allowed origins
- Better organization and documentation

---

## Render Deployment Configuration

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Root Directory
```
backend
```

### Required Environment Variables
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:password@host:port/database
CORS_ORIGINS=http://localhost:3000,https://YOUR_VERCEL_PROJECT.vercel.app
```

### Health Check Path
```
/health
```

---

## Testing the Changes

### Local Testing
1. Set `DATABASE_URL=sqlite:///pdf_flashcards.db` (default)
2. Set `CORS_ORIGINS=http://localhost:3000`
3. Run: `uvicorn main:app --host 0.0.0.0 --port 8000`
4. Test: `curl http://localhost:8000/health`

### Render Testing
1. Deploy to Render with the configuration above
2. Test: `curl https://your-service.onrender.com/health`
3. Should return: `{"status":"ok","database":"postgres"}`

---

## Backward Compatibility

✅ **All existing functionality preserved**
- All API endpoints remain unchanged
- All request/response schemas unchanged
- Frontend integration remains compatible
- Local development still works with SQLite default
- Dual-repo system continues to work
- Feature flags allow gradual migration

✅ **No breaking changes**
- Default behavior is SQLite (local dev)
- Environment variables are optional with sensible defaults
- Existing code paths remain functional

