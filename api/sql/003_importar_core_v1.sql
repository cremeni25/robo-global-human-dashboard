-- Robô Global — importa os dados do Core V1 (schema robo_global_core) para o sistema unificado.
-- Rode no SQL Editor do Supabase DEPOIS de 001_schema.sql (ou do primeiro start da API)
-- e de 002_importar_catalogo_legado.sql. Idempotente. Não altera nem apaga robo_global_core.
begin;

-- 1. Anunciantes (Awin) a partir das evidências gravadas pelo Core
insert into rg_anunciantes (id, platform, external_id, name, membership, membership_checked_at,
                            approved, auto_publish, notes, created_at)
select gen_random_uuid()::text, 'awin', m.merchant_id,
       coalesce(nullif(m.merchant_name, ''), 'Anunciante ' || m.merchant_id),
       case when m.joined then 'joined' else 'unknown' end, null,
       m.verified, true, 'importado do Core V1', now()
from (
  select f.evidence->>'merchant_id' as merchant_id,
         max(f.evidence->'product_feed_record'->>'merchant_name') as merchant_name,
         bool_or(f.evidence->>'membership_status' = 'joined') as joined,
         bool_or(f.evidence->>'eligibility' = 'verified'
                 and lower(coalesce(f.evidence->>'terms_reviewed', 'false')) = 'true') as verified
  from robo_global_core.offers f
  where f.platform = 'AWIN' and nullif(f.evidence->>'merchant_id', '') is not null
  group by 1
) m
on conflict (platform, external_id) do nothing;

-- 2. Ofertas (mesmos ids). Produtos de feed ficam publicados, mas só aparecem
--    quando o anunciante estiver liberado (afiliação confirmada + termos aprovados).
insert into rg_ofertas (id, title, description, translations, kind, platform, provider, destination_url,
                        subid_param, external_product_id, market, language, currency, commission_estimate,
                        image_url, price, category, source, anunciante_id, last_seen_at, active, published,
                        created_at, updated_at)
select f.id::text, left(f.name, 200),
       left(coalesce(f.evidence->'product_feed_record'->>'description', ''), 2000), '{}'::json, 'afiliado',
       lower(f.platform),
       left(coalesce(f.evidence->'product_feed_record'->>'merchant_name', f.platform), 200),
       f.affiliate_url,
       case when f.tracking_strategy = 'query_param' then f.tracking_template
            when f.platform = 'AWIN' then 'clickref' end,
       f.external_product_id, upper(left(coalesce(f.market, 'BR'), 10)), left(coalesce(f.language, 'pt'), 10),
       upper(left(f.currency, 3)), coalesce(f.commission_value, 0),
       left(coalesce(f.evidence->'product_feed_record'->>'merchant_image_url',
                     f.evidence->'product_feed_record'->>'aw_image_url', ''), 2000),
       f.price,
       left(coalesce(f.evidence->'product_feed_record'->>'category_name',
                     f.evidence->'product_feed_record'->>'merchant_category', ''), 300),
       'core_v1', a.id, f.updated_at,
       f.status not in ('rejected', 'expired', 'paused'),
       f.status = 'active' or f.platform = 'AWIN',
       f.created_at, now()
from robo_global_core.offers f
left join rg_anunciantes a on a.platform = 'awin' and a.external_id = f.evidence->>'merchant_id'
where f.affiliate_url like 'https://%'
on conflict do nothing;

-- 3. Links antigos /r/{oportunidade} continuam funcionando
insert into rg_aliases (id, oferta_id)
select o.id::text, o.offer_id::text
from robo_global_core.opportunities o
join rg_ofertas r on r.id = o.offer_id::text
where o.id <> o.offer_id
on conflict do nothing;

-- 4. Ligações dor → oferta que o Core tinha (demand.evidence.v2_need_id)
insert into rg_dor_ofertas (id, dor_id, oferta_id, priority, created_at)
select gen_random_uuid()::text, d.evidence->>'v2_need_id', o.offer_id::text, 1, now()
from robo_global_core.opportunities o
join robo_global_core.demands d on d.id = o.demand_id
join rg_dores rd on rd.id = d.evidence->>'v2_need_id'
join rg_ofertas r on r.id = o.offer_id::text
where o.status in ('candidate', 'testing', 'winner')
on conflict do nothing;

-- 5. Cliques (o id do clique é a chave de atribuição usada nos links já clicados)
insert into rg_cliques (id, oferta_id, dor_id, created_at, referrer, utm_source, utm_medium, utm_campaign, visitor_hash)
select coalesce(i.attribution_key, i.id::text), i.offer_id::text, null, i.occurred_at,
       left(coalesce(i.referrer, ''), 500), left(coalesce(i.source, ''), 120), '', '', left(coalesce(i.ip_hash, ''), 32)
from robo_global_core.interactions i
join rg_ofertas r on r.id = i.offer_id::text
where i.event_type in ('redirect', 'click') and length(coalesce(i.attribution_key, i.id::text)) <= 36
on conflict do nothing;

-- 6. Vendas e histórico
insert into rg_conversoes (id, platform, external_id, oferta_id, clique_id, product_id, status, gross_amount,
                           commission_amount, currency, occurred_at, source, created_at, updated_at)
select c.id::text, lower(c.platform), c.external_sale_id, r.id, k.id, '',
       case c.status when 'cancelled' then 'canceled' else c.status end,
       c.gross_value, c.commission_value, upper(left(c.currency, 3)), c.occurred_at, 'core_v1', c.created_at, now()
from robo_global_core.conversions c
left join rg_ofertas r on r.id = c.offer_id::text
left join rg_cliques k on k.id = c.attribution_key
on conflict do nothing;

insert into rg_conversao_eventos (id, conversao_id, status, received_at, raw)
select gen_random_uuid()::text, r.id, r.status, r.created_at, '{"origem":"core_v1"}'::json
from rg_conversoes r
where r.source = 'core_v1' and not exists (select 1 from rg_conversao_eventos e where e.conversao_id = r.id);

commit;

select 'anunciantes' as item, count(*) from rg_anunciantes
union all select 'anunciantes liberados', count(*) from rg_anunciantes where approved and membership = 'joined'
union all select 'ofertas importadas do core', count(*) from rg_ofertas where source = 'core_v1'
union all select 'links antigos preservados', count(*) from rg_aliases
union all select 'cliques', count(*) from rg_cliques
union all select 'vendas', count(*) from rg_conversoes;
