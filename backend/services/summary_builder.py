"""
Tolerant and debuggable summary builder service
"""
import json
import logging
import sqlite3
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from openai import OpenAI, AuthenticationError, RateLimitError, APITimeoutError, APIError
from pdf_processor import extract_text_from_pdf
from models import Base, Summary, SummarySentence, SummarySentenceCitation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging
log = logging.getLogger("citations")

# Database setup
engine = create_engine('sqlite:///pdf_flashcards.db')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configuration
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")
TOP_K = int(os.getenv("SUMMARY_EVIDENCE_TOPK", "6"))
THRESH = float(os.getenv("SUMMARY_SUPPORT_THRESHOLD", "0.74"))

def get_openai_client():
    """Get OpenAI client with error handling"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)

def get_chunks_for_source(source_id: str) -> List[Dict]:
    """Get chunks for a source"""
    conn = sqlite3.connect("pdf_flashcards.db")
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM pdfs WHERE id = ?", (source_id,))
    pdf_record = cursor.fetchone()
    conn.close()
    
    if not pdf_record:
        raise RuntimeError("No chunks found for this source")
    
    # Extract text from PDF
    file_path = Path("uploads") / f"{source_id}.pdf"
    if not file_path.exists():
        raise RuntimeError("PDF file not found")
    
    text_content = extract_text_from_pdf(str(file_path))
    if not text_content.strip():
        raise RuntimeError("No text could be extracted from PDF")
    
    # Create chunks from the text
    chunk_size = 500
    overlap = 50
    chunks = []
    words = text_content.split()
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)
        chunks.append({
            'id': f"{source_id}_chunk_{i}",
            'text': chunk_text,
            'start_word': i,
            'end_word': min(i + chunk_size, len(words))
        })
    
    return chunks

def llm_generate_sentences(chunks: List[Dict], model: str) -> List[str]:
    """Generate candidate sentences from source using LLM"""
    if not chunks:
        raise RuntimeError("No chunks provided for sentence generation")
    
    # Combine first few chunks for context
    context_text = " ".join([chunk['text'] for chunk in chunks[:3]])
    context_text = context_text[:4000]  # Limit to avoid token limits
    
    prompt = f"""You summarize academic/technical text into 6–10 short sentences.
For each sentence, also emit an "evidence_query" suitable for retrieval from the original text.
Return ONLY a JSON object with a "sentences" array: {{"sentences": [{{"sentence": "...", "evidence_query": "..."}}]}}
Do not include commentary.

