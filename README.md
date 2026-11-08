# Robô Global v2

Sistema para **ligar necessidades reais de pessoas a soluções que geram receita**, com tudo medido, rastreado e auditável. A máquina mede e recomenda; **uma pessoa decide**.

Esta versão substitui os 7 repositórios anteriores por **um único sistema limpo**. O que valia a pena foi reaproveitado, e o que estava duplicado, simulado ou sem uso foi retirado. O que saiu, o que ficou e por quê está em [docs/MIGRACAO.md](docs/MIGRACAO.md).

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
  app/inteligencia.py   métricas, demanda e recomendações explicáveis
  app/routers/          public.py, webhooks.py, admin.py
  sql/                  001_schema.sql (gerado) e 002_importar_catalogo_legado.sql
  tests/                16 testes de ponta a ponta (SQLite e PostgreSQL)
web/    React + Vite: site público (PT, EN, ES) e painel de operação em /admin
docs/   MIGRACAO.md (o que mudou) e OPERACAO.md (como operar e monetizar)
render.yaml             deploy da API e do site no Render
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
