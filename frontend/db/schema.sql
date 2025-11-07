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




