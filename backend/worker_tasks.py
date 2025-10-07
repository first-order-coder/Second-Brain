import os
import json
import re
import sqlite3
from typing import List, Dict, Tuple
from celery import Celery
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from models import Base, Summary, SummarySentence, SummarySentenceCitation
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pdf_processor import extract_text_from_pdf
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Initialize Celery
celery_app = Celery('summary_worker')
celery_app.config_from_object({
    'broker_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'result_backend': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
})

# Initialize OpenAI client (will be created when needed)
def get_openai_client():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)

# Database setup
engine = create_engine('sqlite:///pdf_flashcards.db')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configuration
SIMILARITY_THRESHOLD = float(os.getenv('SUMMARY_SUPPORT_THRESHOLD', '0.3'))
MAX_SENTENCES = int(os.getenv('SUMMARY_MAX_SENTENCES', '10'))
MAX_TOKENS = int(os.getenv('SUMMARY_MAX_TOKENS', '2000'))

def split_into_sentences(text: str) -> List[str]:
    """Lightweight sentence splitting using regex"""
    # Simple sentence splitting - can be enhanced with nltk if needed
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

def create_text_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
    """Split text into overlapping chunks for better retrieval"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)
        chunks.append({
            'id': f"chunk_{i}",
            'text': chunk_text,
            'start_word': i,
            'end_word': min(i + chunk_size, len(words))
        })
    
    return chunks

def compute_similarity(query: str, chunks: List[Dict]) -> List[Tuple[Dict, float]]:
    """Compute TF-IDF similarity between query and chunks"""
    if not chunks:
        return []
    
    # Prepare texts for TF-IDF
    texts = [chunk['text'] for chunk in chunks]
    texts.append(query)
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    # Compute similarities
    query_vector = tfidf_matrix[-1]
    chunk_vectors = tfidf_matrix[:-1]
    
    similarities = cosine_similarity(query_vector, chunk_vectors).flatten()
    
    # Return chunks with similarities
    results = [(chunks[i], similarities[i]) for i in range(len(chunks))]
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results

def find_span_in_chunk(sentence: str, chunk_text: str) -> Tuple[int, int]:
    """Find the span of sentence within chunk text"""
    # Try exact match first
    start_idx = chunk_text.lower().find(sentence.lower())
    if start_idx != -1:
        end_idx = start_idx + len(sentence)
        return start_idx, end_idx
    
    # Try to find key words from the sentence in the chunk
    sentence_words = sentence.lower().split()
    chunk_words = chunk_text.lower().split()
    
    # Find the best matching sequence
    best_match_start = None
    best_match_length = 0
    
    for i in range(len(chunk_words)):
        match_length = 0
        for j in range(len(sentence_words)):
            if i + j < len(chunk_words) and chunk_words[i + j] == sentence_words[j]:
                match_length += 1
            else:
                break
        
        if match_length > best_match_length and match_length >= 3:  # At least 3 words match
            best_match_length = match_length
            # Convert word index to character index
            word_start_idx = chunk_text.lower().find(chunk_words[i])
            word_end_idx = word_start_idx
            for k in range(best_match_length):
                if i + k < len(chunk_words):
                    word_end_idx += len(chunk_words[i + k]) + 1  # +1 for space
            
            best_match_start = word_start_idx
            best_match_end = word_end_idx - 1  # Remove trailing space
    
    if best_match_start is not None:
        return best_match_start, best_match_end
    
    # Fallback: return first 240 characters of chunk
    return 0, min(240, len(chunk_text))

@celery_app.task
def build_summary_task(source_id: str):
    """Celery task to build summary with citations"""
    print(f"=== DEBUG: Starting summary build for source_id: {source_id} ===")
    print(f"Configuration: threshold={SIMILARITY_THRESHOLD}, max_sentences={MAX_SENTENCES}, max_tokens={MAX_TOKENS}")
    
    try:
        # Check if source exists
        conn = sqlite3.connect("pdf_flashcards.db")
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM pdfs WHERE id = ?", (source_id,))
        pdf_record = cursor.fetchone()
        
        if not pdf_record:
            print(f"PDF not found for source_id: {source_id}")
            return {"error": "PDF not found"}
        
        # Extract text from PDF
        file_path = Path("uploads") / f"{source_id}.pdf"
        if not file_path.exists():
            print(f"PDF file not found: {file_path}")
            return {"error": "PDF file not found"}
        
        text_content = extract_text_from_pdf(str(file_path))
        if not text_content.strip():
            print(f"No text extracted from PDF: {source_id}")
            return {"error": "No text could be extracted"}
        
        print(f"Extracted {len(text_content)} characters from PDF")
        
        # Create text chunks
        chunks = create_text_chunks(text_content)
        print(f"Created {len(chunks)} chunks")
        print(f"=== DEBUG: About to call OpenAI ===")
        
        # Generate summary using OpenAI
        prompt = f"""You summarize academic/technical text into 6–10 short sentences.
