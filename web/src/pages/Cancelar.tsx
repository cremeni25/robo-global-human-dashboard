// Sair dos achados da semana: simples, sem login, e com a mesma resposta para qualquer contato.
import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { API_URL } from "../config";
import { useLanguage } from "../contexts/LanguageContext";

const copy = {
  pt: { title: "Sair dos achados da semana", lead: "Digite o WhatsApp ou o e-mail que você cadastrou. Você deixa de receber na hora.",
    ph: "WhatsApp com DDD ou e-mail", send: "Cancelar meu recebimento", ok: "Pronto. Você não vai mais receber os achados da semana. Se mudar de ideia, é só se inscrever de novo.",
    error: "Confira o contato e tente de novo.", back: "Voltar ao início" },
  en: { title: "Leave the weekly picks", lead: "Enter the WhatsApp number or email you signed up with. You'll stop receiving them right away.",
    ph: "WhatsApp number or email", send: "Unsubscribe", ok: "Done. You won't receive the weekly picks anymore. You can sign up again anytime.",
    error: "Please check your contact and try again.", back: "Back to home" },
  es: { title: "Dejar los hallazgos de la semana", lead: "Escribe el WhatsApp o el correo que registraste. Dejarás de recibirlos al instante.",
    ph: "WhatsApp o correo", send: "Cancelar mi suscripción", ok: "Listo. Ya no recibirás los hallazgos de la semana. Puedes volver a suscribirte cuando quieras.",
    error: "Revisa el contacto e inténtalo de nuevo.", back: "Volver al inicio" },
};

export default function Cancelar() {
  const { lang } = useLanguage(); const t = copy[lang];
  const [contato, setContato] = useState("");
  const [estado, setEstado] = useState<"idle" | "enviando" | "ok" | "erro">("idle");
  async function enviar(e: FormEvent) {
    e.preventDefault(); setEstado("enviando");
    try {
      const r = await fetch(API_URL + "/public/inscricoes/cancelar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ contato }) });
      setEstado(r.ok ? "ok" : "erro");
    } catch { setEstado("erro"); }
  }
  return <div className="rg-store">
    <section className="rg-store-hero"><div className="rg-store-inner"><h1>{t.title}</h1><p>{t.lead}</p></div></section>
    <div className="rg-store-inner rg-store-body">
      {estado === "ok" ? <p className="rg-ajudou rg-ajudou-fim" role="status">✓ {t.ok}</p> :
      <form className="rg-cancelar" onSubmit={enviar}>
        <input required value={contato} onChange={e => setContato(e.target.value)} placeholder={t.ph} aria-label={t.ph} autoComplete="email" />
        <button className="rg-retry" type="submit" disabled={estado === "enviando"}>{t.send}</button>
        {estado === "erro" && <p role="alert">{t.error}</p>}
      </form>}
      <p><Link className="rg-shelf-all" to="/">← {t.back}</Link></p>
    </div>
  </div>;
}
