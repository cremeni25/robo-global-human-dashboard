import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
import { carregarProblema } from "../problemas";
import type { Problema as P } from "../problemas";
import { compartilhar, lembrarTema, linkSaida, tituloOferta } from "../rastreio";
import Achados from "../components/Achados";
import Ajudou from "../components/Ajudou";

const copy = {
  pt: { consider: "Antes de escolher", picks: "Três boas opções", go: "Ver na loja", share: "Compartilhar", back: "Ver outros problemas", voltar: "Voltar para",
    loading: "Carregando…", missing: "Esta página não está disponível no momento.", error: "Não foi possível carregar agora.", store: "Vendido e entregue por", amazon: "Ver preço na Amazon", onAmazon: "Disponível na Amazon.com.br", na: "Ver na", ambas: "Disponível na Amazon e no Mercado Livre", lojas: "Compare o preço nas duas lojas:" },
  en: { consider: "Before you choose", picks: "Three good options", go: "View in store", share: "Share", back: "See other problems", voltar: "Back to",
    loading: "Loading…", missing: "This page isn't available right now.", error: "We couldn't load this right now.", store: "Sold and shipped by", amazon: "See price on Amazon", onAmazon: "Available on Amazon.com.br", na: "View on", ambas: "Available on Amazon and Mercado Livre", lojas: "Compare the price at both stores:" },
  es: { consider: "Antes de elegir", picks: "Tres buenas opciones", go: "Ver en la tienda", share: "Compartir", back: "Ver otros problemas", voltar: "Volver a",
    loading: "Cargando…", missing: "Esta página no está disponible en este momento.", error: "No pudimos cargar ahora.", store: "Vendido y enviado por", amazon: "Ver precio en Amazon", onAmazon: "Disponible en Amazon.com.br", na: "Ver en", ambas: "Disponible en Amazon y Mercado Livre", lojas: "Compara el precio en las dos tiendas:" },
};
const locais = { pt: "pt-BR", en: "en-US", es: "es-ES" } as const;

export default function Problema() {
  const { slug = "" } = useParams(); const { lang } = useLanguage(); const t = copy[lang];
  const [p, setP] = useState<P | null | undefined>(undefined);
  const [erro, setErro] = useState(false);
  useEffect(() => {
    const c = new AbortController();
    setP(undefined); setErro(false);
    carregarProblema(slug, c.signal).then(setP).catch(() => { if (!c.signal.aborted) setErro(true); });
    return () => c.abort();
  }, [slug]);
  useEffect(() => { if (p) lembrarTema(p.tema); }, [p]);
  useEffect(() => { if (p) document.title = p.titulo[lang] + " · Robô Global"; return () => { document.title = "Robô Global · Soluções para o dia a dia"; }; }, [p, lang]);

  if (erro || p === null || p === undefined) return <div className="rg-store"><div className="rg-store-inner rg-store-body">
    <p role="status">{erro ? t.error : p === null ? t.missing : t.loading}</p>
    {(erro || p === null) && <Link className="rg-retry" to="/">← {t.back}</Link>}</div></div>;

  const preco = (v?: number | null, m?: string) => v != null && m ? new Intl.NumberFormat(locais[lang], { style: "currency", currency: m }).format(v) : "";
  return <div className="rg-store">
    <section className="rg-store-hero"><div className="rg-store-inner">
      <Link className="rg-voltar" to={"/tema/" + p.tema}>← {t.voltar} {p.tema_titulo[lang]}</Link>
      <h1>{p.titulo[lang]}</h1><p>{p.resumo[lang]}</p>
    </div></section>
    <div className="rg-store-inner rg-store-body rg-problema">
      <section className="rg-considerar" aria-labelledby="considerar">
        <h2 id="considerar">{t.consider}</h2>
        <ul>{p.considerar.map((c, i) => <li key={i}>{c[lang]}</li>)}</ul>
      </section>
      <section aria-labelledby="escolhas">
        <header className="rg-escolhas-head"><h2 id="escolhas">{t.picks}</h2>
          <button className="rg-share" onClick={() => compartilhar(p.titulo[lang], window.location.origin + "/problema/" + p.slug)}>{t.share}</button></header>
        <div className="rg-escolhas">{p.escolhas.map((e, i) => {
          const o = e.oferta; const loja = (o.provider || "").replace(/\s+(WW|BR|Many Geos)$/i, ""); const amazon = loja === "Amazon";
          return <article className="rg-escolha" key={o.id}>
            <span className="rg-nivel"><b aria-hidden="true">{i + 1}</b> {e.nivel[lang]}</span>
            {o.image_url && <div className="rg-escolha-img"><img src={o.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" onError={ev => { ev.currentTarget.style.visibility = "hidden"; }} /></div>}
            <h3 className={o.image_url ? "" : "rg-escolha-titulo"}>{tituloOferta(o, lang)}</h3>
            <p className="rg-motivo">{e.motivo[lang]}</p>
            {preco(o.price, o.currency) && <strong className="rg-card-price">{preco(o.price, o.currency)}</strong>}
            {(e.lojas?.length ?? 0) > 1 ? <>
              <small className="rg-loja">{t.lojas}</small>
              <div className="rg-lojas">{e.lojas!.map(l =>
                <a key={l.url} className={"rg-retry rg-escolha-go rg-loja-" + (l.loja === "Amazon" ? "amazon" : "ml")} href={linkSaida(l.url)} target="_blank" rel="noopener noreferrer sponsored">{l.loja} ↗</a>)}
              </div></>
            : <>
              {loja && <small className="rg-loja">{amazon ? t.onAmazon : t.store + " " + loja}</small>}
              <a className="rg-retry rg-escolha-go" href={linkSaida(o.url)} target="_blank" rel="noopener noreferrer sponsored">{amazon ? t.amazon : t.go} ↗</a>
            </>}
          </article>;
        })}</div>
      </section>
      <Ajudou pagina={p.slug} />
      <Achados origem={"problema:" + p.slug} />
      <p><Link className="rg-shelf-all" to={"/tema/" + p.tema}>← {t.voltar} {p.tema_titulo[lang]}</Link></p>
    </div>
  </div>;
}