For each sentence, also emit an "evidence_query" suitable for retrieval from the original text.
Return ONLY a JSON object with a "sentences" array: {{"sentences": [{{"sentence": "...", "evidence_query": "..."}}]}}
Do not include commentary.

Text to summarize:
{text_content[:4000]}"""  # Limit input to avoid token limits
        
        try:
            client = get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates structured summaries with evidence queries. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            response_content = response.choices[0].message.content
            print(f"OpenAI response: {response_content}")
            
            summary_data = json.loads(response_content)
            proposed_sentences = summary_data.get("sentences", [])
            
            print(f"Generated {len(proposed_sentences)} proposed sentences")
            print(f"Summary data keys: {list(summary_data.keys())}")
        except Exception as e:
            print(f"Error in OpenAI call: {str(e)}")
            print(f"Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"OpenAI call failed: {str(e)}"}
        
        # Validate each sentence and find citations
        session = SessionLocal()
        
        # Delete existing summary for this source
        session.query(Summary).filter(Summary.source_id == source_id).delete()
        
        # Create new summary
        summary = Summary(source_id=source_id, text="")
        session.add(summary)
        session.flush()  # Get the ID
        
        supported_sentences = []
        
        for i, item in enumerate(proposed_sentences[:MAX_SENTENCES]):
            sentence_text = item.get("sentence", "")
            evidence_query = item.get("evidence_query", sentence_text)
            
            if not sentence_text.strip():
                continue
            
            # Find similar chunks
            similar_chunks = compute_similarity(evidence_query, chunks)
            
            # Check if we have sufficient support
            max_similarity = similar_chunks[0][1] if similar_chunks else 0
            
            sentence = SummarySentence(
                summary_id=summary.id,
                order_index=i,
                sentence_text=sentence_text,
                support_status="supported" if max_similarity >= SIMILARITY_THRESHOLD else "insufficient"
            )
            session.add(sentence)
            session.flush()
            
            # Add citations if supported
            if max_similarity >= SIMILARITY_THRESHOLD:
                for chunk, similarity in similar_chunks[:2]:  # Top 2 chunks
                    start_char, end_char = find_span_in_chunk(sentence_text, chunk['text'])
                    
                    citation = SummarySentenceCitation(
                        sentence_id=sentence.id,
                        chunk_id=chunk['id'],
                        start_char=start_char,
                        end_char=end_char,
                        score=float(similarity)
                    )
                    session.add(citation)
            
            supported_sentences.append(sentence_text)
            print(f"Sentence {i}: {'supported' if max_similarity >= SIMILARITY_THRESHOLD else 'insufficient'} (similarity: {max_similarity:.3f}, threshold: {SIMILARITY_THRESHOLD})")
        
        # Update summary text
        summary.text = " ".join(supported_sentences)
        
        session.commit()
        session.close()
        
        print(f"Successfully built summary for source_id: {source_id}")
        return {"status": "completed", "sentences_count": len(supported_sentences)}
        
    except Exception as e:
        print(f"Error building summary for source_id {source_id}: {str(e)}")
        return {"error": str(e)}
