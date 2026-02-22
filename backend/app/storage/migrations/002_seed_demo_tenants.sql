begin;

with upsert_acme as (
  insert into public.tenants (name, status)
  values ('acme', 'active')
  on conflict (name) do update set status = excluded.status
  returning id
), acme as (
  select id from upsert_acme
  union all
  select id from public.tenants where name = 'acme'
  limit 1
), upsert_beta as (
  insert into public.tenants (name, status)
  values ('beta', 'active')
  on conflict (name) do update set status = excluded.status
  returning id
), beta as (
  select id from upsert_beta
  union all
  select id from public.tenants where name = 'beta'
  limit 1
)
insert into public.api_keys (tenant_id, user_id, key_hash, key_prefix, active)
select a.id, null, encode(digest('rb_acme_demo_2026_key', 'sha256'), 'hex'), 'rb_acme', true
from acme a
where not exists (
  select 1 from public.api_keys
  where key_hash = encode(digest('rb_acme_demo_2026_key', 'sha256'), 'hex')
)
union all
select b.id, null, encode(digest('rb_beta_demo_2026_key', 'sha256'), 'hex'), 'rb_beta', true
from beta b
where not exists (
  select 1 from public.api_keys
  where key_hash = encode(digest('rb_beta_demo_2026_key', 'sha256'), 'hex')
);

with acme as (
  select id from public.tenants where name = 'acme'
), beta as (
  select id from public.tenants where name = 'beta'
)
insert into public.budgets (tenant_id, department, monthly_cap_usd, max_tier)
select a.id, null, 50.00, 'fast_cheap' from acme a
where not exists (
  select 1 from public.budgets b
  where b.tenant_id = a.id and b.department is null
)
union all
select b.id, null, 400.00, 'powerful' from beta b
where not exists (
  select 1 from public.budgets bb
  where bb.tenant_id = b.id and bb.department is null
);

with acme as (
  select id from public.tenants where name = 'acme'
), beta as (
  select id from public.tenants where name = 'beta'
)
insert into public.policies (
  tenant_id,
  department,
  version,
  status,
  yaml_blob,
  published_at
)
select
  a.id,
  'rd',
  'v1',
  'active',
  $$routing:
  task_overrides:
    code_generation:
      default_virtual_model: local.smol
  tiers:
    fast_cheap:
      max_latency_ms: 1500
      providers: ["ollama"]
  fallback:
    allow_fallback: true
    max_attempts: 1
$$,
  now()
from acme a
where not exists (
  select 1 from public.policies p
  where p.tenant_id = a.id and p.department = 'rd' and p.version = 'v1'
)
union all
select
  b.id,
  'rd',
  'v1',
  'active',
  $$routing:
  task_overrides:
    code_generation:
      default_virtual_model: claude.opus
  tiers:
    powerful:
      max_latency_ms: 8000
      providers: ["anthropic"]
  fallback:
    allow_fallback: true
    max_attempts: 2
$$,
  now()
from beta b
where not exists (
  select 1 from public.policies p
  where p.tenant_id = b.id and p.department = 'rd' and p.version = 'v1'
);

commit;
