-- Run this SQL in the **production** Supabase project before using the feedback feature.
-- It creates a simple `public.feedback` table and opens insert access to everyone.

create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  message text not null,
  email text,
  page_url text,
  created_at timestamptz not null default now()
);

alter table public.feedback enable row level security;

-- Allow anyone (anon or authenticated) to insert feedback
create policy "Anyone can insert feedback"
on public.feedback
for insert
to public
with check (true);



