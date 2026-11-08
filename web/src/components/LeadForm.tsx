import { useState } from "react";
import type { FormEvent } from "react";
import { API_URL } from "../config";
import { useLanguage } from "../contexts/LanguageContext";

const copy = {
  pt: { title: "Quer ser avisado quando houver mais soluções para isso?", compactTitle: "Não encontrou o que procurava?", email: "Seu e-mail", name: "Seu nome (opcional)", consent: "Aceito receber contato do Robô Global sobre esta necessidade. Posso pedir a remoção quando quiser.", send: "Avise-me", sending: "Enviando…", ok: "Pronto! Vamos avisar você.", error: "Não foi possível enviar agora. Tente novamente." },
  en: { title: "Want to hear when there are more solutions for this?", compactTitle: "Didn't find what you need?", email: "Your email", name: "Your name (optional)", consent: "I agree to be contacted by Robô Global about this need. I can ask to be removed at any time.", send: "Notify me", sending: "Sending…", ok: "Done! We'll let you know.", error: "We couldn't send this right now. Please try again." },
  es: { title: "¿Quieres saber cuando haya más soluciones para esto?", compactTitle: "¿No encontraste lo que buscabas?", email: "Tu correo", name: "Tu nombre (opcional)", consent: "Acepto que Robô Global me contacte sobre esta necesidad. Puedo pedir la baja cuando quiera.", send: "Avísame", sending: "Enviando…", ok: "¡Listo! Te avisaremos.", error: "No pudimos enviarlo ahora. Inténtalo de nuevo." },
};

export default function LeadForm({ dorId, compact = false }: { dorId: string; compact?: boolean }) {
  const { lang } = useLanguage();
  const t = copy[lang];
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [website, setWebsite] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "ok" | "error">("idle");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setState("sending");
    try {
      const r = await fetch(API_URL + "/public/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, consent, dor_id: dorId, language: lang, website }),
      });
      setState(r.ok ? "ok" : "error");
    } catch {
      setState("error");
    }
  }

  if (state === "ok") return <p className="rg-lead-ok" role="status">✓ {t.ok}</p>;
  return (
    <form className="rg-lead-form" onSubmit={submit}>
      <h3>{compact ? t.compactTitle : t.title}</h3>
      <div className="rg-lead-fields">
        <input type="email" required placeholder={t.email} aria-label={t.email} value={email} onChange={e => setEmail(e.target.value)} />
        <input type="text" placeholder={t.name} aria-label={t.name} value={name} onChange={e => setName(e.target.value)} />
        <input type="text" tabIndex={-1} autoComplete="off" aria-hidden="true" className="rg-hp" value={website} onChange={e => setWebsite(e.target.value)} />
      </div>
      <label className="rg-lead-consent"><input type="checkbox" required checked={consent} onChange={e => setConsent(e.target.checked)} /> {t.consent}</label>
      <button className="rg-retry" type="submit" disabled={state === "sending"}>{state === "sending" ? t.sending : t.send}</button>
      {state === "error" && <p role="alert">{t.error}</p>}
    </form>
  );
}
