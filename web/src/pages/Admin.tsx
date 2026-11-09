/* eslint-disable @typescript-eslint/no-explicit-any -- respostas JSON administrativas, validadas pelo servidor */
import { useCallback, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { API_URL } from "../config";

/* Painel de operação humana do Robô Global.
   A máquina mede e recomenda; aqui uma pessoa decide. */

const TOKEN_KEY = "rg_admin_token";
type Json = Record<string, any>;
type Tab = "geral" | "aquisicao" | "catalogo" | "ofertas" | "vendas" | "leads" | "sistema";

function readToken() { try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; } }

async function call(token: string, path: string, init: RequestInit = {}): Promise<any> {
  const r = await fetch(API_URL + path, {
    ...init,
    headers: { Authorization: "Bearer " + token, ...(init.body && typeof init.body === "string" && !path.endsWith("importar") ? { "Content-Type": "application/json" } : {}), ...(init.headers || {}) },
  });
  const text = await r.text();
  const data = text ? (() => { try { return JSON.parse(text); } catch { return text; } })() : null;
  if (!r.ok) throw new Error((data && data.detail && (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))) || "Erro " + r.status);
  return data;
}

const money = (v: any) => Number(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = (v: any) => (Number(v || 0) * 100).toFixed(1) + "%";
const dt = (v: any) => (v ? new Date(v).toLocaleString("pt-BR") : "");

export default function Admin() {
  const [token, setToken] = useState(readToken);
  const [tab, setTab] = useState<Tab>("geral");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [version, setVersion] = useState(0); // clicar na aba atual recarrega os dados

  const run = useCallback(async (path: string, init?: RequestInit, okText?: OkText) => {
    try {
      const data = await call(token, path, init);
      if (okText) setMsg({ ok: true, text: typeof okText === "function" ? okText(data) : okText });
      return data;
    } catch (e) {
      const text = (e as Error).message;
      if (/Token administrativo invalido/.test(text)) { try { sessionStorage.removeItem(TOKEN_KEY); } catch { /* sem armazenamento */ } setToken(""); }
      setMsg({ ok: false, text });
      throw e;
    }
  }, [token]);

  if (!token) return <Login onToken={t => { try { sessionStorage.setItem(TOKEN_KEY, t); } catch { /* sem armazenamento */ } setToken(t); }} />;

  const tabs: [Tab, string][] = [["geral", "Visão geral"], ["aquisicao", "Aquisição"], ["catalogo", "Catálogo"], ["ofertas", "Ofertas"], ["vendas", "Vendas"], ["leads", "Leads"], ["sistema", "Sistema"]];
  return <div className="adm">
    <div className="adm-top"><h1>Operação Robô Global</h1>
      <button className="adm-link" onClick={() => { try { sessionStorage.removeItem(TOKEN_KEY); } catch { /* sem armazenamento */ } setToken(""); }}>Sair</button></div>
    <nav className="adm-tabs">{tabs.map(([k, label]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => { setTab(k); setMsg(null); setVersion(v => v + 1); }}>{label}</button>)}</nav>
    {msg && <p className={msg.ok ? "adm-ok" : "adm-err"} role="status">{msg.text}</p>}
    <div key={tab + version}>
      {tab === "geral" && <Geral run={run} />}
      {tab === "aquisicao" && <Aquisicao run={run} />}
      {tab === "catalogo" && <Catalogo run={run} />}
      {tab === "ofertas" && <Ofertas run={run} />}
      {tab === "vendas" && <Vendas run={run} />}
      {tab === "leads" && <Leads run={run} token={token} />}
      {tab === "sistema" && <Sistema run={run} />}
    </div>
  </div>;
}

type OkText = string | ((data: any) => string);
type Run = (path: string, init?: RequestInit, okText?: OkText) => Promise<any>;

function useData(run: Run, path: string): [any, () => void] {
  const [data, setData] = useState<any>(null);
  const [n, setN] = useState(0);
  useEffect(() => { run(path).then(setData).catch(() => setData(null)); }, [run, path, n]);
  return [data, () => setN(x => x + 1)];
}

function Login({ onToken }: { onToken: (t: string) => void }) {
  const [value, setValue] = useState("");
  const [err, setErr] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault(); setErr("");
    try { await call(value.trim(), "/admin/sistema"); onToken(value.trim()); }
    catch (x) { setErr((x as Error).message); }
  }
  return <div className="adm adm-login"><h1>Área de operação</h1>
    <p>Acesso com o token administrativo definido no servidor (ADMIN_TOKEN).</p>
    <form onSubmit={submit}><input type="password" value={value} onChange={e => setValue(e.target.value)} placeholder="Token" aria-label="Token administrativo" required />
      <button className="adm-btn">Entrar</button></form>{err && <p className="adm-err">{err}</p>}</div>;
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return <section className="adm-card"><h2>{title}</h2>{children}</section>;
}

