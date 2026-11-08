# Migração: dos 7 repositórios para o Robô Global v2

Auditoria feita em 08/11/2026. Critério: **fica o que funciona e serve à evolução; sai o que está duplicado, simulado, quebrado ou sem uso.** Os repositórios antigos não foram alterados. Depois do novo deploy, eles podem ser arquivados no GitHub (Settings → Archive).

## Resumo

| Repositório antigo | Decisão | Destino na v2 |
|---|---|---|
| `robo` (backend em produção, `main.py` com 2.162 linhas) | Regras reaproveitadas, código reescrito | `api/` |
| `robo-global-frontend` | **Reaproveitado** (site público) | `web/` |
| Core V1 (`robo-global-core-v1.onrender.com`, código não acessível) | Substituído | `api/` (`/public/*` e `/r/{id}`) |
| `robo-global-api` | Removido | — |
| `robo-global` | Removido | — |
| `robo-global-dashboard` | Removido | Painel `/admin` |
| `robo-global-landing` | Removido | Página inicial do `web/` |
| `affiliate-` | Removido | — |
| `operational_loop.py` | Vazio | — |
| `robo-global-human-dashboard` (este) | Ideia mantida, código substituído | "Leitura humana" no `/admin` |

## O que foi aproveitado e por quê

**Do backend `robo`:**
- A hierarquia **Nicho → Subnicho → Dor → Solução** e a regra de publicação (o filho só aparece se o pai estiver publicado; slugs `teste-` e `test-` nunca são publicados). Era a parte mais sólida.
- O princípio de **falhar fechado** e de **sair só por link rastreado** (antes `/go/{uuid}` → Core `/r/{id}`, agora `/r/{id}` direto).
- O contrato das rotas públicas (`/public/nichos`, `/public/nichos/{slug}/subnichos`, `/public/subnichos/{id}/dores`, `/public/dores/{id}/solucoes`, `/public/ofertas`). O frontend continuou funcionando sem reescrita.
- A ideia de decisões ESCALAR, TESTAR e PAUSAR, agora com **dados reais**, motivo explicado e **aprovação humana**.
- O botão de ligar e desligar, agora **persistente no banco e protegido por token**.
- A ideia de "leitura humana", agora em frases geradas só de dados reais.

**Do `robo-global-frontend`:** Home, Sobre, Nichos, Dores, Ofertas, os três idiomas, o visual e o carregamento com tempo limite (`catalogRequest.ts`, com testes). Também as traduções editoriais (`catalogCopy.ts`), que continuam valendo porque a migração preserva os IDs.

## O que foi retirado e por quê

| Item | Motivo |
|---|---|
| ~25 rotas abertas (`/governanca/desligar`, `/operacional/*`, `/master/*`, `/estrategia/*`, `/financeiro/*`) | Sem autenticação: qualquer pessoa podia gravar dados ou desligar o sistema |
| Rotas duplicadas (`/estrategia/decisoes-real` ×4, `/acoes-real` ×4, `/master/produto` ×2…) | Só a primeira valia; o resto era código morto |
| `ESTADO_GLOBAL` (capital e risco em memória) | Números fictícios que se perdiam a cada reinício |
| Pipeline financeiro (`sales_service`, `balance_service`, `payout_service`, divisão 60/40) | Contava reembolso como venda, duplicava em reenvio; o saque nem funcionava |
| Webhooks Hotmart, Eduzz e Monetizze antigos | Formato de assinatura incompatível com a Hotmart; status sempre "aprovado" |
| `/go?produto=` e `/go/{gul}` legados, GUL com hash | Contornavam o rastreio; substituídos por `/r/{id}` |
| `/b2/produtos` | Gravava senha master em texto puro |
| `robo_receiver.py`, `motor_interno.py`, `cen.py`, `worker.py` | Apps soltos que não rodavam; logs em arquivo local; `worker` chamava rota inexistente |
| `controlador_acao_externa.py`, `adapter_google_ads.py` | Link Eduzz fixo no código e um adaptador que não fazia nada |
| `acquisition_meta_ads.py` (em `robo-global-api`) | **Ativava campanhas pagas reais sem aprovação humana** |
| `robo-global-api`, `robo-global` | Versões antigas da API, com outra modelagem |
| `affiliate-` | Interface com erro de sintaxe, nunca usada |
| `robo-global-dashboard` | Login apontava para rota inexistente; guardava a chave no navegador |
| Frontend: `_future/`, `CMS.tsx` (chave master no bundle), `dashboard.tsx`, `Go.tsx`, `services/`, `hooks/`, `adapters/`, `data/`, `i18n/`, `components/`, Tailwind, axios, ~10 MB de imagens sem uso | Sem uso ou inseguro |
| Este repositório (`index.html`, `app.js`, `public/`) | Mostrava estado e decisões **inventados** no código |

## Banco de dados

A v2 cria tabelas novas com prefixo `rg_` no **mesmo Supabase** e **não apaga nada** do legado. Para trazer o catálogo, rode `api/sql/002_importar_catalogo_legado.sql` no SQL Editor do Supabase. O script é idempotente e já foi testado em PostgreSQL 16.

- Nichos, subnichos e dores entram com os mesmos IDs e o mesmo estado de publicação.
- Soluções antigas entram como ofertas **despublicadas**: revise link, plataforma, parâmetro de rastreio e ID do produto antes de publicar.
- Tabelas financeiras e de decisão antigas **não** são importadas, porque os dados eram simulados ou inconsistentes. Elas continuam no banco, só para consulta.

## Ideias guardadas para depois (não implementadas)

- **Programa de parceiros com repasse de comissão.** Só faz sentido com vendas reais conciliadas. O registro de vendas da v2 já é a base certa.
- **Tráfego pago automatizado** (Meta e Google). Só depois de saber quais ofertas têm ganho por clique positivo, e com orçamento aprovado por uma pessoa.
- **Webhooks nativos** de Eduzz, Monetizze, Kiwify e Awin. Até lá, use o webhook genérico (via Make, Zapier ou n8n), o lançamento manual ou o CSV.
