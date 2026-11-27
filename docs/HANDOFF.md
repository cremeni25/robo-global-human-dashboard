# HANDOFF — Robô Global (atualizado em 27/11/2026)

## Pronto e funcionando (no ar)
- Site só de **natação e triathlon**: 5 temas, 13 dores, 39 produtos (Speedo, Arena, Hammerhead,
  Garmin, Orca, Zone3, Giro, Mormaii, Mizuno, Asics, Max Titanium...). Início → tema → dor, com
  botões de voltar; abre em <0,1 s após a 1ª carga (catálogo guardado no aparelho, `rg_catalogo_v2`).
- Amazon em todos os 39 produtos (busca do modelo + `tag=roboglobal-20`, sem foto/preço por regra
  do programa). Mercado Livre em 8 dos 39 (links reaproveitados).
- Rastreio de cliques por canal (`/r/{id}` + utm_*), painel `/admin` (acesso lembrado no aparelho):
  Geral, Divulgação (links por canal), Páginas de problema, Público (inscritos e feedback), Custo IA.
- Achados da semana (WhatsApp/e-mail com consentimento LGPD) + `/cancelar`; "Isso te ajudou?".
- Página Sobre com Cremeni e AGP Intelligence; rodapé "Uma iniciativa Cremeni" + aviso Amazon.
- Ícone próprio, manifesto, prévia de compartilhamento. 44 testes passando (SQLite e PostgreSQL).

## Em andamento / onde parou
- **Links do Mercado Livre para 31 produtos novos**: o dono deve gerar em 2 rodadas (16 + 15) no
  Gerador de links do ML ("Links completos") e colar. Lista na última resposta da sessão anterior e
  reprodutível: itens de `CURADORIA` cuja `busca` não está em `LINKS_ML`, URL
  `https://lista.mercadolivre.com.br/<busca-sem-acento-com-hifens>`. Ao receber, adicionar em
  `api/app/curadoria_ml.py` (chave = `busca`), na MESMA ordem da lista.
- **API do Mercado Livre (preço/foto/frete)**: bloqueada — DevCenter diz "No tenés permiso para crear
  aplicaciones". Dono vai pedir liberação à OpenPlatform (texto já fornecido).
- **Produtos digitais (Hotmart/Eduzz/Monetizze)**: dono quer escolha 100% automática. Em 27/11/2026
  o dono instalou o Claude in Chrome (extensão, painel lateral) e está rodando lá um roteiro pronto:
  buscar no Mercado de Afiliados da Hotmart (natação, triathlon, corrida, endurance, psicologia do
  esporte), até 8 produtos com nota ≥ 4, autor com credencial, sem promessa milagrosa; afiliar-se e
  devolver tabela (nome, autor, ID, preço, comissão, status, hotlink). Ao receber a tabela: cadastrar
  no site e mapear postback. A sessão na nuvem não alcança o Chrome do dono (sem Remote Control).
  Conta Hotmart: a já existente (iniciais "CI"), que já promove afiliados — decisão do dono. Eduzz/Monetizze: ligar o postback quando houver 1º produto afiliado
  (mapear pelo evento de teste real; Hotmart já integrado).

## Próximos passos (prioridade)
0. Receber a tabela de afiliações da Hotmart (Claude in Chrome) e cadastrar os produtos no site.
1. Receber e cadastrar os 31 links do ML; publicar e conferir.
2. Roteiro semanal da social media focado em natação/triathlon (links com utm por canal; "#publi").
3. Produtos digitais de natação/triathlon/psicologia do esporte (afiliação + postbacks Eduzz/Monetizze).
4. Calendário de provas e calculadoras (ritmo/100 m, conversão piscina 25/50 m) — motor de retorno.
5. Quando ML liberar API / Amazon liberar após vendas: preço, foto, "menor preço 30 dias", alertas,
   comparação entre lojas; cupons do ML no site.

## Decisões e motivos
- Nicho único esporte (natação+triathlon): público apaixonado, compra recorrente, autoridade Cremeni/AGP.
- Curadoria manual em vez de catálogo automático: a seleção por palavra-chave trazia itens absurdos
  (cara de golpe). Lojas da Admitad (estrangeiras/desconhecidas) fora do site.
- Links para a BUSCA do modelo (não anúncio): nunca quebram; outras compras na sessão também comissionam.
- Importação dos catálogos das redes desligada (`IMPORTAR_CATALOGOS=0`): deixava o banco lento.
- Sem página sobre comissão (escolha do dono); só a linha obrigatória no rodapé.
- Carraro e Geekbuying descartados (não agregam / pouco conhecidos no Brasil).

## Problemas conhecidos e tentativas
- Amazon: sem preço/foto até haver vendas (API oficial). Conta precisa de 3 vendas em 180 dias (desde 23/11/2026).
- ML DevCenter sem permissão (ver acima). Não consigo abrir meli.la/ML/imagens das lojas pelo ambiente
  da sessão (proxy) — o dono confere no celular.
- Token Awin retorna 401 (Awin sem uso no foco atual).
- Serviços antigos no Render não suspensos (core-v1, cms, dashboard, landing, robo-global-api web);
  webhook Hotmart ainda aponta para o core-v1 → mudar para `https://api.roboglobal.com.br/webhooks/hotmart`.

## Integrações e configurações (sem segredos)
- Render: `robo-global-api-v2` (srv-d4q9s2chg0os738617o0, api.roboglobal.com.br) e
  `robo-global-frontend` (srv-d5o47smmcj7s73ajdqi0, www.roboglobal.com.br); deploy do `main`.
- Supabase: projeto `lnftqpxrnuushzkuuete` (tabelas `rg_*`, ex.: rg_ofertas, rg_cliques,
  rg_inscricoes, rg_feedback, rg_config com `problemas_escolhas`, `catalogo_ia`).
- Variáveis no Render (só nomes): ADMIN_TOKENS, DATABASE_URL, ANTHROPIC_API_KEY, HOTMART_HOTTOK,
  EDUZZ_WEBHOOK_*, MONETIZZE_WEBHOOK_*, ADMITAD_*, AWIN_*. Configs de código: AMAZON_TAG (padrão
  roboglobal-20), LOJAS_CONFIAVEIS (vazio), IMPORTAR_CATALOGOS=0, PROBLEMAS_AUTOMATICO=0,
  IA_TETO_TESTE_USD=5, IA_FRACAO_COMISSAO=0.10.
- Hotmart: conta já existente (iniciais "CI"), usada por decisão do dono.
- Afiliados: Amazon Associados `roboglobal-20` (dados fiscais PF concluídos); Mercado Livre
  etiqueta `naan132272` (identidade validada; comissões no Mercado Pago da conta Anderson).

## Repositórios
- `cremeni25/robo-global-human-dashboard`: único repositório ativo (api + web + docs).
- Legado: `cremeni25/robo` (branch `rebuild/core-v1`, serviço core-v1) — não usado no site atual.
