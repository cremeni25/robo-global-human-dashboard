// "Receba os achados da semana": o canal próprio do Robô Global com quem já confiou no site.
import { useState } from "react";
import type { FormEvent } from "react";
import { API_URL } from "../config";
import { useLanguage } from "../contexts/LanguageContext";
import { Link } from "react-router-dom";
import { canalAtual } from "../rastreio";

const copy = {
  pt: { title: "Receba os achados da semana", lead: "Toda semana, 3 soluções escolhidas a dedo para o dia a dia. Sem spam: você sai quando quiser.",
    whatsapp: "WhatsApp", email: "E-mail", phWa: "Seu WhatsApp com DDD", phEmail: "Seu e-mail",
    consent: "Aceito receber os achados da semana do Robô Global. Posso cancelar a qualquer momento em", sair: "roboglobal.com.br/cancelar",
    send: "Quero receber", sending: "Enviando…", ok: "Pronto! Você vai receber os próximos achados.", error: "Confira o contato e tente de novo." },
  en: { title: "Get the weekly picks", lead: "Every week, 3 hand-picked solutions for everyday life. No spam: leave whenever you want.",
    whatsapp: "WhatsApp", email: "Email", phWa: "Your WhatsApp number", phEmail: "Your email",
    consent: "I agree to receive Robô Global's weekly picks. I can unsubscribe anytime at", sair: "roboglobal.com.br/cancelar",
    send: "Sign me up", sending: "Sending…", ok: "Done! You'll get the next picks.", error: "Please check your contact and try again." },
  es: { title: "Recibe los hallazgos de la semana", lead: "Cada semana, 3 soluciones elegidas para el día a día. Sin spam: te das de baja cuando quieras.",
    whatsapp: "WhatsApp", email: "Correo", phWa: "Tu WhatsApp con código de área", phEmail: "Tu correo",
    consent: "Acepto recibir los hallazgos semanales de Robô Global. Puedo cancelar cuando quiera en", sair: "roboglobal.com.br/cancelar",
    send: "Quiero recibir", sending: "Enviando…", ok: "¡Listo! Recibirás los próximos hallazgos.", error: "Revisa el contacto e inténtalo de nuevo." },
};

export default function Achados({ origem }: { origem: string }) {
  const { lang } = useLanguage(); const t = copy[lang];
  const [canal, setCanal] = useState<"whatsapp" | "email">("whatsapp");
  const [contato, setContato] = useState("");
  const [consent, setConsent] = useState(false);
  const [website, setWebsite] = useState("");
  const [estado, setEstado] = useState<"idle" | "enviando" | "ok" | "erro">("idle");

  async function enviar(e: FormEvent) {
    e.preventDefault(); setEstado("enviando");
    try {
      const r = await fetch(API_URL + "/public/inscricoes", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ canal, contato, consent, language: lang, origem, utm_source: canalAtual(), website }) });
      setEstado(r.ok ? "ok" : "erro");
    } catch { setEstado("erro"); }
  }

  return <section className="rg-achados" aria-labelledby="achados-titulo">
    <h2 id="achados-titulo">✳ {t.title}</h2><p>{t.lead}</p>
    {estado === "ok" ? <p className="rg-achados-ok" role="status">✓ {t.ok}</p> :
    <form onSubmit={enviar}>
      <div className="rg-achados-canais" role="radiogroup" aria-label={t.title}>
        {(["whatsapp", "email"] as const).map(c => <button key={c} type="button" role="radio" aria-checked={canal === c}
          className={canal === c ? "on" : ""} onClick={() => { setCanal(c); setContato(""); }}>{t[c]}</button>)}
      </div>
      <div className="rg-achados-linha">
        <input required value={contato} onChange={e => setContato(e.target.value)}
          type={canal === "email" ? "email" : "tel"} inputMode={canal === "email" ? "email" : "tel"}
          autoComplete={canal === "email" ? "email" : "tel"} placeholder={canal === "email" ? t.phEmail : t.phWa}
          aria-label={canal === "email" ? t.phEmail : t.phWa} />
        <button className="rg-retry" type="submit" disabled={estado === "enviando"}>{estado === "enviando" ? t.sending : t.send}</button>
      </div>
      <input type="text" tabIndex={-1} autoComplete="off" aria-hidden="true" className="rg-hp" value={website} onChange={e => setWebsite(e.target.value)} />
      <label className="rg-achados-consent"><input type="checkbox" required checked={consent} onChange={e => setConsent(e.target.checked)} /> <span>{t.consent} <Link to="/cancelar">{t.sair}</Link>.</span></label>
      {estado === "erro" && <p className="rg-achados-erro" role="alert">{t.error}</p>}
    </form>}
  </section>;
}
