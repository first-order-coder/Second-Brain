from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
import os
import uuid
import logging
from pathlib import Path
import sqlite3
import json
from models import PDF, Flashcard, Base, Summary, SummarySentence, SummarySentenceCitation
from pdf_processor import extract_text_from_pdf
from flashcard_generator import generate_flashcards
from worker_tasks import build_summary_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create specific loggers
summary_logger = logging.getLogger("summaries")
citations_logger = logging.getLogger("citations")

# Import YouTube ingest routers (feature-flagged)
from routes.ingest import router as ingest_router
from routes.ingest_debug import router as ingest_debug_router

# Import YouTube flashcards router
from routes.youtube_cards import router as youtube_cards_router

app = FastAPI(title="PDF to Flashcards API", version="1.0.0")

# Feature flag for summary citations
FEATURE_SUMMARY_CITATIONS = os.getenv('FEATURE_SUMMARY_CITATIONS', 'true').lower() == 'true'

# Summary configuration
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")
TOP_K = int(os.getenv("SUMMARY_EVIDENCE_TOPK", "6"))
THRESH = float(os.getenv("SUMMARY_SUPPORT_THRESHOLD", "0.74"))
USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"

# SQLAlchemy database setup
engine = create_engine('sqlite:///pdf_flashcards.db')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic schemas for summary feature
class CitationOut(BaseModel):
    chunk_id: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    score: Optional[float] = None
    preview_text: Optional[str] = None

class SentenceOut(BaseModel):
    id: str
    order_index: int
    sentence_text: str
    support_status: Literal["supported", "insufficient"]
    citations: List[CitationOut] = []

class SummaryOut(BaseModel):
    summary_id: str
    source_id: str
    sentences: List[SentenceOut]

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register YouTube ingest routers (feature-flagged)
FEATURE_YOUTUBE_INGEST = os.getenv("FEATURE_YOUTUBE_INGEST", "true").lower() == "true"
ENABLE_DEBUG_ENDPOINTS = os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true"
if FEATURE_YOUTUBE_INGEST:
    app.include_router(ingest_router)
    if ENABLE_DEBUG_ENDPOINTS:
        app.include_router(ingest_debug_router)
        logging.info("YouTube ingest debug endpoints enabled")
    logging.info("YouTube ingest feature enabled")

