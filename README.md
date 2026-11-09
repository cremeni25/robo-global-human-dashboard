# Robô Global v2

Sistema para **ligar necessidades reais de pessoas a soluções que geram receita**, com tudo medido, rastreado e auditável. A máquina mede e recomenda; **uma pessoa decide**.

Esta versão une os 7 repositórios e o **Core V1** (motor de aquisição Awin, branch `rebuild/core-v1` do repositório `robo`) num **único sistema limpo**. O que valia a pena foi reaproveitado, e o que estava duplicado, simulado ou sem uso foi retirado. O que saiu, o que ficou e por quê está em [docs/MIGRACAO.md](docs/MIGRACAO.md).

## Escala sem cadastro manual

O motor de aquisição (`api/app/aquisicao.py`) roda sozinho a cada 6 horas:

1. importa os **feeds de produtos** das redes (milhares de itens; hoje, a Awin);
2. cria e atualiza **anunciantes** e produtos, e tira do ar o que saiu do feed;
3. liga produtos às dores por **regras de categoria** definidas uma vez;
4. confere na rede **de quais anunciantes você é afiliado aprovado**;
5. **sincroniza vendas e comissões** e atribui cada uma ao clique de origem.

A decisão humana é **uma por anunciante** (revisar os termos do programa) e **uma por categoria** (em qual dor ela aparece). Nunca é por produto.

## Como gera dinheiro

```
Pessoa  →  Nicho → Subnicho → Dor  →  Solução (oferta)  →  /r/{id}  →  parceiro ou checkout
                                 ↘ sem solução? "Avise-me" (lead com consentimento)
Venda   ←  webhook Hotmart / webhook genérico / lançamento manual / CSV   (idempotente)
Painel  →  métricas reais → recomendações (ESCALAR, PAUSAR, OTIMIZAR) → aprovação humana
```

A **oferta** não precisa ser de afiliado. O mesmo fluxo aceita quatro tipos:

| Tipo | Exemplo | Como a receita entra |
|---|---|---|
| `afiliado` | Curso na Hotmart, produto na Eduzz ou Awin | Comissão da plataforma |
| `produto_proprio` | E-book ou curso seu (checkout Hotmart como produtor, link de pagamento) | Venda direta |
| `servico` | Consultoria, atendimento, serviço local | Venda direta |
| `lead_parceiro` | Encaminhar interessados a uma empresa que paga por contato | Pagamento por lead |

Os **leads** de dores sem oferta mostram onde há demanda real ainda sem atendimento. O painel aponta essas dores como "oportunidade", e uma pessoa decide se busca um parceiro ou cria uma solução própria.

## Estrutura

```
api/    FastAPI + SQLAlchemy (PostgreSQL/Supabase ou SQLite local)
  app/main.py           criação do app
  app/models.py         modelo de dados único (tabelas rg_*)
  app/core.py           regras de publicação, pausa geral do sistema e auditoria
  app/conversions.py    registro financeiro idempotente e webhook Hotmart
  app/aquisicao.py      ciclo automático: feeds, anunciantes, regras, afiliações, vendas
  app/conectores/       conectores de redes (awin.py, vindo do Core V1)
  app/migracao_legado.py  importa uma vez os dados antigos (sql/002 e sql/003)
  app/inteligencia.py   métricas, demanda e recomendações explicáveis
  app/routers/          public.py, webhooks.py, admin.py
  sql/                  001_schema.sql (gerado), 002 (catálogo legado), 003 (Core V1)
  tests/                22 testes de ponta a ponta (SQLite e PostgreSQL)
web/    React + Vite: site público (PT, EN, ES) e painel de operação em /admin
docs/   MIGRACAO.md (o que mudou) e OPERACAO.md (como operar e monetizar)
render.yaml             configuração alvo dos 2 serviços que ficam no Render
```

## Rodar localmente

API:

```bash
cd api && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
```

```bash
ADMIN_TOKEN=um-token-local-bem-longo uvicorn app.main:app --reload
```

```bash
pytest
```

Site:

```bash
cd web && npm install && VITE_API_URL=http://localhost:8000 npm run dev
```

Abra http://localhost:5173. O painel fica em `/admin` e o acesso usa o token.

## Segurança: o que mudou

- Toda rota de escrita ou administrativa exige token. Sem token configurado, a área fica **fechada** (503).
- Toda ação humana fica registrada na auditoria (quem, o quê, quando).
- O link do parceiro nunca é exposto: a saída é sempre por `/r/{id}`, que valida a oferta, registra o clique e redireciona.
- Webhooks: token obrigatório. Reenvios não duplicam vendas, e reembolso ou chargeback atualizam a venda original.
- Nenhum IP é guardado; o clique tem apenas um hash anônimo do visitante (LGPD).
- Recomendações só têm efeito depois de aprovadas por uma pessoa.
- Um botão de pausa geral bloqueia toda saída para parceiros. As vendas continuam sendo registradas.

## Próximos passos

Veja [docs/OPERACAO.md](docs/OPERACAO.md): deploy, migração do catálogo, primeira oferta real e rotina semanal.
