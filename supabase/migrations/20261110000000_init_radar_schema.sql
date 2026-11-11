-- Sardegna B2B Radar — Milestone 1 & 2 Schema (EDILMORITTU S.R.L.)
-- Follows Supabase Postgres Best Practices: FK indexes, partial indexes, and RLS.

create table if not exists public.tenders (
    dedup_key text primary key,
    source text not null,
    external_id text not null,
    notice_type text not null,
    cig text,
    cup text,
    title text not null,
    contracting_authority text not null,
    delegated_authority text,
    province text not null,
    municipality text,
    amount_eur double precision,
    award_amount_eur double precision,
    discount_pct double precision,
    winner_company text,
    winner_tax_id text,
    winner_distance_km integer,
    rup_name text,
    contract_started boolean,
    has_subcontracts boolean,
    score double precision not null,
    logistics_tier text not null,
    crm_status text not null default 'da_chiamare'
        check (crm_status in ('da_chiamare', 'preventivo_inviato', 'vinto', 'scartato')),
    notified boolean not null default false,
    url text not null,
    attachment_url text,
    http_status integer,
    payload jsonb not null,
    discovered_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (source, external_id)
);

create table if not exists public.cme_items (
    id bigint generated always as identity primary key,
    dedup_key text not null references public.tenders(dedup_key) on delete cascade,
    item_number integer,
    tariff_code text not null default '',
    description text not null,
    unit text not null default '',
    quantity double precision not null default 0,
    unit_price_eur double precision,
    total_price_eur double precision,
    product_line text not null check (product_line in ('linea_a', 'linea_b')),
    category text not null,
    matched_catalog_label text not null default ''
);

-- Foreign-key index for fast joins and cascade deletes
create index if not exists idx_cme_items_dedup_key
    on public.cme_items (dedup_key);

-- Partial index for Milestone 2 Dashboard actionable queue (`da_chiamare` above threshold)
create index if not exists idx_tenders_actionable
    on public.tenders (score desc, updated_at desc)
    where crm_status = 'da_chiamare' and score >= 45.0;

-- Partial index for Telegram/WhatsApp cron worker unnotified queue
create index if not exists idx_tenders_unnotified
    on public.tenders (score desc)
    where notified = false and score >= 45.0;

-- Partial index for fast CIG lookup
create index if not exists idx_tenders_cig
    on public.tenders (cig)
    where cig is not null;

-- Row Level Security (Service Role bypasses automatically; Dashboard users require explicit tenant claim)
alter table public.tenders enable row level security;
alter table public.cme_items enable row level security;

create policy "Edilmorittu tenant users can view tenders"
    on public.tenders for select
    to authenticated
    using ((auth.jwt() -> 'app_metadata' ->> 'tenant') = 'edilmorittu');

create policy "Edilmorittu tenant users can update tender CRM status"
    on public.tenders for update
    to authenticated
    using ((auth.jwt() -> 'app_metadata' ->> 'tenant') = 'edilmorittu')
    with check ((auth.jwt() -> 'app_metadata' ->> 'tenant') = 'edilmorittu');

create policy "Edilmorittu tenant users can view cme_items"
    on public.cme_items for select
    to authenticated
    using ((auth.jwt() -> 'app_metadata' ->> 'tenant') = 'edilmorittu');
