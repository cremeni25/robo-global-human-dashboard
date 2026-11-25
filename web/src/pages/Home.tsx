import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
import { carregarTemas, catalogoImediato } from "../problemas";
import type { Tema } from "../problemas";
import Achados from "../components/Achados";
import { ultimoTema } from "../rastreio";

const copy = {
  pt: { title: "O que você quer resolver no seu treino hoje?",
    lead: "Natação e triathlon. Escolha um tema e encontre o seu caso: explicamos o que considerar e indicamos três boas opções de marcas conhecidas.",
    loading: "Carregando…", error: "Não foi possível carregar agora. Tente de novo em instantes.", continuar: "Continuar em" },
  en: { title: "What do you want to solve in your training today?",
    lead: "Swimming and triathlon. Pick a topic and find your case: we explain what to consider and suggest three good options from trusted brands.",
    loading: "Loading…", error: "We couldn't load this right now. Please try again shortly.", continuar: "Continue with" },
  es: { title: "¿Qué quieres resolver hoy en tu entrenamiento?",
    lead: "Natación y triatlón. Elige un tema y encuentra tu caso: te explicamos qué tener en cuenta y te sugerimos tres buenas opciones de marcas conocidas.",
    loading: "Cargando…", error: "No pudimos cargar ahora. Inténtalo de nuevo en unos instantes.", continuar: "Continuar en" },
};

export default function Home() {
  const { lang } = useLanguage(); const t = copy[lang];
  const [temas, setTemas] = useState<Tema[] | null>(() => catalogoImediato()?.temas ?? null);
  const [erro, setErro] = useState(false);
  useEffect(() => {
    const c = new AbortController();
    carregarTemas(c.signal).then(setTemas).catch(() => { if (!c.signal.aborted) setErro(true); });
    return () => c.abort();
  }, []);

  const ultimo = temas?.find(x => x.slug === ultimoTema());
  return <div className="rg-store rg-inicio">
    <section className="rg-store-hero"><div className="rg-store-inner">
      <h1>{t.title}</h1><p>{t.lead}</p>
      {ultimo && <Link className="rg-voltar rg-continuar" to={"/tema/" + ultimo.slug}>{t.continuar} {ultimo.icone} {ultimo.titulo[lang]} →</Link>}
    </div></section>
    <div className="rg-store-inner rg-store-body">
      {erro ? <p className="rg-catalog-feedback" role="alert">{t.error}</p>
        : !temas ? <p className="rg-store-loading" role="status">{t.loading}</p>
        : <nav className="rg-temas" aria-label={t.title}>
          {temas.map(tm => <Link key={tm.slug} className={"rg-tema-botao" + (tm.slug === "presentes" ? " rg-tema-destaque" : "")} to={"/tema/" + tm.slug}>
            <span className="rg-tema-icone" aria-hidden="true">{tm.icone}</span>
            <strong>{tm.titulo[lang]}</strong>
            <span className="rg-tema-casos">{tm.problemas.map(p => (p.curto || p.titulo)[lang]).join(" · ")}</span>
          </Link>)}
        </nav>}
      <Achados origem="inicio" />
    </div>
  </div>;
}