Text to summarize:
{context_text}"""
    
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates structured summaries with evidence queries. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        response_content = response.choices[0].message.content
        summary_data = json.loads(response_content)
        sentences = summary_data.get("sentences", [])
        
        if not sentences:
            raise RuntimeError("Model produced no sentences")
        
        # Extract just the sentence text
        return [item.get("sentence", "") for item in sentences if item.get("sentence", "").strip()]
        
    except AuthenticationError as e:
        raise RuntimeError(f"OpenAI authentication failed: {str(e)}")
    except RateLimitError as e:
        raise RuntimeError(f"OpenAI rate limit exceeded: {str(e)}")
    except APITimeoutError as e:
        raise RuntimeError(f"OpenAI API timeout: {str(e)}")
    except APIError as e:
        raise RuntimeError(f"OpenAI API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse OpenAI response as JSON: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"OpenAI call failed: {str(e)}")

def search_chunks(source_id: str, query: str, top_k: int) -> List[Tuple[str, float, Optional[int], Optional[int], str]]:
    """Search for similar chunks using simple text matching"""
    chunks = get_chunks_for_source(source_id)
    if not chunks:
        return []
    
    # Simple similarity based on word overlap
    query_words = set(query.lower().split())
    results = []
    
    for chunk in chunks:
        chunk_words = set(chunk['text'].lower().split())
        intersection = len(query_words.intersection(chunk_words))
        union = len(query_words.union(chunk_words))
        similarity = intersection / union if union > 0 else 0
        
        # Find span in chunk
        start_char, end_char = find_span_in_chunk(query, chunk['text'])
        preview_text = chunk['text'][start_char:end_char] if end_char <= len(chunk['text']) else chunk['text'][start_char:]
        
        results.append((chunk['id'], similarity, start_char, end_char, preview_text))
    
    # Sort by similarity and return top_k
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]

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

def get_chunk_text(chunk_id: str) -> str:
    """Get text content for a chunk"""
    # Extract source_id from chunk_id
    if '_chunk_' in chunk_id:
        source_id = chunk_id.split('_chunk_')[0]
        chunks = get_chunks_for_source(source_id)
        for chunk in chunks:
            if chunk['id'] == chunk_id:
                return chunk['text']
    
    return f"Text content for chunk {chunk_id}"

def slice_preview(text: str, start_char: int, end_char: int) -> str:
    """Slice text for preview with fallback"""
    if start_char is None or end_char is None:
        return text[:200] + "..." if len(text) > 200 else text
    return text[start_char:end_char] if end_char <= len(text) else text[start_char:]

def save_summary(source_id: str, sentences_data: List[Dict]) -> str:
    """Save summary data to database with upsert"""
    session = SessionLocal()
    try:
        # Delete existing summary for this source
        session.query(Summary).filter(Summary.source_id == source_id).delete()
        
        # Create new summary
        summary = Summary(source_id=source_id, text="")
        session.add(summary)
        session.flush()
        
        # Add sentences and citations
        for sentence_data in sentences_data:
            sentence = SummarySentence(
                summary_id=summary.id,
                order_index=sentence_data["order_index"],
                sentence_text=sentence_data["sentence_text"],
                support_status=sentence_data["support_status"]
            )
            session.add(sentence)
            session.flush()
            
            # Add citations
            for citation_data in sentence_data["citations"]:
                citation = SummarySentenceCitation(
                    sentence_id=sentence.id,
                    chunk_id=citation_data["chunk_id"],
                    start_char=citation_data["start_char"],
                    end_char=citation_data["end_char"],
                    score=citation_data["score"],
                    preview_text=citation_data.get("preview_text")
                )
                session.add(citation)
        
        session.commit()
        return summary.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

async def build_summary_inline(source_id: str, top_k: int, thresh: float, model: str):
    """Build summary inline with comprehensive error handling"""
    log.info(f"[builder] Starting summary build for source: {source_id}, model: {model}, top_k: {top_k}, thresh: {thresh}")
    
    try:
        # 1) Fetch chunks for source
        chunks = get_chunks_for_source(source_id)
        if not chunks:
            raise RuntimeError("No chunks found for this source")
        
        log.info(f"[builder] Found {len(chunks)} chunks for source: {source_id}")
        
        # 2) Generate candidate sentences from source (LLM)
        sentences = llm_generate_sentences(chunks, model)
        if not sentences:
            raise RuntimeError("Model produced no sentences")
        
        log.info(f"[builder] Generated {len(sentences)} candidate sentences")
        
        # 3) For each sentence, retrieve top_k chunks (embedding/semantic search)
        out = []
        for i, sentence in enumerate(sentences):
            hits = search_chunks(source_id, sentence, top_k)
            support = "insufficient"
            cits = []
            
            if hits:
                best = hits[0]
                if best[1] >= thresh:  # similarity score
                    support = "supported"
                    # Ensure preview_text is populated; if spans are missing, slice first 200 chars
                    preview = best[4] if best[4] else slice_preview(get_chunk_text(best[0]), best[2] or 0, best[3] or 200)
                    cits = [{
                        "chunk_id": best[0],
                        "score": round(best[1], 4),
                        "start_char": best[2] or 0,
                        "end_char": best[3] or min(220, len(get_chunk_text(best[0]))),
                        "preview_text": preview
                    }]
            
            out.append({
                "order_index": i,
                "sentence_text": sentence.strip(),
                "support_status": support,
                "citations": cits
            })
            
            log.debug(f"[builder] Sentence {i}: {support} (score: {hits[0][1] if hits else 0:.3f}, threshold: {thresh})")
        
        # 4) Persist (summary, sentences, citations) in a transaction
        summary_id = save_summary(source_id, out)
        log.info(f"[builder] Saved summary={summary_id} source={source_id} sentences={len(out)} thresh={thresh} top_k={top_k}")
        
        from types import SimpleNamespace
        return SimpleNamespace(summary_id=summary_id)
        
    except Exception as e:
        log.exception(f"[builder] Failed to build summary for source={source_id}: {e}")
        raise e
