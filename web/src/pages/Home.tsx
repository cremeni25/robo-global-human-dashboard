import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
import { carregarTemas } from "../problemas";
import type { Tema } from "../problemas";

const copy = {
  pt: { kicker: "ROBÔ GLOBAL", title: "Qual problema você quer resolver hoje?",
    lead: "Escolha uma situação do seu dia a dia. A gente mostra o que vale considerar e três boas opções para resolver.",
    loading: "Carregando…", error: "Não foi possível carregar agora. Tente de novo em instantes.", see: "Ver soluções" },
  en: { kicker: "ROBÔ GLOBAL", title: "What problem do you want to solve today?",
    lead: "Pick an everyday situation. We show what's worth considering and three good options to solve it.",
    loading: "Loading…", error: "We couldn't load this right now. Please try again shortly.", see: "See solutions" },
  es: { kicker: "ROBÔ GLOBAL", title: "¿Qué problema quieres resolver hoy?",
    lead: "Elige una situación de tu día a día. Te mostramos qué tener en cuenta y tres buenas opciones para resolverla.",
    loading: "Cargando…", error: "No pudimos cargar ahora. Inténtalo de nuevo en unos instantes.", see: "Ver soluciones" },
};

export default function Home() {
  const { lang } = useLanguage(); const t = copy[lang];
  const [temas, setTemas] = useState<Tema[] | null>(null);
  const [erro, setErro] = useState(false);
  useEffect(() => {
    const c = new AbortController();
    carregarTemas(c.signal).then(setTemas).catch(() => { if (!c.signal.aborted) setErro(true); });
    return () => c.abort();
  }, []);

  useEffect(() => { // links como /#pet levam direto ao tema
    if (!temas || !window.location.hash) return;
    const el = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    if (el) setTimeout(() => el.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }, [temas]);

  return <div className="rg-store">
    <section className="rg-store-hero"><div className="rg-store-inner">
      <span className="rg-catalog-eyebrow">✳ {t.kicker}</span>
      <h1>{t.title}</h1><p>{t.lead}</p>
      {temas && temas.length > 1 && <nav className="rg-chips" aria-label={t.title}>
        {temas.map(tm => <a key={tm.slug} href={"#" + tm.slug}><span aria-hidden="true">{tm.icone}</span> {tm.titulo[lang]}</a>)}
      </nav>}
    </div></section>
    <div className="rg-store-inner rg-store-body">
      {erro ? <p className="rg-catalog-feedback" role="alert">{t.error}</p>
        : !temas ? <p className="rg-store-loading" role="status">{t.loading}</p>
        : temas.map(tm => <section className="rg-tema" key={tm.slug} id={tm.slug} aria-labelledby={"h-" + tm.slug}>
          <h2 id={"h-" + tm.slug}><span aria-hidden="true">{tm.icone}</span> {tm.titulo[lang]}</h2>
          <div className="rg-problemas">{tm.problemas.map(p =>
            <Link key={p.slug} className="rg-problema-card" to={"/problema/" + p.slug}>
              <strong>{p.titulo[lang]}</strong>
              <span>{p.resumo[lang]}</span>
              <em>{t.see} →</em>
            </Link>)}
          </div>
        </section>)}
    </div>
  </div>;
}