/* ------------------------------------------------------------ visão geral */
function Geral({ run }: { run: Run }) {
  const [resumo, reloadResumo] = useData(run, "/admin/resumo");
  const [metricas, reloadMetricas] = useData(run, "/admin/metricas");
  const [decisoes, reloadDecisoes] = useData(run, "/admin/decisoes?status=pendente");
  const reload = () => { reloadResumo(); reloadMetricas(); reloadDecisoes(); };
  const decidir = async (id: string, acao: "aprovar" | "rejeitar") => {
    await run(`/admin/decisoes/${id}/${acao}`, { method: "POST", body: JSON.stringify({}) }, acao === "aprovar" ? "Decisão aprovada e aplicada." : "Decisão rejeitada.");
    reload();
  };
  const t = resumo?.totais || {};
  return <>
    {resumo && <Card title="Leitura humana (últimos 30 dias)">
      {!resumo.sistema?.ativo && <p className="adm-err">Sistema PAUSADO: redirecionamentos bloqueados. {resumo.sistema?.motivo}</p>}
      <div className="adm-kpis">{[["Cliques", t.cliques], ["Vendas aprovadas", t.vendas], ["Comissões", money(t.receita)], ["Reembolsos", t.reembolsos], ["Leads", t.leads], ["Ofertas no ar", t.ofertas_visiveis]].map(([k, v]) => <div key={k}><strong>{v}</strong><span>{k}</span></div>)}</div>
      <ul className="adm-frases">{resumo.frases.map((f: string) => <li key={f}>{f}</li>)}</ul>
    </Card>}
    <Card title="Recomendações aguardando sua decisão">
      <button className="adm-btn" onClick={async () => { await run("/admin/decisoes/gerar", { method: "POST" }, r => `${r.criadas} nova(s) recomendação(ões).`); reload(); }}>Analisar dados e gerar recomendações</button>
      {decisoes?.data?.length ? <table className="adm-table"><thead><tr><th>Oferta</th><th>Recomendação</th><th>Motivo</th><th></th></tr></thead><tbody>
        {decisoes.data.map((d: Json) => <tr key={d.id}><td>{d.oferta}</td><td><b>{d.recomendacao}</b></td><td>{d.motivo}</td>
          <td className="adm-actions"><button className="adm-btn" onClick={() => decidir(d.id, "aprovar")}>Aprovar</button><button className="adm-link" onClick={() => decidir(d.id, "rejeitar")}>Rejeitar</button></td></tr>)}
      </tbody></table> : <p className="adm-muted">Nenhuma recomendação pendente.</p>}
      <p className="adm-muted">Aprovar PAUSAR desativa a oferta. Aprovar ESCALAR aumenta a prioridade dela nas dores. Nada muda sem aprovação.</p>
    </Card>
    <Card title="Desempenho por oferta (todo o período)">
      {metricas?.ofertas?.length ? <div className="adm-scroll"><table className="adm-table"><thead><tr><th>Oferta</th><th>No ar</th><th>Cliques</th><th>Vendas</th><th>Conversão</th><th>Comissões</th><th>Ganho/clique</th><th>Reembolso</th></tr></thead><tbody>
        {metricas.ofertas.map((m: Json) => <tr key={m.oferta_id}><td>{m.title}</td><td>{m.visivel ? "sim" : "não"}</td><td>{m.cliques}</td><td>{m.vendas}</td><td>{pct(m.taxa_conversao)}</td><td>{money(m.receita)}</td><td>{money(m.epc)}</td><td>{pct(m.taxa_reembolso)}</td></tr>)}
      </tbody></table></div> : <p className="adm-muted">Ainda não há ofertas.</p>}
    </Card>
    <Card title="Demanda por dor">
      {metricas?.dores?.length ? <div className="adm-scroll"><table className="adm-table"><thead><tr><th>Dor</th><th>Caminho</th><th>Cliques</th><th>Leads</th><th>Ofertas no ar</th><th></th></tr></thead><tbody>
        {metricas.dores.map((d: Json) => <tr key={d.dor_id}><td>{d.title}</td><td className="adm-muted">{d.nicho} › {d.subnicho}</td><td>{d.cliques}</td><td>{d.leads}</td><td>{d.ofertas_visiveis}</td><td>{d.oportunidade && <b className="adm-tag">oportunidade</b>}</td></tr>)}
      </tbody></table></div> : <p className="adm-muted">Ainda não há dores cadastradas.</p>}
      <p className="adm-muted">"Oportunidade" = pessoas pediram solução e não há oferta: busque um parceiro ou crie um produto/serviço próprio.</p>
    </Card>
  </>;
}

