-- Migration : table api_calls pour le logging des appels LLM
-- À appliquer une fois manuellement dans Supabase (SQL editor) avant le 1er run.
-- Idempotent : peut être rejoué sans casser les données existantes.

create table if not exists api_calls (
  id uuid primary key default gen_random_uuid(),
  timestamp timestamptz not null default now(),
  date date not null,
  provider text not null,            -- 'anthropic' | 'openai' | 'google'
  model text not null,               -- ID exact du modèle
  operation text not null,           -- 'messages.create' | 'images.generate' | 'generate_content'
  input_tokens int,
  output_tokens int,
  duration_ms int,
  success boolean not null,
  error text,
  cost_estimate_usd numeric(10, 4),
  context jsonb default '{}'::jsonb
);

create index if not exists api_calls_date_model_idx on api_calls (date, model);
create index if not exists api_calls_timestamp_idx on api_calls (timestamp desc);

-- Optionnel : RLS désactivé par défaut sur cette table interne.
-- La table n'est jamais lue/écrite côté client, uniquement par le pipeline avec
-- la SUPABASE_SERVICE_KEY (role service, bypasse RLS).
alter table api_calls disable row level security;
