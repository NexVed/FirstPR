-- FirstPR Supabase schema.
-- Run in the Supabase SQL editor.

-- User profiles (row owned by the user).
create table if not exists public.user_profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    display_name text,
    github_username text,
    created_at timestamptz not null default now()
);

-- Repository analyses produced by POST /api/v1/repositories/analyze.
create table if not exists public.repository_analyses (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    repository_url text not null,
    owner text not null,
    name text not null,
    conventions jsonb not null default '{}'::jsonb,
    recommendations jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists repository_analyses_user_idx
    on public.repository_analyses (user_id, created_at desc);

-- Contribution plans produced by POST /api/v1/plans.
create table if not exists public.contribution_plans (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    repository_url text not null,
    issue_number int not null,
    issue_title text not null,
    plan jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists contribution_plans_user_idx
    on public.contribution_plans (user_id, created_at desc);

-- Screenshot triage results produced by POST /api/v1/triage.
create table if not exists public.screenshot_triages (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    repository_url text not null,
    note text,
    analysis jsonb not null default '{}'::jsonb,
    related_issues jsonb not null default '[]'::jsonb,
    draft jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists screenshot_triages_user_idx
    on public.screenshot_triages (user_id, created_at desc);

-- Activity history feed.
create table if not exists public.activity_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    activity_type text not null,
    summary jsonb not null default '{}'::jsonb,
    entity_id uuid,
    created_at timestamptz not null default now()
);
create index if not exists activity_history_user_idx
    on public.activity_history (user_id, created_at desc);

-- Row level security: users may only touch their own rows.
alter table public.user_profiles enable row level security;
alter table public.repository_analyses enable row level security;
alter table public.contribution_plans enable row level security;
alter table public.screenshot_triages enable row level security;
alter table public.activity_history enable row level security;

create policy "users read own profile" on public.user_profiles
    for select using (auth.uid () = id);
create policy "users update own profile" on public.user_profiles
    for update using (auth.uid () = id);
create policy "users insert own profile" on public.user_profiles
    for insert with check (auth.uid () = id);

create policy "users select own analyses" on public.repository_analyses
    for select using (auth.uid () = user_id);
create policy "users select own plans" on public.contribution_plans
    for select using (auth.uid () = user_id);
create policy "users select own triages" on public.screenshot_triages
    for select using (auth.uid () = user_id);
create policy "users select own activity" on public.activity_history
    for select using (auth.uid () = user_id);

-- The API writes through the server-side service-role key, which bypasses
-- RLS by design; no insert/update policies are required for it.
