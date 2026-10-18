-- ComputePilot V6: atomic daily authorization ledger (Asia/Bangkok).
-- Run in a PRIVATE Supabase project; never expose the service role key.
create table if not exists public.cp_budget_days (
  day date primary key,
  reserved_cents integer not null default 0 check (reserved_cents between 0 and 500)
);
create table if not exists public.cp_budget_reservations (
  id uuid primary key,
  day date not null references public.cp_budget_days(day),
  reserved_cents integer not null check (reserved_cents > 0),
  created_at timestamptz not null default now()
);
alter table public.cp_budget_days enable row level security;
alter table public.cp_budget_reservations enable row level security;
revoke all on public.cp_budget_days from anon, authenticated;
revoke all on public.cp_budget_reservations from anon, authenticated;
create or replace function public.cp_reserve_budget(p_id uuid, p_cents integer)
returns jsonb language plpgsql security definer set search_path = public
as $$
declare d date := (now() at time zone 'Asia/Bangkok')::date;
        current_total integer;
        existing public.cp_budget_reservations%rowtype;
begin
 if p_cents < 1 or p_cents > 500 then raise exception 'invalid reservation'; end if;
 select * into existing from public.cp_budget_reservations where id=p_id;
 if found then return jsonb_build_object('approved',true,'duplicate',true,'day',existing.day,'reserved_cents',existing.reserved_cents); end if;
 insert into public.cp_budget_days(day,reserved_cents) values(d,0) on conflict do nothing;
 update public.cp_budget_days set reserved_cents=reserved_cents+p_cents
   where day=d and reserved_cents+p_cents <= 500 returning reserved_cents into current_total;
 if current_total is null then return jsonb_build_object('approved',false,'day',d,'reason','daily budget exhausted'); end if;
 insert into public.cp_budget_reservations(id,day,reserved_cents) values(p_id,d,p_cents);
 return jsonb_build_object('approved',true,'day',d,'reserved_cents',p_cents,'total_reserved_cents',current_total);
end $$;
revoke all on function public.cp_reserve_budget(uuid,integer) from public, anon, authenticated;
grant execute on function public.cp_reserve_budget(uuid,integer) to service_role;
-- No refund mechanism: conservative reservations remain spent even on provider failure.
-- This caps reservations, NOT external provider invoices. Review token pricing before enabling.
