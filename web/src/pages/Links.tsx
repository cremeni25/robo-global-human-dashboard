// Página de "link na bio" para Instagram, TikTok, YouTube, WhatsApp etc.
// A divulgadora usa roboglobal.com.br/links?utm_source=instagram e cada clique fica atribuído ao canal.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { localizeEditorial } from "../catalogCopy";
import { API_URL } from "../config";
import { useLanguage } from "../contexts/LanguageContext";

type Ed = { id: string; slug: string; title: string; translations?: Record<string, { title?: string }> };
const copy = {
  pt: { title: "Achados Robô Global", lead: "Escolha por onde começar:", cheap: "Achados até R$ 50", all: "Buscar qualquer produto" },
  en: { title: "Robô Global finds", lead: "Pick where to start:", cheap: "Finds under R$ 50", all: "Search any product" },
  es: { title: "Hallazgos Robô Global", lead: "Elige por dónde empezar:", cheap: "Hallazgos hasta R$ 50", all: "Buscar cualquier producto" },
};

export default function Links() {
  const { lang } = useLanguage(); const t = copy[lang];
  const [temas, setTemas] = useState<{ dor: Ed; nicho: Ed }[]>([]);
  useEffect(() => {
    fetch(API_URL + "/public/vitrine").then(r => r.json()).then(b => setTemas(b.secoes || [])).catch(() => setTemas([]));
  }, []);
  return <div className="rg-links">
    <div className="rg-links-inner">
      <span className="rg-brand-icon" aria-hidden="true">✳</span>
      <h1>{t.title}</h1><p>{t.lead}</p>
      <Link className="rg-links-btn rg-links-main" to="/#achados">{t.cheap}</Link>
      {temas.map(s => <Link key={s.dor.id} className="rg-links-btn" to={"/#tema-" + s.dor.id}>
        <small>{localizeEditorial(s.nicho, lang).title}</small>{localizeEditorial(s.dor, lang).title}</Link>)}
      <Link className="rg-links-btn" to="/ofertas">⌕ {t.all}</Link>
    </div>
  </div>;
}
