-- Migration: Add decks table and connect to user_decks
-- Run this in Supabase SQL Editor

-- 1) User → Deck mapping
create table if not exists public.user_decks (
  user_id uuid not null references auth.users(id) on delete cascade,
  deck_id text not null,
  role text not null default 'owner',
  created_at timestamptz not null default now(),
  primary key (user_id, deck_id)
);

alter table public.user_decks enable row level security;

drop policy if exists user_decks_owner_all on public.user_decks;

create policy user_decks_owner_all
on public.user_decks
as permissive
for all
to public
using (user_id = auth.uid())
with check (user_id = auth.uid());



-- 2) Deck metadata table (proper titles!)
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



-- 3) Connect user_decks → decks
-- First, convert existing user_decks.deck_id from uuid to text if needed
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

-- 4) Populate decks table with existing deck_ids from user_decks
-- This ensures all existing user_decks have corresponding rows in decks
-- BEFORE we add the foreign key constraint
insert into public.decks (deck_id, title, source_type, source_label)
select distinct 
  ud.deck_id,
  ud.deck_id as title,  -- Use deck_id as fallback title for existing decks
  null as source_type,
  null as source_label
from public.user_decks ud
where not exists (
  select 1 from public.decks d where d.deck_id = ud.deck_id
)
on conflict (deck_id) do nothing;

-- 5) Now add the foreign key constraint
-- This will succeed because all deck_ids in user_decks now exist in decks
alter table public.user_decks
  drop constraint if exists user_decks_deck_id_fkey;

alter table public.user_decks
  add constraint user_decks_deck_id_fkey
  foreign key (deck_id)
  references public.decks(deck_id)
  on delete cascade;

create index if not exists idx_user_decks_deck_id
  on public.user_decks(deck_id);

