# Fontes de receita do Robô Global

O Robô Global **não depende de uma rede**. O motor trata qualquer fonte de produtos da mesma forma: importa, organiza em dores, publica, rastreia o clique e registra a venda. Cada nova fonte soma catálogo e receita; se uma falhar, as outras continuam.

## 1. Já funcionam hoje, sem código novo

| Fonte | Como entra | O que você faz (uma vez) |
|---|---|---|
| **Awin** (BR e global) | Conector próprio: feed, afiliações e vendas automáticas | Gerar o token da API (o atual expirou) |
| **Qualquer rede com feed de produtos**: CJ Affiliate, Impact, Rakuten Advertising, Admitad, Webgains, Tradedoubler, Partnerize, Lomadee e outras | Conector universal (CSV, XML Google Shopping, YML) | Abrir a conta na rede, gerar a URL do feed e colar em **Painel → Aquisição → Fontes** |
| **Lojas e fornecedores parceiros** (empresas com estoque próprio que pagam comissão) | Conector universal: a loja exporta o feed do Google Shopping, que quase toda plataforma de e-commerce já gera (Shopify, Nuvemshop, VTEX, WooCommerce, Tray, Loja Integrada) | Combinar a comissão com a loja e receber a URL do feed |
| **Hotmart** e outros infoprodutos | Webhook Hotmart (vendas automáticas); oferta cadastrada uma vez | Afiliar-se ao produto |
| **Eduzz, Monetizze, Kiwify, Braip, Ticto** | Oferta cadastrada uma vez; vendas pelo webhook genérico (via Make, Zapier ou n8n) ou CSV | Afiliar-se e ligar o webhook uma vez |
| **Produto ou serviço próprio** | Oferta do tipo `produto_proprio` ou `servico` com link de checkout (a conta Stripe já existe) | Ter o produto ou serviço |
| **Venda de contatos (leads)** | Formulário "Avise-me" já capta pessoas com consentimento, por dor | Fechar parceria com empresas que pagam por contato |

## 2. Próximos conectores nativos (precisam de conta aprovada para testar)

| Fonte | Por que vale | Requisito |
|---|---|---|
| **Shopee Afiliados** (API aberta) | Milhões de produtos no Brasil e no Sudeste Asiático, link de afiliado gerado pela API | Conta de afiliado Shopee e credenciais da API |
| **AliExpress Portals** (API de afiliados) | Catálogo global, mais de 200 países | Conta no AliExpress Portals e app key na Open Platform |
| **Amazon Associados** | Marca de confiança, muitos países | A API de produtos só libera após as primeiras vendas pelo programa |
| **Mercado Livre Afiliados** | Maior marketplace da América Latina | Conta no programa de afiliados |
| **ClickBank, Digistore24** | Infoprodutos globais em inglês e alemão | Conta de afiliado |
| **CJdropshipping** (dropshipping) | Venda com margem própria e estoque de terceiros | Checkout próprio (Stripe), política de entrega e de troca. Você passa a ser o vendedor legal |

Cada conector nativo segue o mesmo molde do da Awin: importar o catálogo, confirmar a afiliação, sincronizar as vendas. Ele entra no mesmo ciclo automático.

## 3. Receita que não depende de venda

- **Anúncios no site** (Google AdSense, Ezoic, Mediavine): pagam por visita ou impressão, inclusive de quem não compra. Exigem páginas com conteúdo próprio, o que reforça a importância do agente de conteúdo.
- **Patrocínio de categoria ou dor:** uma marca paga para aparecer em destaque numa dor específica, com o espaço identificado como patrocinado.

## O que realmente limita a receita

1. **Contas aprovadas nas redes.** Cada conta é feita uma vez, com seus dados (CPF/CNPJ, banco, impostos). Nenhum sistema pode abrir contas em seu nome.
2. **Visitas.** Catálogo grande sem visitas não vende. O próximo agente recomendado é o **agente de conteúdo**: páginas úteis por dor, nos 3 idiomas, para atrair visitas orgânicas.
