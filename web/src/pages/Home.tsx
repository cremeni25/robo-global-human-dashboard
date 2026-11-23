import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
import { carregarTemas } from "../problemas";
import type { Tema } from "../problemas";

const copy = {
  pt: { kicker: "ROBÔ GLOBAL", title: "Qual problema você quer resolver hoje?",
    lead: "Escolha uma área. A gente mostra situações do dia a dia, o que vale considerar e três boas opções para resolver.",
    loading: "Carregando…", error: "Não foi possível carregar agora. Tente de novo em instantes.", situacoes: (n: number) => n === 1 ? "1 situação" : `${n} situações` },
  en: { kicker: "ROBÔ GLOBAL", title: "What problem do you want to solve today?",
    lead: "Pick an area. We show everyday situations, what's worth considering and three good options to solve them.",
    loading: "Loading…", error: "We couldn't load this right now. Please try again shortly.", situacoes: (n: number) => n === 1 ? "1 situation" : `${n} situations` },
  es: { kicker: "ROBÔ GLOBAL", title: "¿Qué problema quieres resolver hoy?",
    lead: "Elige un área. Te mostramos situaciones del día a día, qué tener en cuenta y tres buenas opciones para resolverlas.",
    loading: "Cargando…", error: "No pudimos cargar ahora. Inténtalo de nuevo en unos instantes.", situacoes: (n: number) => n === 1 ? "1 situación" : `${n} situaciones` },
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
      <span className="rg-catalog-eyebrow">✳ {t.kicker}</span>
      <h1>{t.title}</h1><p>{t.lead}</p>
    </div></section>
    <div className="rg-store-inner rg-store-body">
      {erro ? <p className="rg-catalog-feedback" role="alert">{t.error}</p>
        : !temas ? <p className="rg-store-loading" role="status">{t.loading}</p>
        : <nav className="rg-temas" aria-label={t.title}>
          {temas.map(tm => <Link key={tm.slug} className="rg-tema-botao" to={"/tema/" + tm.slug}>
            <span className="rg-tema-icone" aria-hidden="true">{tm.icone}</span>
            <strong>{tm.titulo[lang]}</strong>
            <small>{t.situacoes(tm.problemas.length)} →</small>
          </Link>)}
        </nav>}
    </div>
  </div>;
}
