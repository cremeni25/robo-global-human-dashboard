import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
import { carregarTemas } from "../problemas";
import type { Tema } from "../problemas";

const copy = {
  pt: { title: "O que você quer resolver hoje?",
    lead: "Escolha um tema e encontre o seu caso. Para cada um, explicamos o que considerar e indicamos três boas opções.",
    loading: "Carregando…", error: "Não foi possível carregar agora. Tente de novo em instantes." },
  en: { title: "What do you want to solve today?",
    lead: "Pick a topic and find your case. For each one, we explain what to consider and suggest three good options.",
    loading: "Loading…", error: "We couldn't load this right now. Please try again shortly." },
  es: { title: "¿Qué quieres resolver hoy?",
    lead: "Elige un tema y encuentra tu caso. Para cada uno, te explicamos qué tener en cuenta y te sugerimos tres buenas opciones.",
    loading: "Cargando…", error: "No pudimos cargar ahora. Inténtalo de nuevo en unos instantes." },
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

  return <div className="rg-store rg-inicio">
    <section className="rg-store-hero"><div className="rg-store-inner">
      <h1>{t.title}</h1><p>{t.lead}</p>
    </div></section>
    <div className="rg-store-inner rg-store-body">
      {erro ? <p className="rg-catalog-feedback" role="alert">{t.error}</p>
        : !temas ? <p className="rg-store-loading" role="status">{t.loading}</p>
        : <nav className="rg-temas" aria-label={t.title}>
          {temas.map(tm => <Link key={tm.slug} className="rg-tema-botao" to={"/tema/" + tm.slug}>
            <span className="rg-tema-icone" aria-hidden="true">{tm.icone}</span>
            <strong>{tm.titulo[lang]}</strong>
            <span className="rg-tema-casos">{tm.problemas.map(p => (p.curto || p.titulo)[lang]).join(" · ")}</span>
          </Link>)}
        </nav>}
    </div>
  </div>;
}
