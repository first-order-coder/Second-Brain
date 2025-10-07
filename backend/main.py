from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
import os
import uuid
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

app = FastAPI(title="PDF to Flashcards API", version="1.0.0")

# Feature flag for summary citations
FEATURE_SUMMARY_CITATIONS = os.getenv('FEATURE_SUMMARY_CITATIONS', 'true').lower() == 'true'

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

# Summary endpoints (feature-flagged)
@app.get("/summaries/{source_id}", response_model=SummaryOut)
async def get_summary(source_id: str, db: Session = Depends(get_db)):
    """Get summary with citations for a source"""
    if not FEATURE_SUMMARY_CITATIONS:
        raise HTTPException(status_code=404, detail="Feature not enabled")
    
    # Check if source exists
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pdfs WHERE id = ?", (source_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Source not found")
    conn.close()
    
    # Get summary from SQLAlchemy
    summary = db.query(Summary).filter(Summary.source_id == source_id).first()
    
    if not summary:
        return SummaryOut(summary_id="", source_id=source_id, sentences=[])
    
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
            # Generate preview text from chunk
            preview_text = None
            if c.start_char is not None and c.end_char is not None:
                # For now, we'll use a placeholder since we don't have the chunk text readily available
                # In a real implementation, you'd fetch the chunk text from the database
                preview_text = f"Chunk excerpt (chars {c.start_char}-{c.end_char})"
            else:
                preview_text = f"Chunk {c.chunk_id} excerpt"
            
            citation_data.append(CitationOut(
                chunk_id=c.chunk_id,
                start_char=c.start_char,
                end_char=c.end_char,
                score=c.score,
                preview_text=preview_text
            ))
        
        sentence_data.append(SentenceOut(
            id=sentence.id,
            order_index=sentence.order_index,
            sentence_text=sentence.sentence_text,
            support_status=sentence.support_status,
            citations=citation_data
        ))
    
    return SummaryOut(
        summary_id=summary.id,
        source_id=summary.source_id,
        sentences=sentence_data
    )

@app.post("/summaries/{source_id}/refresh", status_code=202)
async def refresh_summary(source_id: str):
    """Enqueue summary generation task"""
    if not FEATURE_SUMMARY_CITATIONS:
        raise HTTPException(status_code=404, detail="Feature not enabled")
    
    # Check if source exists
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pdfs WHERE id = ?", (source_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Source not found")
    conn.close()
    
    # Enqueue Celery task
    task = build_summary_task.delay(source_id)
    
    return {"message": "Summary generation started", "task_id": task.id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