/* ------------------------------------------------------------ catálogo */
function Catalogo({ run }: { run: Run }) {
  const [cat, reload] = useData(run, "/admin/catalogo");
  const [ofertas] = useData(run, "/admin/ofertas");
  const [form, setForm] = useState({ nivel: "nichos", title: "", slug: "", description: "", parent_id: "" });
  const [link, setLink] = useState({ dor_id: "", oferta_id: "", priority: 1 });
  const nichos: Json[] = cat?.data || [];
  const subs = nichos.flatMap(n => n.subnichos.map((s: Json) => ({ ...s, path: n.title + " › " + s.title })));
  const dores = subs.flatMap(s => s.dores.map((d: Json) => ({ ...d, path: s.path + " › " + d.title })));
  const slugify = (v: string) => v.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const toggle = async (nivel: string, item: Json) => { await run(`/admin/catalogo/${nivel}/${item.id}`, { method: "PATCH", body: JSON.stringify({ published: !item.published }) }, item.published ? "Despublicado." : "Publicado."); reload(); };
  const Pub = ({ nivel, item }: { nivel: string; item: Json }) => <button className={item.published ? "adm-pill on" : "adm-pill"} onClick={() => toggle(nivel, item)}>{item.published ? "publicado" : "rascunho"}</button>;
  async function criar(e: FormEvent) {
    e.preventDefault();
    const { nivel, ...rest } = form;
    await run(`/admin/catalogo/${nivel}`, { method: "POST", body: JSON.stringify({ ...rest, parent_id: rest.parent_id || null }) }, "Criado como rascunho. Publique quando estiver pronto.");
    setForm({ ...form, title: "", slug: "", description: "" }); reload();
  }
  async function vincular(e: FormEvent) {
    e.preventDefault();
    await run("/admin/vinculos", { method: "POST", body: JSON.stringify(link) }, "Oferta vinculada à dor."); reload();
  }
  return <>
    <Card title="Novo item">
      <form className="adm-form" onSubmit={criar}>
        <select value={form.nivel} onChange={e => setForm({ ...form, nivel: e.target.value, parent_id: "" })}><option value="nichos">Nicho</option><option value="subnichos">Subnicho</option><option value="dores">Dor (necessidade)</option></select>
        {form.nivel !== "nichos" && <select required value={form.parent_id} onChange={e => setForm({ ...form, parent_id: e.target.value })}><option value="">— dentro de —</option>{(form.nivel === "subnichos" ? nichos.map(n => ({ id: n.id, path: n.title })) : subs).map(p => <option key={p.id} value={p.id}>{p.path}</option>)}</select>}
        <input required placeholder="Título" value={form.title} onChange={e => setForm({ ...form, title: e.target.value, slug: slugify(e.target.value) })} />
        <input required placeholder="slug-sem-acento" pattern="[a-z0-9]+(-[a-z0-9]+)*" value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })} />
        <textarea placeholder="Descrição para o público" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
        <button className="adm-btn">Criar</button>
      </form>
    </Card>
    <Card title="Vincular oferta a uma dor">
      <form className="adm-form" onSubmit={vincular}>
        <select required value={link.dor_id} onChange={e => setLink({ ...link, dor_id: e.target.value })}><option value="">— dor —</option>{dores.map(d => <option key={d.id} value={d.id}>{d.path}</option>)}</select>
        <select required value={link.oferta_id} onChange={e => setLink({ ...link, oferta_id: e.target.value })}><option value="">— oferta —</option>{(ofertas?.data || []).map((o: Json) => <option key={o.id} value={o.id}>{o.title}</option>)}</select>
        <input type="number" min={0} value={link.priority} onChange={e => setLink({ ...link, priority: Number(e.target.value) })} aria-label="Prioridade" title="Prioridade (maior aparece primeiro)" />
        <button className="adm-btn">Vincular</button>
      </form>
    </Card>
    <Card title="Árvore do catálogo">
      <p className="adm-muted">Um item só aparece ao público se ele e todos os itens acima estiverem publicados.</p>
      {nichos.length === 0 && <p className="adm-muted">Catálogo vazio.</p>}
      <ul className="adm-tree">{nichos.map(n => <li key={n.id}><b>{n.title}</b> <Pub nivel="nichos" item={n} />
        <ul>{n.subnichos.map((s: Json) => <li key={s.id}>{s.title} <Pub nivel="subnichos" item={s} />
          <ul>{s.dores.map((d: Json) => <li key={d.id}>{d.title} <Pub nivel="dores" item={d} />
            {d.vinculos.length > 0 && <ul>{d.vinculos.map((v: Json) => <li key={v.id} className="adm-muted">→ {v.oferta} (prioridade {v.priority}) <button className="adm-link" onClick={async () => { await run(`/admin/vinculos/${v.id}`, { method: "DELETE" }, "Vínculo removido."); reload(); }}>remover</button></li>)}</ul>}
          </li>)}</ul></li>)}</ul></li>)}</ul>
    </Card>
  </>;
}

