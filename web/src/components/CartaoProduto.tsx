import { linkSaida, tituloOferta } from "../rastreio";

export type Produto = { id: string; title: string; image_url?: string; price?: number | null; currency?: string; provider?: string; url: string; translations?: Record<string, { title?: string } | undefined> };
const locais = { pt: "pt-BR", en: "en-US", es: "es-ES" } as const;
const rotulo = { pt: "Ver na loja", en: "View in store", es: "Ver en la tienda" } as const;

export default function CartaoProduto({ p, lang, dorId }: { p: Produto; lang: "pt" | "en" | "es"; dorId?: string }) {
  const preco = p.price != null && p.currency
    ? new Intl.NumberFormat(locais[lang], { style: "currency", currency: p.currency }).format(p.price) : "";
  const titulo = tituloOferta(p, lang);
  return <a className="rg-card" href={linkSaida(p.url, dorId)} target="_blank" rel="noopener noreferrer sponsored" title={titulo}>
    <div className="rg-card-img">{p.image_url && <img src={p.image_url} alt="" loading="lazy" referrerPolicy="no-referrer"
      onError={e => { e.currentTarget.style.visibility = "hidden"; }} />}</div>
    <div className="rg-card-body">
      <span className="rg-card-title">{titulo}</span>
      {preco && <strong className="rg-card-price">{preco}</strong>}
      <span className="rg-card-store">{p.provider?.replace(/\s+(WW|BR|Many Geos)$/i, "")} · {rotulo[lang]} ↗</span>
    </div>
  </a>;
}
