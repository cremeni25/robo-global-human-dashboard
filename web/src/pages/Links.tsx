// "Link na bio" para Instagram, TikTok, YouTube: roboglobal.com.br/links?utm_source=instagram
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
import { carregarTemas } from "../problemas";
import type { Tema } from "../problemas";

const copy = {
  pt: { title: "Robô Global", lead: "Natação e triathlon: o que você quer resolver no seu treino hoje?", all: "Ver todos os temas" },
  en: { title: "Robô Global", lead: "Swimming and triathlon: what do you want to solve in your training today?", all: "See all topics" },
  es: { title: "Robô Global", lead: "Natación y triatlón: ¿qué quieres resolver hoy en tu entrenamiento?", all: "Ver todos los temas" },
};

export default function Links() {
  const { lang } = useLanguage(); const t = copy[lang];
  const [temas, setTemas] = useState<Tema[]>([]);
  useEffect(() => { carregarTemas().then(setTemas).catch(() => setTemas([])); }, []);
  return <div className="rg-links"><div className="rg-links-inner">
    <span className="rg-brand-icon" aria-hidden="true">✳</span>
    <h1>{t.title}</h1><p>{t.lead}</p>
    {temas.flatMap(tm => tm.problemas.map(p => <Link key={p.slug} className="rg-links-btn" to={"/problema/" + p.slug}>
      <small>{tm.icone} {tm.titulo[lang]}</small>{p.titulo[lang]}</Link>))}
    <Link className="rg-links-btn rg-links-main" to="/">{t.all}</Link>
  </div></div>;
}
