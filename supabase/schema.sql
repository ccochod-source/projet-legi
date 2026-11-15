-- À exécuter dans l'éditeur SQL Supabase ; aucune politique publique.
create table if not exists public.analyses (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    question text not null,
    rapport jsonb not null,
    outils jsonb not null default '[]'::jsonb,
    statut text not null,
    modele text not null
);

alter table public.analyses enable row level security;
revoke all on table public.analyses from anon, authenticated;
grant select, insert on table public.analyses to service_role;
