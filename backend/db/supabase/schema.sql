-- Supabase schema for Second Brain app
-- This mirrors the existing SQLite schema with PostgreSQL optimizations

-- Enable extensions (idempotent)
create extension if not exists "uuid-ossp";
create extension if not exists pg_trgm;
create extension if not exists vector;  -- for future vector support

-- Core tables mirroring current SQLite schema
-- Using UUIDs for better distributed system compatibility

-- PDFs table (sources)
create table if not exists pdfs (
  id uuid primary key default uuid_generate_v4(),
  filename text not null,
  upload_date timestamptz not null default now(),
  status text not null default 'uploaded',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Flashcards table
create table if not exists flashcards (
  id uuid primary key default uuid_generate_v4(),
  pdf_id uuid not null references pdfs(id) on delete cascade,
  question text not null,
  answer text not null,
  card_number integer not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Summary tables (for existing SQLAlchemy models)
create table if not exists summaries (
  id uuid primary key default uuid_generate_v4(),
  source_id uuid not null references pdfs(id) on delete cascade,
  text text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists summary_sentences (
  id uuid primary key default uuid_generate_v4(),
  summary_id uuid not null references summaries(id) on delete cascade,
  order_index integer not null,
  sentence_text text not null,
  support_status text not null default 'supported',
  created_at timestamptz not null default now()
);

create table if not exists summary_sentence_citations (
  id uuid primary key default uuid_generate_v4(),
  sentence_id uuid not null references summary_sentences(id) on delete cascade,
  chunk_id uuid not null,
  start_char integer,
  end_char integer,
  score float,
  preview_text text,
  created_at timestamptz not null default now()
);

-- Indexes for better query performance
create index if not exists idx_pdfs_status on pdfs(status);
create index if not exists idx_pdfs_upload_date on pdfs(upload_date);
create index if not exists idx_flashcards_pdf_id on flashcards(pdf_id);
create index if not exists idx_flashcards_card_number on flashcards(pdf_id, card_number);
create index if not exists idx_summaries_source_id on summaries(source_id);
create index if not exists idx_summary_sentences_summary_id_order on summary_sentences(summary_id, order_index);
create index if not exists idx_citations_sentence_id on summary_sentence_citations(sentence_id);
create index if not exists idx_citations_chunk_id on summary_sentence_citations(chunk_id);

-- Full-text search indexes for better search performance
create index if not exists idx_flashcards_question_gin on flashcards using gin(to_tsvector('english', question));
create index if not exists idx_flashcards_answer_gin on flashcards using gin(to_tsvector('english', answer));

-- Future vector table for embeddings (disabled by default)
create table if not exists card_embeddings (
  card_id uuid primary key references flashcards(id) on delete cascade,
  embedding vector(1536),  -- adjust dimensions to your embedding model
  model_name text,
  created_at timestamptz not null default now()
);

-- Create updated_at trigger function
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Add updated_at triggers
create trigger update_pdfs_updated_at before update on pdfs
    for each row execute function update_updated_at_column();

create trigger update_flashcards_updated_at before update on flashcards
    for each row execute function update_updated_at_column();

create trigger update_summaries_updated_at before update on summaries
    for each row execute function update_updated_at_column();

-- Row Level Security (RLS) - disabled for now since we're using service role
-- Uncomment these when ready to enable RLS:
-- alter table pdfs enable row level security;
-- alter table flashcards enable row level security;
-- alter table summaries enable row level security;
-- alter table summary_sentences enable row level security;
-- alter table summary_sentence_citations enable row level security;
-- alter table card_embeddings enable row level security;

-- Grant permissions (adjust as needed for your security model)
-- For now, we'll rely on the service role key for all operations
