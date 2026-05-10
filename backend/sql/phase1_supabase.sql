-- Phase 1 — run in Supabase SQL Editor (dashboard → SQL → New query)
-- ── Jobs table ────────────────────────────────────────────────
create table if not exists public.jobs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    topic text not null,
    status text not null default 'running'
        check (status in ('running', 'done', 'error')),
    final_report text,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Index for fast per-user queries
create index idx_jobs_user_id on public.jobs(user_id);
create index idx_jobs_created_at on public.jobs(created_at desc);

-- Auto-update updated_at
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger jobs_updated_at
    before update on public.jobs
    for each row execute function update_updated_at();

-- ── Row Level Security ────────────────────────────────────────
alter table public.jobs enable row level security;

-- Users can only see their own jobs
create policy "Users see own jobs"
    on public.jobs for select
    using (auth.uid() = user_id);

-- Service role (backend) can do everything — no policy needed,
-- service_role key bypasses RLS.

-- ── Rate limit tracking (optional, for server-side limiting) ──
create table if not exists public.rate_limits (
    user_id uuid primary key references auth.users(id) on delete cascade,
    last_request_at timestamptz not null default now(),
    request_count int not null default 0,
    window_start timestamptz not null default now()
);
