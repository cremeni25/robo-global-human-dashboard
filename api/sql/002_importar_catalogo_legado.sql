-- Robô Global v2 — importa o catálogo editorial do sistema antigo (mesmo banco Supabase).
-- Rode UMA vez no SQL Editor do Supabase, depois de 001_schema.sql (ou do primeiro
-- start da API). É idempotente: rodar de novo não duplica nada.
--
-- O que importa:
--   robo_global.nichos / subnichos / dores  → rg_nichos / rg_subnichos / rg_dores
--       (mesmos ids e mesmo estado de publicação)
--   public.solucoes (ativas e com link https) → rg_ofertas, SEMPRE despublicadas:
--       um humano revisa link, plataforma e id do produto antes de publicar.
--   robo_global.dor_solucoes (publicados)   → rg_dor_ofertas
-- O que NÃO importa: tabelas financeiras e de decisão antigas (eventos_financeiros,
-- sales, partner_balances, decisoes_estrategicas, acoes_executadas...), que eram
-- simuladas ou inconsistentes. Elas continuam intactas no banco, só para consulta.
begin;

insert into rg_nichos (id, slug, title, description, translations, published, position, created_at)
select n.id::text, n.slug, n.title, coalesce(n.description, ''), '{}'::json,
       coalesce(n.published, false) and n.slug !~* '^(teste|test)-', 0, now()
from robo_global.nichos n
on conflict do nothing;

insert into rg_subnichos (id, nicho_id, slug, title, description, translations, published, position, created_at)
select s.id::text, s.nicho_id::text, s.slug, s.title, coalesce(s.description, ''), '{}'::json,
       coalesce(s.published, false) and s.slug !~* '^(teste|test)-', 0, now()
from robo_global.subnichos s
join rg_nichos n on n.id = s.nicho_id::text
on conflict do nothing;

insert into rg_dores (id, subnicho_id, slug, title, description, translations, published, position, created_at)
select d.id::text, d.subnicho_id::text, d.slug, d.title, coalesce(d.description, ''), '{}'::json,
       coalesce(d.published, false) and d.slug !~* '^(teste|test)-', 0, now()
from robo_global.dores d
join rg_subnichos s on s.id = d.subnicho_id::text
on conflict do nothing;

insert into rg_ofertas (id, title, description, translations, kind, platform, provider, destination_url,
                        subid_param, external_product_id, market, language, currency,
                        commission_estimate, image_url, active, published, created_at, updated_at)
select so.id::text, so.nome, coalesce(so.descricao, ''), '{}'::json, 'afiliado', 'manual', '',
       so.link_afiliado, null, null, 'BR', 'pt', 'BRL', 0, '', true, false, now(), now()
from public.solucoes so
where coalesce(so.ativo, false) and so.link_afiliado like 'https://%'
on conflict do nothing;

insert into rg_dor_ofertas (id, dor_id, oferta_id, priority, created_at)
select gen_random_uuid()::text, v.dor_id::text, v.solucao_id::text, coalesce(v.prioridade, 1), now()
from robo_global.dor_solucoes v
join rg_dores d on d.id = v.dor_id::text
join rg_ofertas o on o.id = v.solucao_id::text
where coalesce(v.published, false)
on conflict do nothing;

commit;

-- Conferência:
select 'nichos' as tabela, count(*) from rg_nichos
union all select 'subnichos', count(*) from rg_subnichos
union all select 'dores', count(*) from rg_dores
union all select 'ofertas (despublicadas para revisão)', count(*) from rg_ofertas
union all select 'vinculos', count(*) from rg_dor_ofertas;
