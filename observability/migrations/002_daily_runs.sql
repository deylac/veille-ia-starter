-- Migration : table daily_runs pour stocker un rapport synthèse par jour
-- À appliquer dans Supabase SQL editor avant le 1er run avec daily_report.
-- Idempotente : peut être rejouée sans casser les données existantes.

create table if not exists daily_runs (
  date date primary key,                -- 1 ligne par jour, upsert si rejeu
  ran_at timestamptz not null,
  duration_seconds int,
  total_collected int default 0,
  by_source jsonb default '{}'::jsonb,  -- { "RSS": 1, "Newsletters": 2, "Reddit": 0 }
  scoring jsonb default '[]'::jsonb,    -- [ {title, source, score, reason}, ... ]
  editorial jsonb default '{}'::jsonb,  -- { selected_count, rejected_indices, reasoning }
  enriched_count int default 0,
  published_count int default 0,
  carousel_slides_count int default 0,
  cost_usd numeric(10, 4) default 0,
  early_exit_reason text                -- null si run complet, sinon raison du early-return
);

create index if not exists daily_runs_date_idx on daily_runs (date desc);
alter table daily_runs disable row level security;