/* ------------------------------------------------------------ ofertas */
const emptyOffer = { id: "", title: "", destination_url: "https://", kind: "afiliado", platform: "hotmart", provider: "", subid_param: "sck", external_product_id: "", commission_estimate: 0, description: "", image_url: "", market: "BR", language: "pt" };

function Ofertas({ run }: { run: Run }) {
  const [busca, setBusca] = useState("");
  const [termo, setTermo] = useState("");
  const [list, reload] = useData(run, "/admin/ofertas?limit=100&q=" + encodeURIComponent(termo));
  const [f, setF] = useState<Json>(emptyOffer);
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  async function salvar(e: FormEvent) {
    e.preventDefault();
    const { id, ...body } = f;
    body.commission_estimate = Number(body.commission_estimate || 0);
    if (!body.external_product_id) body.external_product_id = null;
    if (!id && !body.subid_param) body.subid_param = null;
    await run(id ? `/admin/ofertas/${id}` : "/admin/ofertas", { method: id ? "PATCH" : "POST", body: JSON.stringify(body) }, id ? "Oferta atualizada." : "Oferta criada como rascunho.");
    setF(emptyOffer); reload();
  }
  const patch = async (o: Json, body: Json, text: string) => { await run(`/admin/ofertas/${o.id}`, { method: "PATCH", body: JSON.stringify(body) }, text); reload(); };
  return <>
    <Card title={f.id ? "Editar oferta" : "Nova oferta"}>
      <form className="adm-form" onSubmit={salvar}>
        <input required placeholder="Título público" value={f.title} onChange={set("title")} />
        <input required type="url" placeholder="Link de destino (https://, seu link de afiliado ou checkout)" value={f.destination_url} onChange={set("destination_url")} />
        <select value={f.kind} onChange={set("kind")}><option value="afiliado">Afiliado</option><option value="produto_proprio">Produto próprio</option><option value="servico">Serviço próprio</option><option value="lead_parceiro">Lead para parceiro</option></select>
        <input placeholder="Plataforma (hotmart, eduzz, kiwify, awin, manual…)" value={f.platform} onChange={set("platform")} />
        <input placeholder="Parâmetro de rastreio (Hotmart: sck)" value={f.subid_param || ""} onChange={set("subid_param")} />
        <input placeholder="Id do produto na plataforma (para atribuir vendas)" value={f.external_product_id || ""} onChange={set("external_product_id")} />
        <input placeholder="Fornecedor exibido" value={f.provider} onChange={set("provider")} />
        <input type="number" step="0.01" min={0} placeholder="Comissão estimada por venda" value={f.commission_estimate} onChange={set("commission_estimate")} />
        <textarea placeholder="Descrição honesta para o público (sem promessas de resultado)" value={f.description} onChange={set("description")} />
        <div className="adm-actions"><button className="adm-btn">{f.id ? "Salvar" : "Criar"}</button>{f.id && <button type="button" className="adm-link" onClick={() => setF(emptyOffer)}>Cancelar</button>}</div>
      </form>
    </Card>
    <Card title={`Ofertas (${list?.total ?? 0})`}>
      <form className="adm-form" onSubmit={e => { e.preventDefault(); setTermo(busca); }}><input placeholder="Buscar por título, categoria ou fornecedor" value={busca} onChange={e => setBusca(e.target.value)} /><button className="adm-btn">Buscar</button></form>
      <p className="adm-muted">Mostrando até 100. Produtos importados das redes são controlados pelo anunciante (aba Aquisição), não um a um.</p>
      {list?.data?.length ? <div className="adm-scroll"><table className="adm-table"><thead><tr><th>Título</th><th>Tipo</th><th>Plataforma</th><th>Estado</th><th></th></tr></thead><tbody>
        {list.data.map((o: Json) => <tr key={o.id}><td>{o.title}<div className="adm-muted adm-url">{o.destination_url}</div></td><td>{o.kind}</td><td>{o.platform}</td>
          <td><button className={o.published ? "adm-pill on" : "adm-pill"} onClick={() => patch(o, { published: !o.published }, o.published ? "Oferta despublicada." : "Oferta publicada.")}>{o.published ? "publicada" : "rascunho"}</button>
            <button className={o.active ? "adm-pill on" : "adm-pill"} onClick={() => patch(o, { active: !o.active }, o.active ? "Oferta desativada." : "Oferta reativada.")}>{o.active ? "ativa" : "inativa"}</button></td>
          <td><button className="adm-link" onClick={() => setF({ ...emptyOffer, ...o, subid_param: o.subid_param || "", external_product_id: o.external_product_id || "" })}>editar</button></td></tr>)}
      </tbody></table></div> : <p className="adm-muted">Nenhuma oferta.</p>}
    </Card>
  </>;
}

