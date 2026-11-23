import { API_URL } from "./config";
import type { Produto } from "./components/CartaoProduto";

export type Lang = "pt" | "en" | "es";
export type Txt = Record<Lang, string>;
export type ProblemaResumo = { slug: string; titulo: Txt; resumo: Txt; tema: string; produtos: number };
export type Tema = { slug: string; titulo: Txt; icone: string; problemas: ProblemaResumo[] };
export type Escolha = { nivel: { chave: string } & Txt; motivo: Txt; oferta: Produto };
export type Problema = ProblemaResumo & { considerar: Txt[]; tema_titulo: Txt; tema_icone: string; escolhas: Escolha[] };

export async function carregarTemas(signal?: AbortSignal): Promise<Tema[]> {
  const r = await fetch(API_URL + "/public/problemas", { signal, headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error("indisponivel");
  const b = await r.json();
  return Array.isArray(b?.temas) ? b.temas : [];
}

export async function carregarProblema(slug: string, signal?: AbortSignal): Promise<Problema | null> {
  const r = await fetch(API_URL + "/public/problemas/" + encodeURIComponent(slug), { signal, headers: { Accept: "application/json" } });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error("indisponivel");
  return (await r.json()).data as Problema;
}
