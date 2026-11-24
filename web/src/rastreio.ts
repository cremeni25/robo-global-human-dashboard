// Rastreio de canal: quem chega por um link da divulgação (Instagram, TikTok,
// WhatsApp...) carrega utm_source/utm_medium/utm_campaign até o clique de saída,
// e o painel mostra cliques e vendas por canal.
import { API_URL } from "./config";

const CHAVES = ["utm_source", "utm_medium", "utm_campaign"] as const;
const ARMAZEM = "rg_utm";

export function capturarCanal(): void {
  try {
    const q = new URLSearchParams(window.location.search);
    const novo: Record<string, string> = {};
    for (const k of CHAVES) { const v = q.get(k); if (v) novo[k] = v.slice(0, 120); }
    if (Object.keys(novo).length) sessionStorage.setItem(ARMAZEM, JSON.stringify(novo));
  } catch { /* navegação privada: segue sem canal */ }
}

function canal(): Record<string, string> {
  try { return JSON.parse(sessionStorage.getItem(ARMAZEM) || "{}"); } catch { return {}; }
}

/** Canal de divulgação por onde a pessoa chegou (ex.: "instagram"), ou "". */
export function canalAtual(): string { return canal().utm_source || ""; }

/** Último tema visitado: o início mostra "Continuar em…" (fica só neste aparelho). */
export function lembrarTema(slug: string): void { try { localStorage.setItem("rg_ultimo_tema", slug); } catch { /* sem armazenamento */ } }
export function ultimoTema(): string { try { return localStorage.getItem("rg_ultimo_tema") || ""; } catch { return ""; } }

/** Link de saída rastreado para a loja parceira. */
export function linkSaida(url: string, dorId?: string): string {
  const q = new URLSearchParams(canal());
  if (dorId) q.set("d", dorId);
  const s = q.toString();
  return API_URL + url + (s ? "?" + s : "");
}

type ComTraducao = { title: string; translations?: Record<string, { title?: string } | undefined> };
/** Título no idioma do visitante quando existir; senão o original da loja. */
export function tituloOferta(o: ComTraducao, lang: string): string {
  return o.translations?.[lang]?.title || o.title;
}

/** Compartilhar: menu nativo do aparelho; sem ele, WhatsApp. */
export async function compartilhar(titulo: string, url: string): Promise<void> {
  const nav = navigator as Navigator & { share?: (d: ShareData) => Promise<void> };
  if (nav.share) { try { await nav.share({ title: titulo, url }); return; } catch { return; } }
  window.open("https://wa.me/?text=" + encodeURIComponent(titulo + " " + url), "_blank", "noopener");
}