/* ------------------------------------------------------------ vendas */
function Vendas({ run }: { run: Run }) {
  const [list, reload] = useData(run, "/admin/conversoes?limit=300");
  const [f, setF] = useState({ platform: "hotmart", external_id: "", status: "approved", commission_amount: "", gross_amount: "", product_id: "" });
  const [csv, setCsv] = useState("platform,external_id,status,commission_amount,gross_amount,product_id\n");
  async function lancar(e: FormEvent) {
    e.preventDefault();
    const body: Json = { ...f, commission_amount: Number(f.commission_amount || 0), gross_amount: Number(f.gross_amount || 0) };
    await run("/admin/conversoes", { method: "POST", body: JSON.stringify(body) },
      r => r.criada ? "Venda registrada." : r.alterada ? "Status da venda atualizado." : "Venda já registrada (nada mudou).");
    reload();
  }
  async function importar() {
    await run("/admin/conversoes/importar", { method: "POST", body: csv, headers: { "Content-Type": "text/csv" } },
      r => `Importação: ${r.criadas} nova(s), ${r.atualizadas} atualizada(s), ${r.duplicadas} já existente(s), ${r.erros.length} erro(s).` + (r.erros.length ? " " + r.erros.map((x: Json) => `linha ${x.linha}: ${x.erro}`).join("; ") : ""));
    reload();
  }
  return <>
    <Card title="Lançar venda do relatório da plataforma">
      <form className="adm-form" onSubmit={lancar}>
        <input required placeholder="Plataforma" value={f.platform} onChange={e => setF({ ...f, platform: e.target.value })} />
        <input required placeholder="Id da transação" value={f.external_id} onChange={e => setF({ ...f, external_id: e.target.value })} />
        <select value={f.status} onChange={e => setF({ ...f, status: e.target.value })}><option value="approved">aprovada</option><option value="pending">pendente</option><option value="refunded">reembolsada</option><option value="chargeback">chargeback</option><option value="canceled">cancelada</option></select>
        <input type="number" step="0.01" placeholder="Sua comissão" value={f.commission_amount} onChange={e => setF({ ...f, commission_amount: e.target.value })} />
        <input type="number" step="0.01" placeholder="Valor da venda" value={f.gross_amount} onChange={e => setF({ ...f, gross_amount: e.target.value })} />
        <input placeholder="Id do produto (atribui à oferta)" value={f.product_id} onChange={e => setF({ ...f, product_id: e.target.value })} />
        <button className="adm-btn">Registrar</button>
      </form>
      <p className="adm-muted">Lançar de novo a mesma transação não duplica: só atualiza o status (ex.: aprovada → reembolsada).</p>
    </Card>
    <Card title="Importar CSV">
      <textarea className="adm-csv" value={csv} onChange={e => setCsv(e.target.value)} aria-label="Conteúdo CSV" />
      <button className="adm-btn" onClick={importar}>Importar</button>
    </Card>
    <Card title="Vendas registradas">
      {list?.data?.length ? <div className="adm-scroll"><table className="adm-table"><thead><tr><th>Data</th><th>Plataforma</th><th>Transação</th><th>Status</th><th>Comissão</th><th>Origem</th><th>Atribuída</th></tr></thead><tbody>
        {list.data.map((c: Json) => <tr key={c.id}><td>{dt(c.occurred_at)}</td><td>{c.platform}</td><td>{c.external_id}</td><td>{c.status}</td><td>{money(c.commission_amount)}</td><td>{c.source}</td><td>{c.oferta_id ? (c.clique_id ? "clique" : "produto") : "—"}</td></tr>)}
      </tbody></table></div> : <p className="adm-muted">Nenhuma venda registrada ainda.</p>}
    </Card>
  </>;
}