# Register YouTube flashcards router (always enabled)
app.include_router(youtube_cards_router)
logging.info("YouTube flashcards feature enabled")

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Database initialization
def init_db():
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdfs (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'uploaded'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id TEXT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            card_number INTEGER,
            FOREIGN KEY (pdf_id) REFERENCES pdfs(id)
        )
    """)
    
    conn.commit()
    conn.close()

# -------- YouTube flashcards save endpoint --------
class SaveYouTubeCard(BaseModel):
    front: str
    back: str
    cloze: Optional[str] = None
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    evidence: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None

class SaveYouTubeDeckRequest(BaseModel):
    url: str
    video_id: Optional[str] = None
    title: Optional[str] = None
    lang: Optional[str] = None
    cards: List[SaveYouTubeCard]

@app.post("/youtube/save")
async def save_youtube_deck(payload: SaveYouTubeDeckRequest):
    """Save generated YouTube cards into the existing SQLite-backed deck.

    Creates a new entry in `pdfs` as a logical source and inserts cards into `flashcards`.
    Returns the created `pdf_id` for navigation to the review page.
    """
    try:
        # Allocate a synthetic pdf_id to reuse existing flashcards viewer
        pdf_id = str(uuid.uuid4())

        # Use a descriptive filename-like label for the source row
        label_parts = ["youtube"]
        if payload.video_id:
            label_parts.append(payload.video_id)
        if payload.title:
            label_parts.append(payload.title[:60])
        source_label = " | ".join(label_parts)

        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()

        # Insert source row as completed
        cursor.execute(
            "INSERT INTO pdfs (id, filename, status) VALUES (?, ?, ?)",
            (pdf_id, source_label, "completed"),
        )

        # Insert cards
        for idx, c in enumerate(payload.cards, start=1):
            question = c.front.strip() if c.front else ""
            answer = c.back.strip() if c.back else ""
            cursor.execute(
                "INSERT INTO flashcards (pdf_id, question, answer, card_number) VALUES (?, ?, ?, ?)",
                (pdf_id, question, answer, idx),
            )

        conn.commit()
        conn.close()

        return {"pdf_id": pdf_id, "count": len(payload.cards)}
    except Exception as e:
        logging.exception(f"Failed to save YouTube deck: {e}")
        raise HTTPException(status_code=500, detail=f"Save failed: {str(e)}")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and return its ID"""
    
    print(f"Received upload request: filename={file.filename}, content_type={file.content_type}, size={file.size}")
    
    try:
        # Validate file type (more flexible check)
        if file.content_type not in ["application/pdf", "application/octet-stream"]:
            print(f"Invalid content type: {file.content_type}")
            raise HTTPException(status_code=400, detail=f"Only PDF files are allowed. Received: {file.content_type}")
        
        # Validate file size (10MB limit)
        content = await file.read()
        file_size = len(content)
        # Generate unique ID for the PDF
        pdf_id = str(uuid.uuid4())
        print(f"Generated PDF ID: {pdf_id}")
        
        # Ensure uploads directory exists
        UPLOAD_DIR.mkdir(exist_ok=True)
        
        # Save file to uploads directory
        file_path = UPLOAD_DIR / f"{pdf_id}.pdf"
        print(f"Saving file to: {file_path}")
        
        with open(file_path, "wb") as f:
            f.write(content)

        if file_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 10MB")
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        print(f"File saved successfully: {file_path.exists()}")
        
        # Save to database
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pdfs (id, filename, status) VALUES (?, ?, ?)",
            (pdf_id, file.filename, "uploaded")
        )
        conn.commit()
        conn.close()
        
        print(f"Database record created for PDF ID: {pdf_id}")
        
        return {"pdf_id": pdf_id, "filename": file.filename, "status": "uploaded"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/generate-flashcards/{pdf_id}")
async def generate_flashcards_endpoint(pdf_id: str, background_tasks: BackgroundTasks):
    """Start flashcard generation process"""
    
    # Check if PDF exists
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pdfs WHERE id = ?", (pdf_id,))
    pdf_record = cursor.fetchone()
    conn.close()
    
    if not pdf_record:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Update status to processing
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE pdfs SET status = ? WHERE id = ?", ("processing", pdf_id))
    conn.commit()
    conn.close()
    
    # Start background task
    background_tasks.add_task(process_pdf_and_generate_flashcards, pdf_id)
    
    return {"message": "Flashcard generation started", "pdf_id": pdf_id}

async def process_pdf_and_generate_flashcards(pdf_id: str):
    """Background task to process PDF and generate flashcards"""
    try:
        # Update status to processing
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE pdfs SET status = ? WHERE id = ?", ("processing", pdf_id))
        conn.commit()
        conn.close()
        
        # Extract text from PDF
        file_path = UPLOAD_DIR / f"{pdf_id}.pdf"
        if not file_path.exists():
            raise Exception("PDF file not found")
        
        text_content = extract_text_from_pdf(str(file_path))
        
        if not text_content.strip():
            raise Exception("No text could be extracted from PDF")
        
        # Generate flashcards using OpenAI
        flashcards_data = generate_flashcards(text_content)
        
        # Save flashcards to database
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        
        # Clear any existing flashcards for this PDF
        cursor.execute("DELETE FROM flashcards WHERE pdf_id = ?", (pdf_id,))
        
        # Insert new flashcards
        for i, flashcard in enumerate(flashcards_data):
            cursor.execute(
                "INSERT INTO flashcards (pdf_id, question, answer, card_number) VALUES (?, ?, ?, ?)",
                (pdf_id, flashcard["question"], flashcard["answer"], i + 1)
            )
        
        # Update PDF status to completed
        cursor.execute("UPDATE pdfs SET status = ? WHERE id = ?", ("completed", pdf_id))
        
        conn.commit()
        conn.close()
        print(f"✅ Successfully processed PDF {pdf_id} and generated flashcards")
        
    except HTTPException as e:
        # Handle specific HTTP errors from OpenAI
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        
        # Set status based on error type
        if e.status_code == 429:  # Quota exceeded
            cursor.execute("UPDATE pdfs SET status = ? WHERE id = ?", ("quota_exceeded", pdf_id))
            print(f"⚠️ Quota exceeded for PDF {pdf_id}: {e.detail}")
        elif e.status_code == 401:  # Authentication error
            cursor.execute("UPDATE pdfs SET status = ? WHERE id = ?", ("auth_error", pdf_id))
            print(f"❌ Authentication error for PDF {pdf_id}: {e.detail}")
        elif e.status_code == 504:  # Timeout
            cursor.execute("UPDATE pdfs SET status = ? WHERE id = ?", ("timeout", pdf_id))
            print(f"⏱️ Timeout error for PDF {pdf_id}: {e.detail}")
        else:  # Other HTTP errors
            cursor.execute("UPDATE pdfs SET status = ? WHERE id = ?", ("service_error", pdf_id))
            print(f"🔧 Service error for PDF {pdf_id}: {e.detail}")
            
        conn.commit()
        conn.close()
        
    except Exception as e:
        # Handle other errors
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE pdfs SET status = ? WHERE id = ?", ("error", pdf_id))
        conn.commit()
        conn.close()
        
        print(f"❌ Error processing PDF {pdf_id}: {str(e)}")

@app.get("/status/{pdf_id}")
async def get_status(pdf_id: str):
    """Get the processing status of a PDF"""
    
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM pdfs WHERE id = ?", (pdf_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    status = result[0]
    
    # Provide user-friendly error messages based on status
    error_messages = {
        "quota_exceeded": "AI quota exceeded, please try again later",
        "auth_error": "AI service authentication failed, please contact support",
        "timeout": "AI service timeout, please try again later",
        "service_error": "AI service temporarily unavailable, please try again later",
        "error": "Failed to generate flashcards, please try again later"
    }
    
    response = {"pdf_id": pdf_id, "status": status}
    
    if status in error_messages:
        response["error_message"] = error_messages[status]
    
    return response

@app.get("/flashcards/{pdf_id}")
async def get_flashcards(pdf_id: str):
    """Get all flashcards for a PDF"""
    
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flashcards WHERE pdf_id = ? ORDER BY card_number", (pdf_id,))
    flashcards = cursor.fetchall()
    
    cursor.execute("SELECT status FROM pdfs WHERE id = ?", (pdf_id,))
    pdf_status = cursor.fetchone()
    conn.close()
    
    if not pdf_status:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    if pdf_status[0] != "completed":
        return {"pdf_id": pdf_id, "status": pdf_status[0], "flashcards": []}
    
    flashcards_list = []
    for flashcard in flashcards:
        flashcards_list.append({
            "id": flashcard[0],
            "question": flashcard[2],
            "answer": flashcard[3],
            "card_number": flashcard[4]
        })
    
    return {"pdf_id": pdf_id, "status": pdf_status[0], "flashcards": flashcards_list}

@app.get("/")
async def root():
    return {"message": "PDF to Flashcards API is running"}

# Helper functions for summary endpoints
def source_exists(source_id: str) -> bool:
    """Check if source exists in database"""
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pdfs WHERE id = ?", (source_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def enqueue_build_summary(source_id: str, top_k: int, thresh: float, model: str) -> str:
    """Enqueue summary build task to Celery"""
    task = build_summary_task.delay(source_id)
    return task.id

async def build_summary_inline(source_id: str, top_k: int, thresh: float, model: str):
    """Run summary build inline for development"""
    from services.summary_builder import build_summary_inline as service_build
    return await service_build(source_id, top_k, thresh, model)

def get_chunk_text(chunk_id: str) -> str:
    """Get text content for a chunk"""
    from services.summary_builder import get_chunk_text as service_get_chunk_text
    return service_get_chunk_text(chunk_id)

def slice_preview(text: str, start_char: int, end_char: int) -> str:
    """Slice text for preview with fallback"""
    from services.summary_builder import slice_preview as service_slice_preview
    return service_slice_preview(text, start_char, end_char)

# Summary endpoints (feature-flagged)
@app.get("/summaries/{source_id}")
async def get_summary(source_id: str, db: Session = Depends(get_db)):
    """Get summary with citations for a source - never returns 500"""
    if not FEATURE_SUMMARY_CITATIONS:
        raise HTTPException(status_code=404, detail="Feature not enabled")
    
    try:
        # Check if source exists
        if not source_exists(source_id):
            summary_logger.warning(f"[get] Source not found: {source_id}")
            return {"summary_id": None, "source_id": source_id, "sentences": []}
        
        # Get summary from SQLAlchemy
        summary = db.query(Summary).filter(Summary.source_id == source_id).first()
        
        if not summary:
            summary_logger.info(f"[get] No summary found for source: {source_id}")
            return {"summary_id": None, "source_id": source_id, "sentences": []}
        
        # Get sentences with citations
        sentences = db.query(SummarySentence).filter(
            SummarySentence.summary_id == summary.id
        ).order_by(SummarySentence.order_index).all()
        
        sentence_data = []
        for sentence in sentences:
            citations = db.query(SummarySentenceCitation).filter(
                SummarySentenceCitation.sentence_id == sentence.id
            ).all()
            
            citation_data = []
            for c in citations:
                # Use stored preview_text if available, otherwise generate it
                preview_text = c.preview_text
                if not preview_text:
                    if c.start_char is not None and c.end_char is not None:
                        chunk_text = get_chunk_text(c.chunk_id)
                        preview_text = slice_preview(chunk_text, c.start_char, c.end_char)
                    else:
                        chunk_text = get_chunk_text(c.chunk_id)
                        preview_text = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                
                citation_data.append({
                    "chunk_id": c.chunk_id,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                    "score": c.score,
                    "preview_text": preview_text
                })
            
            sentence_data.append({
                "id": sentence.id,
                "order_index": sentence.order_index,
                "sentence_text": sentence.sentence_text,
                "support_status": sentence.support_status,
                "citations": citation_data
            })
        
        summary_logger.info(f"[get] Retrieved summary for source: {source_id}, sentences: {len(sentence_data)}")
        return {
            "summary_id": summary.id,
            "source_id": summary.source_id,
            "sentences": sentence_data
        }
        
    except Exception as e:
        summary_logger.exception(f"[get] failed source={source_id}: {e}")
        return {"summary_id": None, "source_id": source_id, "sentences": [], "error": "fetch_failed"}

@app.post("/summaries/{source_id}/refresh")
async def refresh_summary(source_id: str):
    """Enqueue or run summary build for a source"""
    if not FEATURE_SUMMARY_CITATIONS:
        raise HTTPException(status_code=404, detail="Feature not enabled")
    
    try:
        # Verify source exists
        if not source_exists(source_id):
            summary_logger.warning(f"[refresh] Source not found: {source_id}")
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Enqueue to Celery/RQ if available, else run inline in DEV
        if USE_CELERY:
            task_id = enqueue_build_summary(source_id, TOP_K, THRESH, SUMMARY_MODEL)
            summary_logger.info(f"[refresh] enqueued source={source_id} task={task_id}")
            return JSONResponse({"status": "queued", "task_id": task_id}, status_code=202)
        else:
            summary_logger.info(f"[refresh] running inline source={source_id}")
            result = await build_summary_inline(source_id, TOP_K, THRESH, SUMMARY_MODEL)
            return {"status": "ok", "summary_id": result.summary_id}
            
    except HTTPException:
        raise
    except Exception as e:
        summary_logger.exception(f"[refresh] failed source={source_id}: {e}")
        # Return structured error for UI
        return JSONResponse({"status": "error", "error": "refresh_failed", "detail": str(e)}, status_code=500)

@app.options("/summaries/{source_id}/refresh")
async def refresh_summary_options(source_id: str):
    """Handle CORS preflight for refresh endpoint"""
    return JSONResponse({"message": "OK"})

@app.get("/health/summary")
async def health_check():
    """Health check for summary functionality"""
    try:
        # Check database connectivity
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pdfs")
        pdf_count = cursor.fetchone()[0]
        conn.close()
        
        # Check OpenAI key presence (masked)
        openai_key = os.getenv("OPENAI_API_KEY")
        has_openai = bool(openai_key)
        
        return {
            "ok": True,
            "database_writable": True,
            "pdf_count": pdf_count,
            "openai_configured": has_openai,
            "openai_key_masked": f"{openai_key[:8]}..." if openai_key else None,
            "feature_enabled": FEATURE_SUMMARY_CITATIONS,
            "use_celery": USE_CELERY,
            "config": {
                "model": SUMMARY_MODEL,
                "top_k": TOP_K,
                "threshold": THRESH
            }
        }
    except Exception as e:
        summary_logger.exception(f"[health] check failed: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
