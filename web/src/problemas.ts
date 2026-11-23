import { API_URL } from "./config";
import type { Produto } from "./components/CartaoProduto";

export type Lang = "pt" | "en" | "es";
export type Txt = Record<Lang, string>;
export type ProblemaResumo = { slug: string; titulo: Txt; curto?: Txt; resumo: Txt; tema: string; produtos: number };
export type Tema = { slug: string; titulo: Txt; icone: string; problemas: ProblemaResumo[] };
export type Escolha = { nivel: { chave: string } & Txt; motivo: Txt; oferta: Produto };
export type Problema = ProblemaResumo & { considerar: Txt[]; tema_titulo: Txt; tema_icone: string; escolhas: Escolha[] };

// Espera no máximo 8 s por resposta e tenta de novo uma vez: o visitante nunca fica preso no "Carregando".
async function buscar(url: string, signal?: AbortSignal): Promise<Response> {
  for (let tentativa = 0; ; tentativa++) {
    const c = new AbortController();
    const parar = () => c.abort();
    signal?.addEventListener("abort", parar);
    const t = setTimeout(parar, 8000);
    try {
      return await fetch(url, { signal: c.signal, headers: { Accept: "application/json" } });
    } catch (e) {
      if (signal?.aborted || tentativa >= 1) throw e;
    } finally {
      clearTimeout(t);
      signal?.removeEventListener("abort", parar);
    }
  }
}

export async function carregarTemas(signal?: AbortSignal): Promise<Tema[]> {
  const r = await buscar(API_URL + "/public/problemas", signal);
  if (!r.ok) throw new Error("indisponivel");
  const b = await r.json();
  return Array.isArray(b?.temas) ? b.temas : [];
}

export async function carregarProblema(slug: string, signal?: AbortSignal): Promise<Problema | null> {
  const r = await buscar(API_URL + "/public/problemas/" + encodeURIComponent(slug), signal);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error("indisponivel");
  return (await r.json()).data as Problema;
}