/* ------------------------------------------------------------ leads */
function Leads({ run, token }: { run: Run; token: string }) {
  const [list] = useData(run, "/admin/leads");
  async function baixar() {
    const r = await fetch(API_URL + "/admin/leads.csv", { headers: { Authorization: "Bearer " + token } });
    if (!r.ok) return;
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a"); a.href = url; a.download = "leads.csv"; a.click(); URL.revokeObjectURL(url);
  }
  return <Card title="Pessoas que pediram para ser avisadas">
    <button className="adm-btn" onClick={baixar}>Baixar CSV</button>
    <p className="adm-muted">Todos deram consentimento. Use só para o assunto que pediram (LGPD).</p>
    {list?.data?.length ? <div className="adm-scroll"><table className="adm-table"><thead><tr><th>Data</th><th>E-mail</th><th>Nome</th><th>Idioma</th></tr></thead><tbody>
      {list.data.map((l: Json) => <tr key={l.id}><td>{dt(l.created_at)}</td><td>{l.email}</td><td>{l.name}</td><td>{l.language}</td></tr>)}
    </tbody></table></div> : <p className="adm-muted">Nenhum lead ainda.</p>}
  </Card>;
}

/* ------------------------------------------------------------ sistema */
function Sistema({ run }: { run: Run }) {
  const [sis, reload] = useData(run, "/admin/sistema");
  const [aud] = useData(run, "/admin/auditoria?limit=100");
  const [motivo, setMotivo] = useState("");
  const alterar = async (ativo: boolean) => { await run("/admin/sistema", { method: "PUT", body: JSON.stringify({ ativo, motivo }) }, ativo ? "Sistema ativado." : "Sistema pausado."); reload(); };
  return <>
    <Card title="Estado do sistema">
      {sis && <p>Estado: <b>{sis.ativo ? "ATIVO" : "PAUSADO"}</b>{sis.motivo && <> — {sis.motivo}</>}{sis.alterado_por && <span className="adm-muted"> (por {sis.alterado_por})</span>}</p>}
      <div className="adm-form"><input placeholder="Motivo (registrado na auditoria)" value={motivo} onChange={e => setMotivo(e.target.value)} />
        {sis?.ativo ? <button className="adm-btn adm-danger" onClick={() => alterar(false)}>Pausar redirecionamentos</button> : <button className="adm-btn" onClick={() => alterar(true)}>Ativar</button>}</div>
      <p className="adm-muted">Pausar bloqueia a saída para parceiros. Vendas recebidas por webhook continuam sendo registradas.</p>
    </Card>
    <Card title="Auditoria (quem fez o quê)">
      {aud?.data?.length ? <div className="adm-scroll"><table className="adm-table"><thead><tr><th>Data</th><th>Pessoa</th><th>Ação</th><th>Detalhe</th></tr></thead><tbody>
        {aud.data.map((a: Json) => <tr key={a.id}><td>{dt(a.created_at)}</td><td>{a.actor}</td><td>{a.action}</td><td className="adm-muted">{JSON.stringify(a.detail)}</td></tr>)}
      </tbody></table></div> : <p className="adm-muted">Sem registros.</p>}
    </Card>
  </>;
}

