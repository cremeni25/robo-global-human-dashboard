# Operação: do deploy à primeira receita real

O Robô Global não "fica rico sozinho". Ele organiza, rastreia e aponta para onde o esforço humano rende mais. Este é o caminho prático.

## 1. Colocar no ar (uma vez, cerca de 1 hora)

1. **Banco:** no Supabase, em Project Settings → Database, copie a *connection string* (modo **Session pooler**).
2. **Render:** crie um Blueprint apontando para este repositório (`render.yaml`). Ele cria a API e o site. Preencha:
   - `DATABASE_URL`: a connection string do passo 1;
   - `ADMIN_TOKENS`: `seu-nome:um-token-longo-e-aleatorio` (um par por pessoa da operação, separados por vírgula);
   - `HOTMART_HOTTOK`: preencha no passo 4.
   - Ou então substitua o serviço `robo-global-api-v2` atual por esta API. Assim o domínio e o site antigo continuam funcionando durante a troca.
3. **Catálogo:** depois do primeiro start da API (que cria as tabelas), rode `api/sql/002_importar_catalogo_legado.sql` no SQL Editor do Supabase.
4. **Hotmart:** em Ferramentas → Webhook, cadastre `https://SUA-API/webhooks/hotmart`, versão 2.0, com os eventos de compra (aprovada, completa, reembolsada, chargeback, cancelada). Copie o *hottok* para `HOTMART_HOTTOK`.
5. **Domínio:** aponte `roboglobal.com.br` para o site e confira se ele está em `CORS_ORIGINS`.
6. Abra `https://SEU-SITE/admin` e entre com seu token.

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
