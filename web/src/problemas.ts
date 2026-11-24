import { API_URL } from "./config";
import type { Produto } from "./components/CartaoProduto";

export type Lang = "pt" | "en" | "es";
export type Txt = Record<Lang, string>;
export type ProblemaResumo = { slug: string; titulo: Txt; curto?: Txt; resumo: Txt; tema: string; produtos: number };
export type Tema = { slug: string; titulo: Txt; icone: string; problemas: ProblemaResumo[] };
export type Loja = { loja: string; url: string };
export type Escolha = { nivel: { chave: string } & Txt; motivo: Txt; oferta: Produto; lojas?: Loja[] };
export type Problema = ProblemaResumo & { considerar: Txt[]; tema_titulo: Txt; tema_icone: string; escolhas: Escolha[] };
type Catalogo = { temas: Tema[]; detalhes: Record<string, Problema> };

// O catálogo inteiro (poucos KB) é carregado uma vez e guardado no aparelho:
// as telas seguintes abrem na hora, e quem volta ao site vê tudo sem esperar.
// Em segundo plano, uma versão nova é buscada e substitui a guardada.
const ARMAZEM = "rg_catalogo_v1";
let memoria: Catalogo | null = lerGuardado();
let pedido: Promise<Catalogo> | null = null;

function lerGuardado(): Catalogo | null {
  try {
    const c = JSON.parse(localStorage.getItem(ARMAZEM) || "null");
    return c && Array.isArray(c.temas) && c.detalhes ? c : null;
  } catch { return null; }
}

// Espera no máximo 8 s por resposta e tenta de novo uma vez.
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

function atualizar(): Promise<Catalogo> {
  if (!pedido) {
    pedido = buscar(API_URL + "/public/catalogo")
      .then(r => { if (!r.ok) throw new Error("indisponivel"); return r.json(); })
      .then((b: Catalogo) => {
        const c = { temas: Array.isArray(b?.temas) ? b.temas : [], detalhes: b?.detalhes || {} };
        memoria = c;
        try { localStorage.setItem(ARMAZEM, JSON.stringify(c)); } catch { /* sem armazenamento */ }
        return c;
      })
      .finally(() => { pedido = null; });
  }
  return pedido;
}

/** Catálogo na hora, se já houver; senão espera a primeira carga. Sempre renova em segundo plano. */
async function catalogo(): Promise<Catalogo> {
  if (memoria) {
    if (!pedido) atualizar().catch(() => undefined);
    return memoria;
  }
  return atualizar();
}

export function catalogoImediato(): Catalogo | null { return memoria; }

export async function carregarTemas(_signal?: AbortSignal): Promise<Tema[]> {
  return (await catalogo()).temas;
}

export async function carregarProblema(slug: string, _signal?: AbortSignal): Promise<Problema | null> {
  const c = await catalogo();
  if (c.detalhes[slug]) return c.detalhes[slug];
  const novo = await atualizar().catch(() => c); // página recém-criada: confere a versão mais nova
  return novo.detalhes[slug] || null;
}