/* ------------------------------------------------------------ aquisição (escala) */
function Aquisicao({ run }: { run: Run }) {
  const [estado, reloadEstado] = useData(run, "/admin/aquisicao");
  const [anunciantes, reloadAnunciantes] = useData(run, "/admin/anunciantes");
  const [categorias, reloadCategorias] = useData(run, "/admin/categorias");
  const [regras, reloadRegras] = useData(run, "/admin/mapeamentos");
  const [cat] = useData(run, "/admin/catalogo");
  const [escolha, setEscolha] = useState<Record<string, string>>({});
  const reload = () => { reloadEstado(); reloadAnunciantes(); reloadCategorias(); reloadRegras(); };
  const dores: Json[] = (cat?.data || []).flatMap((n: Json) => n.subnichos.flatMap((s: Json) => s.dores.map((d: Json) => ({ id: d.id, path: `${n.title} › ${s.title} › ${d.title}` }))));
  const cfg = estado?.configuracao;
  const ciclo = estado?.ultimo_ciclo;
  const patch = async (a: Json, body: Json, text: string) => { await run(`/admin/anunciantes/${a.id}`, { method: "PATCH", body: JSON.stringify(body) }, text); reload(); };
  const ligar = async (categoria: string) => {
    const dor_id = escolha[categoria];
    if (!dor_id) return;
    await run("/admin/mapeamentos", { method: "POST", body: JSON.stringify({ termo: categoria, campo: "category", dor_id }) }, r => `Regra criada: ${r.vinculos_criados} produto(s) ligados agora; os próximos entram sozinhos.`);
    reload();
  };
  return <>
    <Card title="Motor de aquisição automática">
      {cfg && <p>Feeds Awin configurados: <b>{cfg.feeds_awin}</b> · API Awin: <b>{cfg.api_awin ? "configurada" : "não configurada"}</b> · Automático: <b>{cfg.automatica ? `a cada ${cfg.intervalo_horas} h` : "desligado"}</b></p>}
      <button className="adm-btn" onClick={async () => { await run("/admin/aquisicao/executar", { method: "POST" }, "Ciclo iniciado. Clique na aba Aquisição em 1–2 minutos para ver o resultado."); }}>Rodar agora</button>
      {ciclo ? <div><p className="adm-muted">Último ciclo: {dt(ciclo.fim)}</p>
        <ul className="adm-frases">{Object.entries(ciclo.etapas as Json).map(([k, v]) => <li key={k}><b>{k}</b>: {Object.entries(v as Json).filter(([, x]) => x !== "" && x != null).map(([kk, x]) => `${kk}=${x}`).join(" · ")}</li>)}</ul></div>
        : <p className="adm-muted">Nenhum ciclo executado ainda.</p>}
    </Card>
    <Fontes run={run} onChange={reload} />
    <Card title="Anunciantes (uma decisão por empresa, não por produto)">
      <p className="adm-muted">Os produtos de um anunciante vão ao ar quando: a rede confirma que você é afiliado aprovado (<b>joined</b>) <b>e</b> você aprova os termos dele aqui, uma única vez. Leia os termos do programa na Awin antes de aprovar.</p>
      {anunciantes?.data?.length ? <div className="adm-scroll"><table className="adm-table"><thead><tr><th>Anunciante</th><th>Afiliação na rede</th><th>Produtos ativos</th><th>Termos</th><th>No ar?</th></tr></thead><tbody>
        {anunciantes.data.map((a: Json) => <tr key={a.id}><td>{a.name}<div className="adm-muted">{a.platform} #{a.external_id}</div></td>
          <td>{a.membership === "joined" ? <b className="adm-tag adm-tag-ok">aprovado</b> : <span className="adm-muted">{a.membership === "not_joined" ? "não afiliado" : a.membership === "unknown" ? "não verificado" : a.membership}</span>}</td>
          <td>{Number(a.produtos_ativos).toLocaleString("pt-BR")}</td>
          <td><button className={a.approved ? "adm-pill on" : "adm-pill"} onClick={() => patch(a, { approved: !a.approved }, a.approved ? "Aprovação retirada: produtos saem do ar." : "Termos aprovados.")}>{a.approved ? "aprovados" : "aprovar termos"}</button></td>
          <td>{a.liberado ? <b className="adm-tag adm-tag-ok">sim</b> : <span className="adm-muted">não</span>}</td></tr>)}
      </tbody></table></div> : <p className="adm-muted">Nenhum anunciante ainda. Rode o ciclo de aquisição.</p>}
    </Card>
    <Card title="Categorias → dores (regras automáticas)">
      <p className="adm-muted">Ligue uma categoria a uma dor uma vez: todos os produtos dela, atuais e futuros, aparecem naquela dor. Produtos sem dor continuam no catálogo e na busca.</p>
      {categorias?.data?.length ? <div className="adm-scroll"><table className="adm-table"><thead><tr><th>Categoria</th><th>Produtos</th><th>Sem dor</th><th>Ligar à dor</th></tr></thead><tbody>
        {categorias.data.map((c: Json) => <tr key={c.category}><td>{c.category}</td><td>{c.produtos}</td><td>{c.sem_dor}</td>
          <td className="adm-actions"><select value={escolha[c.category] || ""} onChange={e => setEscolha({ ...escolha, [c.category]: e.target.value })}><option value="">— dor —</option>{dores.map(d => <option key={d.id} value={d.id}>{d.path}</option>)}</select><button className="adm-btn" onClick={() => ligar(c.category)}>Ligar</button></td></tr>)}
      </tbody></table></div> : <p className="adm-muted">Sem categorias importadas ainda.</p>}
      {regras?.data?.length > 0 && <><h3>Regras ativas</h3><ul className="adm-frases">{regras.data.map((m: Json) => <li key={m.id}>"{m.termo}" ({m.campo}) → {m.dor} <button className="adm-link" onClick={async () => { await run(`/admin/mapeamentos/${m.id}`, { method: "DELETE" }, "Regra removida (vínculos já criados mantidos)."); reload(); }}>remover</button></li>)}</ul></>}
    </Card>
  </>;
}

