# Operação: do deploy à primeira receita real

O Robô Global não "fica rico sozinho". Ele organiza, rastreia e aponta para onde o esforço humano rende mais. Este é o caminho prático.

## 1. Colocar no ar (troca nos serviços que já existem)

A migração reaproveita os serviços e domínios atuais. Nada novo é criado.

1. **robo-global-api-v2** (api.roboglobal.com.br):
   - repositório `cremeni25/robo-global-human-dashboard`, diretório raiz `api`;
   - build `pip install -r requirements.txt`; start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; health check `/health`;
   - variáveis: copiar `DATABASE_URL`, `HOTMART_HOTTOK`, `AWIN_PUBLISHER_ID` e `AWIN_FEED_URL` do core-v1; criar `ADMIN_TOKENS` (`seu-nome:token-longo`), `WEBHOOK_TOKEN` e `VISITOR_HASH_SALT`; gerar um **novo** `AWIN_API_TOKEN` (o atual é recusado pela Awin).
   - No primeiro start, a API cria as tabelas `rg_*` e **importa sozinha** o catálogo antigo e os dados do core-v1, uma única vez.
2. **robo-global-frontend** (www.roboglobal.com.br): mesmo repositório, diretório raiz `web`, build `npm ci && npm run build`, pasta publicada `dist`, `VITE_API_URL=https://api.roboglobal.com.br`.
3. **Hotmart:** o endereço antigo `/v1/webhooks/hotmart` continua aceito. Para usar o novo, troque para `https://api.roboglobal.com.br/webhooks/hotmart`.
4. Depois de conferir que tudo funciona: desligar **robo-global-core-v1**, **robo-global-api** (web e worker), **robo-global-cms**, **robo-global-dashboard** e **robo-global-landing**.
5. Abra `https://www.roboglobal.com.br/admin` e entre com seu token.

### Token da API Awin (passo único, 5 minutos)

1. Entre em **ui.awin.com** com sua conta de publisher.
2. No menu da conta, abra **API Credentials** (ou acesse `ui.awin.com/awin-api`).
3. Gere o token, copie e salve como `AWIN_API_TOKEN` no robo-global-api-v2.

Sem esse token, os produtos continuam sendo importados, mas o sistema não consegue confirmar afiliações nem trazer vendas da Awin. O painel mostra isso na aba **Aquisição**.

## 1.1 Escalar o catálogo (uma vez por anunciante, uma vez por categoria)

1. **Aquisição → Rodar agora** (ou aguarde o ciclo automático de 6 horas).
2. **Anunciantes:** os que mostram "aprovado" na coluna de afiliação são programas em que a Awin já aceitou você. Leia os termos do programa na Awin e clique em **aprovar termos**: todos os produtos dele vão ao ar.
3. **Mais anunciantes = mais produtos.** Na Awin, em *Advertisers → Join Programmes*, candidate-se a anunciantes do seu público. Cada aprovação deles libera o catálogo inteiro no próximo ciclo.
4. **Categorias → dores:** ligue cada categoria à dor certa. Produtos novos dessa categoria entram sozinhos daí em diante.
5. **Mais feeds:** em *Toolbox → Create-a-Feed*, inclua os anunciantes aprovados. Para vários feeds, use `AWIN_FEED_URLS` com uma lista JSON de URLs.

## 2. Cadastrar a primeira oferta que paga

1. Na plataforma (Hotmart, por exemplo), afilie-se a um produto **que resolve uma dor que já existe no catálogo** e copie seu link de afiliado.
2. No painel, vá em **Ofertas → Nova oferta**:
   - link de destino = seu link de afiliado;
   - plataforma = `hotmart`, parâmetro de rastreio = `sck` (a Hotmart devolve esse valor no webhook, e assim a venda é ligada ao clique);
   - ID do produto = o ID na Hotmart (serve de reserva para atribuir a venda quando não há clique);
   - descrição honesta, sem promessa de resultado.
3. Em **Catálogo**, publique nicho, subnicho e dor, depois **vincule** a oferta à dor. Em **Ofertas**, publique a oferta.
4. Teste: navegue no site até a dor e clique em "Conhecer solução". Você deve cair na Hotmart com `sck=` no link, e o clique aparece na Visão geral.

**Outras formas de monetizar, no mesmo fluxo:**
- **Produto ou serviço próprio:** tipo `produto_proprio` ou `servico`, com link para seu checkout (Hotmart como produtor, link de pagamento ou WhatsApp comercial).
- **Lead para parceiro:** tipo `lead_parceiro`, com link para o formulário do parceiro que paga por contato.
- Vendas de plataformas sem webhook nativo entram pelo **webhook genérico** `/webhooks/conversao` (com `X-Webhook-Token`, via Make, Zapier ou n8n), pelo **lançamento manual** ou pela **importação de CSV** do relatório da plataforma.

## 3. Levar pessoas ao site

Sem visitas não há receita. O sistema mede cada canal: use links com UTM, por exemplo `https://SUA-API/r/{id-da-oferta}?utm_source=instagram&utm_campaign=post-emagrecer`.

- Conteúdo útil por dor (post, vídeo curto, artigo) apontando para a página da dor no site.
- Grupos e comunidades onde a dor aparece, sempre com transparência de que é indicação.
- Tráfego pago **só** para ofertas que o painel já mostrou com ganho por clique positivo, e com teto definido por você.

## 4. Rotina semanal (30 minutos)

1. **Visão geral:** leia as frases. Elas dizem o que aconteceu e o que falta.
2. **Vendas:** se alguma plataforma não envia webhook, importe o CSV ou lance as vendas. Reimportar não duplica.
3. Clique em **Analisar dados e gerar recomendações**:
   - **ESCALAR:** a oferta paga bem por clique. Aprovar sobe a prioridade dela; divulgue mais.
   - **OTIMIZAR:** tem cliques sem venda. Revise o texto, a dor vinculada ou troque a oferta.
   - **PAUSAR:** muitos cliques sem venda, ou reembolso alto. Aprovar tira a oferta do ar.
   - Rejeite o que não fizer sentido. Sua decisão e o motivo ficam na auditoria.
4. **Demanda por dor:** dores marcadas como **oportunidade** têm pessoas pedindo solução. Busque um produto para se afiliar ou crie uma oferta própria. Quando publicar, avise os leads daquela dor (exporte o CSV em **Leads**).

Os limites das recomendações se ajustam por variável de ambiente: `MIN_CLIQUES_DECISAO` (100), `EPC_ALVO` (0,50 por clique) e `TAXA_REEMBOLSO_MAX` (30%).

## 5. Quando crescer

| Sinal no painel | Próximo passo |
|---|---|
| Mais de uma plataforma com volume | Webhook nativo para ela (Eduzz, Kiwify…) |
| Ofertas com ganho por clique estável acima da meta | Tráfego pago com orçamento aprovado e medido por UTM |
| Muitos leads em uma dor sem oferta | Criar produto ou serviço próprio para essa dor |
| Pessoas querendo divulgar | Programa de parceiros com repasse, a partir das vendas já conciliadas |
| Visitas de fora do Brasil | Ofertas por mercado e idioma (campos `market` e `language` já existem) |
