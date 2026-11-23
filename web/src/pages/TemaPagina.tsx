import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
import { carregarTemas } from "../problemas";
import type { Tema } from "../problemas";

const copy = {
  pt: { back: "Todos os temas", lead: "Escolha a situação que mais combina com você.", see: "Ver soluções", loading: "Carregando…", missing: "Este tema não está disponível no momento.", error: "Não foi possível carregar agora." },
  en: { back: "All topics", lead: "Pick the situation that fits you best.", see: "See solutions", loading: "Loading…", missing: "This topic isn't available right now.", error: "We couldn't load this right now." },
  es: { back: "Todos los temas", lead: "Elige la situación que más se parece a la tuya.", see: "Ver soluciones", loading: "Cargando…", missing: "Este tema no está disponible ahora.", error: "No pudimos cargar ahora." },
};

export default function TemaPagina() {
  const { slug = "" } = useParams(); const { lang } = useLanguage(); const t = copy[lang];
  const [temas, setTemas] = useState<Tema[] | null>(null);
  const [erro, setErro] = useState(false);
  useEffect(() => {
    const c = new AbortController();
    carregarTemas(c.signal).then(setTemas).catch(() => { if (!c.signal.aborted) setErro(true); });
    return () => c.abort();
  }, []);
  const tema = temas?.find(x => x.slug === slug);
  useEffect(() => { if (tema) document.title = tema.titulo[lang] + " · Robô Global"; return () => { document.title = "Robô Global · Soluções para o dia a dia"; }; }, [tema, lang]);

  return <div className="rg-store">
    <section className="rg-store-hero"><div className="rg-store-inner">
      <Link className="rg-voltar" to="/">← {t.back}</Link>
      {tema && <><h1><span aria-hidden="true">{tema.icone}</span> {tema.titulo[lang]}</h1><p>{t.lead}</p></>}
    </div></section>
    <div className="rg-store-inner rg-store-body">
      {erro ? <p role="alert">{t.error}</p>
        : !temas ? <p className="rg-store-loading" role="status">{t.loading}</p>
        : !tema ? <p role="status">{t.missing}</p>
        : <div className="rg-problemas">{tema.problemas.map(p =>
          <Link key={p.slug} className="rg-problema-card" to={"/problema/" + p.slug}>
            <strong>{p.titulo[lang]}</strong>
            <span>{p.resumo[lang]}</span>
            <em>{t.see} →</em>
          </Link>)}</div>}
    </div>
  </div>;
}
