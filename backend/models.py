from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

@dataclass
class PDF:
    id: str
    filename: str
    upload_date: datetime
    status: str  # uploaded, processing, completed, error

@dataclass
class Flashcard:
    id: Optional[int]
    pdf_id: str
    question: str
    answer: str
    card_number: int

# SQLAlchemy models for summary feature
class Summary(Base):
    __tablename__ = "summaries"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String, index=True, nullable=False)  # pdf_id from existing system
    text = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), default=func.now())

class SummarySentence(Base):
    __tablename__ = "summary_sentences"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    summary_id = Column(String, ForeignKey("summaries.id"), index=True, nullable=False)
    order_index = Column(Integer, nullable=False)
    sentence_text = Column(Text, nullable=False)
    support_status = Column(String, nullable=False, default="supported")  # supported|insufficient
    created_at = Column(DateTime, server_default=func.now())

class SummarySentenceCitation(Base):
    __tablename__ = "summary_sentence_citations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sentence_id = Column(String, ForeignKey("summary_sentences.id"), index=True, nullable=False)
    chunk_id = Column(String, index=True, nullable=False)  # references existing chunks or pdf_id for now
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    preview_text = Column(Text, nullable=True)  # Added for better citation previews

# Create indexes for better query performance
Index('idx_summary_source_id', Summary.source_id)
Index('idx_sentence_summary_id_order', SummarySentence.summary_id, SummarySentence.order_index)
Index('idx_citation_sentence_id', SummarySentenceCitation.sentence_id)
Index('idx_citation_chunk_id', SummarySentenceCitation.chunk_id)
