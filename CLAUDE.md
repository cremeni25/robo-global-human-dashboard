# Robô Global

## O que é
Guia de compras para **natação e triathlon** (uma iniciativa **Cremeni**). O visitante escolhe um
tema → um caso ("dor") → vê "Antes de escolher" + **3 opções** (para começar / melhor custo-benefício /
mais completa) de marcas conhecidas → compra na loja parceira. Receita = comissão de afiliado.
Site: https://www.roboglobal.com.br · API: https://api.roboglobal.com.br · Painel: /admin

## Como funciona
- Curadoria fixa em código: `api/app/curadoria.py` (produtos, motivos PT/EN/ES, busca na Amazon com
  `tag=roboglobal-20`) e `api/app/curadoria_ml.py` (links do Mercado Livre por termo de busca, etiqueta
  `naan132272`, gerados pelo dono no "Gerador de links" do ML). Aplicada na inicialização (idempotente).
- Temas e textos das dores: `api/app/problemas.py` (TEMAS, CURTOS). Páginas ficam prontas na memória.
- Todo clique passa por `/r/{id}` (registra canal utm_* e redireciona).
- Público: `/public/catalogo` (tudo de uma vez; o site guarda no aparelho), inscrições nos achados da
  semana (`/public/inscricoes`, `/cancelar`), "Isso te ajudou?" (`/public/feedback`).

## Stack e pastas
- `api/` FastAPI + SQLAlchemy 2 (Python 3.12 no Render), PostgreSQL (Supabase). Testes em `api/tests`.
- `web/` React 19 + Vite + TypeScript (PT/EN/ES). Páginas em `web/src/pages`.
- `render.yaml` (Render: robo-global-api-v2 e robo-global-frontend, deploy automático do `main`).
- `docs/` operação, fontes de receita, migração e HANDOFF.

## Comandos
- Testes API: `cd api && pip install -r requirements-dev.txt && python -m pytest -q`
  (PostgreSQL: `TEST_DATABASE_URL=postgresql+psycopg://... python -m pytest -q`)
- Frontend: `cd web && npm install && npx tsc --noEmit -p . && npm run build`
- Fluxo de publicação: branch de trabalho → PR → merge no `main` → Render publica sozinho.

## Regras e preferências do dono (Anderson)
- Responder em português do Brasil, direto, sem idas e vindas; verificar sozinho (não pedir "clique e me avise").
- Automação máxima; ações humanas só quando inevitáveis e uma única vez.
- Nicho único: **natação e triathlon** (esporte). Marca é só "Robô Global". Pode citar Cremeni (não
  "Cremeni Alimentos") e AGP Intelligence (sistema exclusivo de clubes; nunca oferecer ao público).
- Só marcas conhecidas e lojas confiáveis; nada de produto duvidoso ou promessa milagrosa.
- Confiança vem da experiência, não de falar de comissão: só uma linha discreta no rodapé
  (o aviso de Associado da Amazon é obrigatório).
- Tudo na conta pessoal **Anderson** (não usar a conta CREMENI nas plataformas).
- Nunca pedir/mostrar senhas ou chaves no chat; segredos só no Render (Environment). Ler só nomes.
- Nenhum acesso para terceiros (a social media não recebe senha nem acesso, nem de leitura).
- Custos de IA amarrados a vendas (teto de teste US$ 5 + 10% das comissões).
- Não usar Meta Ads. Não fazer cashback/recompensa por compra (proibido pela Amazon); sorteio exige autorização.
- Não remover nem suspender serviços do Render sem o dono.

Ao final de cada etapa, atualize docs/HANDOFF.md e faça commit e push.
