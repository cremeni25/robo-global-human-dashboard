// "Isso te ajudou?": ouvir quem usa. Sem dado pessoal; uma resposta por página neste aparelho.
import { useState } from "react";
import { API_URL } from "../config";
import { useLanguage } from "../contexts/LanguageContext";

const copy = {
  pt: { q: "Isso te ajudou?", sim: "Sim", nao: "Não", obrigado: "Obrigado! Sua resposta melhora o Robô Global.",
    falta: "O que faltou? Ou qual problema você quer que a gente resolva?", ph: "Conte em poucas palavras (opcional)", enviar: "Enviar" },
  en: { q: "Was this helpful?", sim: "Yes", nao: "No", obrigado: "Thank you! Your answer makes Robô Global better.",
    falta: "What was missing? Or which problem should we solve next?", ph: "Tell us briefly (optional)", enviar: "Send" },
  es: { q: "¿Te ayudó?", sim: "Sí", nao: "No", obrigado: "¡Gracias! Tu respuesta mejora Robô Global.",
    falta: "¿Qué faltó? ¿O qué problema quieres que resolvamos?", ph: "Cuéntanos en pocas palabras (opcional)", enviar: "Enviar" },
};

function jaRespondeu(p: string) { try { return localStorage.getItem("rg_ajudou_" + p) === "1"; } catch { return false; } }

export default function Ajudou({ pagina }: { pagina: string }) {
  const { lang } = useLanguage(); const t = copy[lang];
  const [etapa, setEtapa] = useState<"pergunta" | "detalhe" | "fim">(() => jaRespondeu(pagina) ? "fim" : "pergunta");
  const [util, setUtil] = useState<boolean | null>(null);
  const [texto, setTexto] = useState("");

  const enviar = (u: boolean | null, sugestao: string) => {
    fetch(API_URL + "/public/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pagina, util: u, sugestao, language: lang }) }).catch(() => undefined);
    try { localStorage.setItem("rg_ajudou_" + pagina, "1"); } catch { /* sem armazenamento */ }
  };

  if (etapa === "fim") return <p className="rg-ajudou rg-ajudou-fim" role="status">✓ {t.obrigado}</p>;
  return <section className="rg-ajudou" aria-label={t.q}>
    {etapa === "pergunta" ? <>
      <strong>{t.q}</strong>
      <div className="rg-ajudou-botoes">
        <button type="button" onClick={() => { setUtil(true); enviar(true, ""); setEtapa("detalhe"); }}>👍 {t.sim}</button>
        <button type="button" onClick={() => { setUtil(false); setEtapa("detalhe"); }}>👎 {t.nao}</button>
      </div>
    </> : <form onSubmit={e => { e.preventDefault(); if (util === false || texto.trim()) enviar(util === false ? false : null, texto.trim()); setEtapa("fim"); }}>
      <label htmlFor={"falta-" + pagina}>{util ? t.obrigado + " " : ""}{t.falta}</label>
      <textarea id={"falta-" + pagina} maxLength={500} rows={2} placeholder={t.ph} value={texto} onChange={e => setTexto(e.target.value)} />
      <button className="rg-retry" type="submit">{t.enviar}</button>
    </form>}
  </section>;
}
