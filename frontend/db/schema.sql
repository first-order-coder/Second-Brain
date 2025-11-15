-- Enable useful extensions
create extension if not exists "uuid-ossp";
create extension if not exists pg_trgm;

-- Profiles linked to auth.users
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique,
  created_at timestamptz not null default now()
);

-- Notebooks own notes/tasks
create table if not exists public.notebooks (
  id uuid primary key default uuid_generate_v4(),
  owner uuid not null references auth.users(id) on delete cascade,
  title text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_notebooks_owner on public.notebooks(owner);

-- Notes
create table if not exists public.notes (
  id uuid primary key default uuid_generate_v4(),
  notebook_id uuid not null references public.notebooks(id) on delete cascade,
  owner uuid not null references auth.users(id) on delete cascade,
  title text,
  content text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_notes_notebook on public.notes(notebook_id);
create index if not exists idx_notes_owner on public.notes(owner);

-- Tasks
create table if not exists public.tasks (
  id uuid primary key default uuid_generate_v4(),
  notebook_id uuid not null references public.notebooks(id) on delete cascade,
  owner uuid not null references auth.users(id) on delete cascade,
  title text not null,
  description text,
  due_at timestamptz,
  is_done boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_tasks_notebook on public.tasks(notebook_id);
create index if not exists idx_tasks_owner on public.tasks(owner);
create index if not exists idx_tasks_due on public.tasks(due_at);

-- Tags (optional)
create table if not exists public.tags (
  id uuid primary key default uuid_generate_v4(),
  owner uuid not null references auth.users(id) on delete cascade,
  name text not null,
  unique(owner, name)
);

create table if not exists public.note_tags (
  note_id uuid not null references public.notes(id) on delete cascade,
  tag_id uuid not null references public.tags(id) on delete cascade,
  primary key (note_id, tag_id)
);

-- Row Level Security (RLS) policies
alter table public.profiles enable row level security;
alter table public.notebooks enable row level security;
alter table public.notes enable row level security;
alter table public.tasks enable row level security;
alter table public.tags enable row level security;
alter table public.note_tags enable row level security;

-- Simple owner-based policies
create policy "profiles_is_owner"
  on public.profiles for all
  using (id = auth.uid())
  with check (id = auth.uid());

create policy "notebooks_is_owner"
  on public.notebooks for all
  using (owner = auth.uid())
  with check (owner = auth.uid());

create policy "notes_is_owner"
  on public.notes for all
  using (owner = auth.uid())
  with check (owner = auth.uid());

create policy "tasks_is_owner"
  on public.tasks for all
  using (owner = auth.uid())
  with check (owner = auth.uid());

create policy "tags_is_owner"
  on public.tags for all
  using (owner = auth.uid())
  with check (owner = auth.uid());

-- For note_tags, ensure both sides belong to auth.uid()
create policy "note_tags_owner_join"
  on public.note_tags for all
  using (
    exists (select 1 from public.notes n where n.id = note_id and n.owner = auth.uid())
    and exists (select 1 from public.tags t where t.id = tag_id and t.owner = auth.uid())
  )
  with check (
    exists (select 1 from public.notes n where n.id = note_id and n.owner = auth.uid())
    and exists (select 1 from public.tags t where t.id = tag_id and t.owner = auth.uid())
  );

-- Profiles bootstrap function (optional)
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, username) values (new.id, split_part(new.email, '@', 1));
  return new;
end; $$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users for each row
execute procedure public.handle_new_user();




-- User decks linkage for Supabase-saved decks
create table if not exists public.user_decks (
  user_id uuid not null references auth.users(id) on delete cascade,
  deck_id text not null,
  role text not null default 'owner',
  created_at timestamptz not null default now(),
  primary key (user_id, deck_id)
);

alter table public.user_decks enable row level security;

drop policy if exists user_decks_owner_all on public.user_decks;
drop policy if exists user_decks_is_owner on public.user_decks;

create policy user_decks_owner_all
  on public.user_decks
  as permissive
  for all
  to public
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- Deck metadata table for human-readable titles
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

-- Foreign key: user_decks.deck_id → decks.deck_id
-- Only add if types match (both text) to avoid FK errors
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'user_decks_deck_id_fkey'
  ) then
    if exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = 'user_decks'
        and column_name = 'deck_id'
        and data_type = 'text'
    ) then
      alter table public.user_decks
        add constraint user_decks_deck_id_fkey
        foreign key (deck_id)
        references public.decks(deck_id)
        on delete cascade;
    end if;
  end if;
end $$;

create index if not exists idx_user_decks_deck_id
  on public.user_decks(deck_id);
