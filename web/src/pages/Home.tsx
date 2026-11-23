import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { localizeEditorial } from "../catalogCopy";
import CartaoProduto from "../components/CartaoProduto";
import type { Produto } from "../components/CartaoProduto";
import { API_URL } from "../config";
import { useLanguage } from "../contexts/LanguageContext";
import { compartilhar } from "../rastreio";

type Editorial = { id: string; slug: string; title: string; description?: string; translations?: Record<string, { title?: string; description?: string }> };
type Secao = { dor: Editorial; nicho: Editorial; total: number; itens: Produto[] };
type Vitrine = { achados: Produto[]; secoes: Secao[] };

const copy = {
  pt: { kicker: "ACHADOS DE LOJAS PARCEIRAS", title: "Encontre o que você precisa, com preço de verdade.",
    lead: "Produtos de lojas parceiras verificadas, organizados pelo que você quer resolver. Você compra direto na loja.",
    search: "O que você procura hoje?", go: "Buscar", cheap: "Achados até R$ 50", cheapLead: "Coisas úteis que cabem no bolso.",
    all: "Ver tudo", share: "Compartilhar", loading: "Carregando achados…", error: "Não foi possível carregar a vitrine agora.",
    catalog: "Ver o catálogo completo", notice: "Os produtos são vendidos e entregues pelas lojas parceiras. Alguns links são de afiliado: podemos receber comissão sem custo extra para você. Preço e estoque são definidos pela loja." },
  en: { kicker: "FINDS FROM PARTNER STORES", title: "Find what you need, at real prices.",
    lead: "Products from verified partner stores, organized by what you want to solve. You buy directly from the store.",
    search: "What are you looking for today?", go: "Search", cheap: "Finds under R$ 50", cheapLead: "Useful things that fit your budget.",
    all: "See all", share: "Share", loading: "Loading finds…", error: "We couldn't load the showcase right now.",
    catalog: "See the full catalogue", notice: "Products are sold and shipped by partner stores. Some links are affiliate links: we may earn a commission at no extra cost to you. Price and stock are set by the store." },
  es: { kicker: "HALLAZGOS DE TIENDAS ASOCIADAS", title: "Encuentra lo que necesitas, con precios reales.",
    lead: "Productos de tiendas asociadas verificadas, organizados por lo que quieres resolver. Compras directo en la tienda.",
    search: "¿Qué buscas hoy?", go: "Buscar", cheap: "Hallazgos hasta R$ 50", cheapLead: "Cosas útiles que caben en tu bolsillo.",
    all: "Ver todo", share: "Compartir", loading: "Cargando hallazgos…", error: "No pudimos cargar la vitrina ahora.",
    catalog: "Ver el catálogo completo", notice: "Los productos los venden y envían las tiendas asociadas. Algunos enlaces son de afiliación: podemos recibir una comisión sin costo extra para ti. Precio y stock los define la tienda." },
};

export default function Home() {
  const { lang } = useLanguage(); const t = copy[lang]; const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [data, setData] = useState<Vitrine | null>(null);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    const c = new AbortController();
    fetch(API_URL + "/public/vitrine", { signal: c.signal, headers: { Accept: "application/json" } })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((b: Vitrine) => setData({ achados: b.achados || [], secoes: b.secoes || [] }))
      .catch(() => { if (!c.signal.aborted) setErro(true); });
    return () => c.abort();
  }, []);

  // Links de divulgação apontam para um tema (#tema-...): rola até ele quando a vitrine chega.
  useEffect(() => {
    if (!data || !window.location.hash) return;
    const el = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    if (el) setTimeout(() => el.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }, [data]);

  const buscar = (e: FormEvent) => { e.preventDefault(); navigate("/ofertas" + (q.trim() ? "?q=" + encodeURIComponent(q.trim()) : "")); };
  const pagina = () => window.location.origin + "/";

  return <div className="rg-store">
    <section className="rg-store-hero"><div className="rg-store-inner">
      <span className="rg-catalog-eyebrow">✳ {t.kicker}</span>
      <h1>{t.title}</h1><p>{t.lead}</p>
      <form className="rg-catalog-search rg-store-search" onSubmit={buscar} role="search">
        <span aria-hidden="true">⌕</span>
        <input aria-label={t.search} placeholder={t.search} value={q} onChange={e => setQ(e.target.value)} />
        <button type="submit">{t.go}</button>
      </form>
      {data && data.secoes.length > 0 && <nav className="rg-chips" aria-label={t.search}>
        {data.secoes.map(s => <a key={s.dor.id} href={"#tema-" + s.dor.id}>{localizeEditorial(s.nicho, lang).title}</a>)}
      </nav>}
    </div></section>

    <div className="rg-store-inner rg-store-body">
      {erro ? <div className="rg-catalog-feedback" role="alert"><p>{t.error}</p><Link className="rg-retry" to="/ofertas">{t.catalog} ↗</Link></div>
        : !data ? <p className="rg-store-loading" role="status">{t.loading}</p>
        : <>
          {data.achados.length > 0 && <section className="rg-shelf" aria-labelledby="achados">
            <header><div><h2 id="achados">{t.cheap}</h2><p>{t.cheapLead}</p></div>
              <button className="rg-share" onClick={() => compartilhar(t.cheap, pagina() + "#achados")}>{t.share}</button></header>
            <div className="rg-shelf-grid">{data.achados.map(p => <CartaoProduto key={p.id} p={p} lang={lang} />)}</div>
          </section>}
          {data.secoes.map(s => {
            const dor = localizeEditorial(s.dor, lang); const nicho = localizeEditorial(s.nicho, lang);
            return <section className="rg-shelf" key={s.dor.id} id={"tema-" + s.dor.id} aria-label={dor.title}>
              <header><div><span className="rg-shelf-kicker">{nicho.title}</span><h2>{dor.title}</h2>{dor.description && <p>{dor.description}</p>}</div>
                <div className="rg-shelf-actions">
                  <button className="rg-share" onClick={() => compartilhar(dor.title, pagina() + "#tema-" + s.dor.id)}>{t.share}</button>
                  <Link className="rg-shelf-all" to={"/ofertas?dor=" + s.dor.id}>{t.all} ({s.total.toLocaleString()}) ↗</Link>
                </div></header>
              <div className="rg-shelf-grid">{s.itens.map(p => <CartaoProduto key={p.id} p={p} lang={lang} dorId={s.dor.id} />)}</div>
            </section>;
          })}
          <p className="rg-store-more"><Link className="rg-retry" to="/ofertas">{t.catalog} ↗</Link></p>
        </>}
      <p className="rg-catalog-disclosure">{t.notice}</p>
    </div>
  </div>;
}
