-- Fix: Backfill missing decks rows for existing user_decks
-- Run this if you're getting FK constraint violations
-- This creates the decks table and populates it with all deck_ids from user_decks

-- 1) Create the decks table if it doesn't exist
create table if not exists public.decks (
  deck_id text primary key,
  title text not null,
  source_type text,      -- "pdf" | "youtube"
  source_label text,     -- filename or youtube title
  created_at timestamptz not null default now()
);

alter table public.decks enable row level security;

drop policy if exists decks_read_all on public.decks;
drop policy if exists decks_write_all on public.decks;
drop policy if exists decks_update_all on public.decks;

create policy decks_read_all
  on public.decks
  for select
  to authenticated
  using (true);

create policy decks_write_all
  on public.decks
  for insert
  to authenticated
  with check (true);

create policy decks_update_all
  on public.decks
  for update
  to authenticated
  using (true)
  with check (true);

-- 2) Convert user_decks.deck_id from uuid to text if needed
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'user_decks'
      and column_name = 'deck_id'
      and data_type = 'uuid'
  ) then
    -- Drop constraints first
    alter table public.user_decks drop constraint if exists user_decks_pkey;
    alter table public.user_decks drop constraint if exists user_decks_deck_id_fkey;
    
    -- Convert uuid to text
    alter table public.user_decks
      alter column deck_id type text using deck_id::text;
    
    -- Recreate primary key
    alter table public.user_decks
      add constraint user_decks_pkey primary key (user_id, deck_id);
  end if;
end $$;

-- 3) Temporarily disable the FK constraint if it exists
alter table public.user_decks
  drop constraint if exists user_decks_deck_id_fkey;

-- 4) Populate decks table with all existing deck_ids from user_decks
insert into public.decks (deck_id, title, source_type, source_label)
select distinct 
  ud.deck_id::text,
  ud.deck_id::text as title,  -- Use deck_id as fallback title for existing decks
  null as source_type,
  null as source_label
from public.user_decks ud
where not exists (
  select 1 from public.decks d where d.deck_id = ud.deck_id::text
)
on conflict (deck_id) do nothing;

-- Re-add the foreign key constraint
alter table public.user_decks
  add constraint user_decks_deck_id_fkey
  foreign key (deck_id)
  references public.decks(deck_id)
  on delete cascade;

