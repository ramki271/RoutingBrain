-- RoutingBrain MVP schema (Step 2.1 from mvp-plan.md)
-- Target: Supabase Postgres

begin;

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- tenants
-- ---------------------------------------------------------------------------
create table if not exists public.tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create unique index if not exists ux_tenants_name on public.tenants (name);

-- ---------------------------------------------------------------------------
-- api_keys
-- ---------------------------------------------------------------------------
create table if not exists public.api_keys (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  user_id text null,
  key_hash text not null,
  key_prefix text null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create unique index if not exists ux_api_keys_key_hash on public.api_keys (key_hash);
create index if not exists ix_api_keys_tenant_id on public.api_keys (tenant_id);
create index if not exists ix_api_keys_user_id on public.api_keys (user_id);

-- ---------------------------------------------------------------------------
-- policies
-- ---------------------------------------------------------------------------
create table if not exists public.policies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  department text not null,
  version text not null,
  status text not null check (status in ('draft', 'active')),
  yaml_blob text not null,
  created_at timestamptz not null default now(),
  published_at timestamptz null
);

create index if not exists ix_policies_tenant_department on public.policies (tenant_id, department);
create unique index if not exists ux_policies_tenant_department_version on public.policies (tenant_id, department, version);
create unique index if not exists ux_policies_one_active_per_tenant_dept
  on public.policies (tenant_id, department)
  where status = 'active';

-- ---------------------------------------------------------------------------
-- budgets
-- ---------------------------------------------------------------------------
create table if not exists public.budgets (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  department text null,
  monthly_cap_usd numeric(14, 4) not null check (monthly_cap_usd >= 0),
  max_tier text null check (max_tier in ('local', 'fast_cheap', 'balanced', 'powerful')),
  created_at timestamptz not null default now()
);

create unique index if not exists ux_budgets_tenant_department
  on public.budgets (tenant_id, coalesce(department, '__all__'));
create index if not exists ix_budgets_tenant_id on public.budgets (tenant_id);

-- ---------------------------------------------------------------------------
-- routing_decisions
-- ---------------------------------------------------------------------------
create table if not exists public.routing_decisions (
  id uuid primary key default gen_random_uuid(),
  request_id text not null,
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  user_id text null,
  department text not null,
  task_type text not null,
  complexity text not null,
  risk_level text not null,
  model_tier text not null,
  virtual_model text null,
  resolved_model text not null,
  provider text not null,
  input_tokens integer not null default 0 check (input_tokens >= 0),
  output_tokens integer not null default 0 check (output_tokens >= 0),
  total_cost numeric(14, 6) not null default 0 check (total_cost >= 0),
  latency_ms integer not null default 0 check (latency_ms >= 0),
  fallback_used boolean not null default false,
  constraints_applied jsonb not null default '[]'::jsonb,
  policy_version text not null,
  created_at timestamptz not null default now()
);

create index if not exists ix_routing_decisions_tenant_created_at on public.routing_decisions (tenant_id, created_at desc);
create index if not exists ix_routing_decisions_tenant_department_created_at on public.routing_decisions (tenant_id, department, created_at desc);
create index if not exists ix_routing_decisions_request_id on public.routing_decisions (request_id);

-- ---------------------------------------------------------------------------
-- daily_usage_rollups
-- ---------------------------------------------------------------------------
create table if not exists public.daily_usage_rollups (
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  date date not null,
  total_requests integer not null default 0,
  total_tokens bigint not null default 0,
  total_cost numeric(14, 6) not null default 0,
  tier_distribution jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  primary key (tenant_id, date)
);

create index if not exists ix_daily_usage_rollups_date on public.daily_usage_rollups (date desc);

commit;
