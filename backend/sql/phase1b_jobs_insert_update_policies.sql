-- Run in Supabase SQL Editor if Phase 1 was already applied and jobs fail on INSERT
-- when not using service_role (e.g. local experiments). Safe to run once.

drop policy if exists "Users insert own jobs" on public.jobs;
create policy "Users insert own jobs"
    on public.jobs for insert
    with check (auth.uid() = user_id);

drop policy if exists "Users update own jobs" on public.jobs;
create policy "Users update own jobs"
    on public.jobs for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