const fonteVazia = { rede: "", url: "", anunciante: "", subid: "", mercado: "BR", idioma: "pt", moeda: "BRL" };

function Fontes({ run, onChange }: { run: Run; onChange: () => void }) {
  const [lista, reload] = useData(run, "/admin/fontes");
  const [f, setF] = useState(fonteVazia);
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  async function salvar(e: FormEvent) {
    e.preventDefault();
    await run("/admin/fontes", { method: "POST", body: JSON.stringify(f) }, r => r.mensagem);
    setF(fonteVazia); reload(); onChange();
  }
  return <Card title="Fontes de produtos (qualquer rede, loja ou fornecedor)">
    <p className="adm-muted">Cole a URL do feed de produtos (CSV, XML Google Shopping ou YML) de qualquer rede: CJ, Impact, Rakuten, Admitad, Webgains, Tradedoubler, Partnerize, Lomadee, ou de uma loja ou fornecedor parceiro. O motor importa, organiza e publica sozinho a cada ciclo.</p>
    <form className="adm-form" onSubmit={salvar}>
      <input required placeholder="Rede (ex.: cj, impact, admitad, loja-x)" value={f.rede} onChange={set("rede")} />
      <input required type="url" placeholder="URL https do feed" value={f.url} onChange={set("url")} />
      <input placeholder="Anunciante (se o feed é de uma só loja)" value={f.anunciante} onChange={set("anunciante")} />
      <input placeholder="Parâmetro de rastreio (CJ: sid · Impact: subId1 · Rakuten: u1 · Admitad: subid)" value={f.subid} onChange={set("subid")} />
      <input placeholder="Mercado (BR, US, PT…)" value={f.mercado} onChange={set("mercado")} />
      <input placeholder="Idioma (pt, en, es)" value={f.idioma} onChange={set("idioma")} />
      <button className="adm-btn">Adicionar fonte</button>
    </form>
    {(lista?.painel?.length || lista?.ambiente?.length) ? <table className="adm-table"><thead><tr><th>Rede</th><th>Feed</th><th>Mercado</th><th></th></tr></thead><tbody>
      {(lista.ambiente || []).map((x: Json, i: number) => <tr key={"e" + i}><td>{x.rede}</td><td className="adm-muted">{x.url}</td><td></td><td className="adm-muted">via Render</td></tr>)}
      {(lista.painel || []).map((x: Json) => <tr key={x.id}><td>{x.rede}{x.anunciante && <div className="adm-muted">{x.anunciante}</div>}</td><td className="adm-muted">{x.url}</td><td>{x.mercado}</td>
        <td><button className="adm-link" onClick={async () => { await run(`/admin/fontes/${x.id}`, { method: "DELETE" }, "Fonte removida."); reload(); }}>remover</button></td></tr>)}
    </tbody></table> : <p className="adm-muted">Nenhuma fonte universal cadastrada ainda (a Awin é configurada à parte).</p>}
  </Card>;
}
