"""Agente de catálogo com IA (Claude).

Transforma categorias técnicas das lojas ("Consumer Electronics > Headphones &
Earphones > Earbud Headphones") em poucos temas por NECESSIDADE, em português,
com tradução para inglês e espanhol, e religa os produtos a esses temas.

Custo amarrado às vendas (regra definida pelo dono do projeto):
- teto do teste: a IA gasta no máximo IA_TETO_TESTE_USD antes de existir venda;
- depois disso, só gasta o que as comissões pagam: o orçamento total é o teto do
  teste + IA_FRACAO_COMISSAO (ex.: 10%) de toda comissão aprovada até hoje;
- antes de cada chamada, confere se o pior custo possível da chamada cabe no saldo;
- após organizar o catálogo existente uma vez, só envia categorias de produtos que
  já tiveram clique ou venda (as demais ficam com o organizador gratuito, sem IA);
- cada categoria é enviada uma única vez (resultado guardado em rg_config);
- todo gasto fica registrado e aparece no painel ao lado de cliques, vendas e comissão.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .config import Settings
from .core import auditar, filtro_oferta_visivel, is_test_slug
from .models import utcnow
from .models import (
    Anunciante, Configuracao, Dor, DorOferta, MapeamentoCategoria, Nicho, Oferta, Subnicho, new_id,
)

log = logging.getLogger("robo.catalogo_ia")
AGENTE = "agente-ia"
CHAVE = "catalogo_ia"
MODELO = "claude-opus-5-5"
LOTE = 120
CATEGORIAS_POR_CICLO = 600
IDIOMAS = ("pt", "en", "es")
MAX_SAIDA = 16000
# Preço do modelo por milhão de tokens (US$), para registrar o gasto de cada chamada.
PRECO_ENTRADA_MTOK = 4.0
PRECO_SAIDA_MTOK = 20.0
# Pior caso por chamada: entrada estimada generosa + saída máxima.
ENTRADA_MAX_ESTIMADA = 20000
CUSTO_MAX_CHAMADA = (ENTRADA_MAX_ESTIMADA * PRECO_ENTRADA_MTOK + MAX_SAIDA * PRECO_SAIDA_MTOK) / 1_000_000


def custo_usd(entrada: int, saida: int) -> float:
    return (entrada * PRECO_ENTRADA_MTOK + saida * PRECO_SAIDA_MTOK) / 1_000_000

_CAMPOS_TEMA = ["chave"] + [f"{nivel}_{l}" for l in IDIOMAS for nivel in ("nicho", "subnicho", "dor", "descricao")] + ["palavras_pt"]

SCHEMA = {
    "type": "object",
    "properties": {
        "novos_temas": {"type": "array", "items": {
            "type": "object", "properties": {c: {"type": "string"} for c in _CAMPOS_TEMA},
            "required": _CAMPOS_TEMA, "additionalProperties": False}},
        "atribuicoes": {"type": "array", "items": {
            "type": "object", "properties": {"categoria": {"type": "string"}, "chave": {"type": "string"}},
            "required": ["categoria", "chave"], "additionalProperties": False}},
    },
    "required": ["novos_temas", "atribuicoes"],
    "additionalProperties": False,
}

SISTEMA = """Você organiza o catálogo do Robô Global, uma vitrine brasileira de produtos de lojas parceiras.
O público é brasileiro e navega por NECESSIDADE, não por código de loja.

Receberá categorias de produtos (geralmente em inglês, no formato "Pai > Filho > Neto") e a lista de temas já existentes.
Sua tarefa:
1. Atribua CADA categoria recebida a um tema. Reutilize um tema existente sempre que ele servir.
2. Crie um tema novo apenas quando nenhum existente servir. O catálogo inteiro deve ficar com poucos temas
   (idealmente 12 a 25 nichos no total, cada um com poucas dores). Agrupe categorias parecidas no mesmo tema.
3. Cada tema tem três níveis: nicho (área ampla, ex.: "Casa e Cozinha"), subnicho (ex.: "Limpeza") e
   dor (a necessidade da pessoa, curta e natural, ex.: "Limpar a casa com menos esforço").
4. Português do Brasil natural e correto; inglês e espanhol equivalentes (não literais).
5. descricao_*: uma frase curta e honesta sobre o que a pessoa encontra ali, sem promessas exageradas.
6. palavras_pt: termos que um brasileiro digitaria na busca, separados por vírgula (ex.: "fone, fone de ouvido, headphone").
7. chave: identificador curto, minúsculo, sem acento, com hífens (ex.: "casa-limpeza"), único.
8. Em "atribuicoes", copie o texto da categoria EXATAMENTE como recebido. Use apenas chaves existentes ou criadas nesta resposta.
Responda somente com o JSON pedido."""

Chamador = Callable[[str, str], dict[str, Any]]


def _chamador_claude(api_key: str) -> Chamador:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=300)

    def chamar(sistema: str, conteudo: str) -> dict[str, Any]:
        resp = client.beta.messages.create(
            model=MODELO,
            max_tokens=MAX_SAIDA,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=sistema,
            messages=[{"role": "user", "content": conteudo}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
        uso = {"entrada": resp.usage.input_tokens, "saida": resp.usage.output_tokens}
        if resp.stop_reason in ("refusal", "max_tokens"):
            return {"_uso": uso, "_erro": f"resposta incompleta: {resp.stop_reason}"}  # paga, mas sem uso
        texto = next(b.text for b in resp.content if b.type == "text")
        dados = json.loads(texto)
        dados["_uso"] = uso
        return dados

    return chamar


def _estado(db: Session) -> dict[str, Any]:
    row = db.get(Configuracao, CHAVE)
    v = json.loads(json.dumps(row.value)) if row and isinstance(row.value, dict) else {}
    v.setdefault("temas", {})
    v.setdefault("categorias", {})
    v.setdefault("dores", {})  # chave do tema -> id da dor criada
    v.setdefault("gasto_usd", 0.0)
    v.setdefault("gasto_por_mes", {})
    v.setdefault("chamadas", 0)
    v.setdefault("inicial_concluida", False)
    return v


def _taxa_brl(s: Settings) -> float:
    return s.ia_cotacao_usd_brl if s.ia_cotacao_usd_brl > 0 else 5.5


def comissoes_aprovadas_usd(db: Session, s: Settings) -> float:
    """Total de comissões aprovadas, convertido para dólar (BRL pela cotação configurada)."""
    from .models import Conversao
    total = 0.0
    for moeda, valor in db.execute(select(Conversao.currency, func.sum(Conversao.commission_amount))
                                   .where(Conversao.status == "approved").group_by(Conversao.currency)).all():
        v = float(valor or 0)
        if moeda == "USD":
            total += v
        elif moeda == "BRL":
            total += v / _taxa_brl(s)
        # outras moedas não contam (conservador: nunca aumenta o orçamento por engano)
    return round(total, 4)


def orcamento(db: Session, s: Settings, estado: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    estado = estado if estado is not None else _estado(db)
    comissao = comissoes_aprovadas_usd(db, s)
    limite = s.ia_teto_teste_usd + s.ia_fracao_comissao * comissao
    gasto = float(estado.get("gasto_usd", 0.0))
    return {"teto_teste_usd": s.ia_teto_teste_usd, "fracao_comissao": s.ia_fracao_comissao,
            "comissoes_aprovadas_usd": comissao, "limite_usd": round(limite, 4),
            "gasto_usd": round(gasto, 4), "saldo_usd": round(max(0.0, limite - gasto), 4),
            "gasto_por_mes": estado.get("gasto_por_mes", {}), "chamadas": estado.get("chamadas", 0)}


def _salvar(db: Session, estado: dict[str, Any]) -> None:
    row = db.get(Configuracao, CHAVE)
    if row is None:
        db.add(Configuracao(key=CHAVE, value=estado))
    else:
        row.value = estado
        flag_modified(row, "value")
    db.commit()


def _categorias_com_resultado(db: Session) -> set[str]:
    """Categorias cujos produtos já tiveram clique ou venda."""
    from .models import Clique, Conversao
    com_clique = select(Clique.oferta_id)
    com_venda = select(Conversao.oferta_id).where(Conversao.oferta_id.is_not(None))
    rows = db.scalars(select(Oferta.category).where(Oferta.category != "",
                                                    Oferta.id.in_(com_clique.union(com_venda))).distinct())
    return {c.lower() for c in rows}


def _categorias_pendentes(db: Session, feitas: dict[str, str]) -> list[str]:
    """Categorias que ainda não passaram pela IA: as já mapeadas pelo agente sem IA
    e as dos produtos no ar que ainda não têm tema."""
    from .conectores.feed_universal import parece_codigo

    mapeadas = db.scalars(select(MapeamentoCategoria.termo).where(MapeamentoCategoria.campo == "category_exact")).all()
    ligados = select(DorOferta.oferta_id)
    soltas = db.execute(
        select(Oferta.category, func.count())
        .outerjoin(Anunciante, Oferta.anunciante_id == Anunciante.id)
        .where(filtro_oferta_visivel(), Oferta.category != "", Oferta.id.not_in(ligados))
        .group_by(Oferta.category).order_by(func.count().desc()).limit(CATEGORIAS_POR_CICLO)).all()
    vistas: set[str] = set()
    out: list[str] = []
    for c in list(mapeadas) + [c for c, _ in soltas]:
        k = c.lower()
        if k in feitas or k in vistas or parece_codigo(c):
            continue
        vistas.add(k)
        out.append(c)
    return out[:CATEGORIAS_POR_CICLO]


def _resumo_temas(temas: dict[str, dict[str, str]]) -> str:
    if not temas:
        return "(nenhum tema ainda)"
    return "\n".join(f"- {k}: {t['nicho_pt']} › {t['subnicho_pt']} › {t['dor_pt']}" for k, t in sorted(temas.items()))


def _slug(texto: str) -> str:
    from .agentes import slugify
    return slugify(texto)


def _tr(t: dict[str, str], nivel: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for l in ("en", "es"):
        item = {"title": t.get(f"{nivel}_{l}", "")[:200]}
        if nivel == "dor":
            item["description"] = t.get(f"descricao_{l}", "")
        out[l] = item
    if nivel == "dor":
        out["pt"] = {"keywords": t.get("palavras_pt", "")[:500]}
    return out


def _obter(db: Session, model, title: str, traducoes: dict[str, Any], descricao: str = "", **pai: str):
    slug = _slug(title)
    obj = db.scalars(select(model).where(model.slug == slug, *[getattr(model, k) == v for k, v in pai.items()])).first()
    if obj is None:
        obj = model(id=new_id(), slug=slug, title=title[:200], description=descricao, translations=traducoes,
                    published=True, position=0, **pai)
        db.add(obj)
        db.flush()
        auditar(db, AGENTE, f"{model.__tablename__}.criado_ia", model.__tablename__, obj.id, {"titulo": title})
    else:
        obj.translations = traducoes
        if descricao:
            obj.description = descricao
        if not is_test_slug(obj.slug):
            obj.published = True
    return obj


def _dor_do_tema(db: Session, t: dict[str, str]) -> Dor:
    nicho = _obter(db, Nicho, t["nicho_pt"], _tr(t, "nicho"))
    sub = _obter(db, Subnicho, t["subnicho_pt"], _tr(t, "subnicho"), nicho_id=nicho.id)
    return _obter(db, Dor, t["dor_pt"], _tr(t, "dor"), t.get("descricao_pt", ""), subnicho_id=sub.id)


def _religar(db: Session, categoria: str, destino: Dor) -> tuple[int, Optional[str]]:
    """Aponta a regra da categoria para o novo tema e move os produtos já ligados."""
    m = db.scalars(select(MapeamentoCategoria).where(MapeamentoCategoria.campo == "category_exact",
                                                     func.lower(MapeamentoCategoria.termo) == categoria.lower())).first()
    antigo = None
    if m is None:
        db.add(MapeamentoCategoria(id=new_id(), termo=categoria, campo="category_exact", dor_id=destino.id))
        return 0, None
    if m.dor_id == destino.id:
        return 0, None
    antigo = m.dor_id
    ofertas = select(Oferta.id).where(func.lower(Oferta.category) == categoria.lower())
    ja_no_destino = select(DorOferta.oferta_id).where(DorOferta.dor_id == destino.id)
    movidos = db.execute(update(DorOferta)
                         .where(DorOferta.dor_id == antigo, DorOferta.oferta_id.in_(ofertas),
                                DorOferta.oferta_id.not_in(ja_no_destino))
                         .values(dor_id=destino.id).execution_options(synchronize_session=False)).rowcount or 0
    outra = db.scalars(select(MapeamentoCategoria).where(MapeamentoCategoria.termo == m.termo,
                                                         MapeamentoCategoria.dor_id == destino.id)).first()
    if outra is not None:
        db.delete(m)
    else:
        m.dor_id = destino.id
    return movidos, antigo


def _recolher_vazios(db: Session, dores_antigas: set[str]) -> int:
    """Tira do ar os temas antigos (criados sem IA) que ficaram sem produtos e sem regra."""
    recolhidos = 0
    for dor_id in dores_antigas:
        d = db.get(Dor, dor_id)
        if d is None or not d.published or is_test_slug(d.slug):
            continue
        tem_produto = db.scalar(select(func.count()).select_from(DorOferta).where(DorOferta.dor_id == d.id))
        tem_regra = db.scalar(select(func.count()).select_from(MapeamentoCategoria).where(MapeamentoCategoria.dor_id == d.id))
        if tem_produto or tem_regra:
            continue
        d.published = False
        recolhidos += 1
        sub = d.subnicho
        if sub and not any(x.published for x in sub.dores):
            sub.published = False
            nicho = sub.nicho
            if nicho and not any(s.published for s in nicho.subnichos):
                nicho.published = False
    return recolhidos


def organizar_com_ia(db: Session, s: Settings, chamar: Optional[Chamador] = None) -> dict[str, Any]:
    if chamar is None:
        if not s.anthropic_api_key:
            return {"status": "sem_chave"}
        chamar = _chamador_claude(s.anthropic_api_key)
    estado = _estado(db)
    pendentes = _categorias_pendentes(db, estado["categorias"])
    if not pendentes and not estado["inicial_concluida"]:
        estado["inicial_concluida"] = True
        _salvar(db, estado)
    if estado["inicial_concluida"]:
        # Depois da organização inicial: só gasta com o que já mostrou interesse real.
        com_resultado = _categorias_com_resultado(db)
        pendentes = [c for c in pendentes if c.lower() in com_resultado]
    out: dict[str, Any] = {"categorias_enviadas": 0, "temas_novos": 0, "produtos_movidos": 0,
                           "temas_antigos_recolhidos": 0, "tokens_entrada": 0, "tokens_saida": 0,
                           "custo_usd": 0.0}
    if not pendentes:
        out["orcamento"] = orcamento(db, s, estado)
        return out
    dores_antigas: set[str] = set()
    for i in range(0, len(pendentes), LOTE):
        lote = pendentes[i:i + LOTE]
        conteudo = ("Temas existentes:\n" + _resumo_temas(estado["temas"]) +
                    "\n\nCategorias para atribuir (uma por linha):\n" + "\n".join(lote))
        if orcamento(db, s, estado)["saldo_usd"] < CUSTO_MAX_CHAMADA:
            out["status"] = "orcamento_esgotado"  # só volta a gastar quando entrar comissão
            break
        resp = chamar(SISTEMA, conteudo)
        uso = resp.get("_uso") or {}
        e, sa = int(uso.get("entrada", 0)), int(uso.get("saida", 0))
        custo = custo_usd(e, sa)
        mes = utcnow().strftime("%Y-%m")
        estado["gasto_usd"] = round(float(estado["gasto_usd"]) + custo, 6)
        estado["gasto_por_mes"][mes] = round(float(estado["gasto_por_mes"].get(mes, 0.0)) + custo, 6)
        estado["chamadas"] = int(estado["chamadas"]) + 1
        out["tokens_entrada"] += e
        out["tokens_saida"] += sa
        out["custo_usd"] = round(out["custo_usd"] + custo, 6)
        if resp.get("_erro"):
            _salvar(db, estado)
            raise RuntimeError(str(resp["_erro"]))
        out["categorias_enviadas"] += len(lote)
        for t in resp.get("novos_temas", []):
            k = _slug(str(t.get("chave", "")))
            if k and all(str(t.get(c, "")).strip() for c in ("nicho_pt", "subnicho_pt", "dor_pt")) and k not in estado["temas"]:
                estado["temas"][k] = {c: str(t.get(c, "")).strip() for c in _CAMPOS_TEMA if c != "chave"}
                out["temas_novos"] += 1
        pedidas = {c.lower(): c for c in lote}
        for a in resp.get("atribuicoes", []):
            original = pedidas.get(str(a.get("categoria", "")).strip().lower())
            k = _slug(str(a.get("chave", "")))
            if original is None or k not in estado["temas"]:
                continue
            dor = _dor_do_tema(db, estado["temas"][k])
            estado["dores"][k] = dor.id
            movidos, antigo = _religar(db, original, dor)
            out["produtos_movidos"] += movidos
            if antigo:
                dores_antigas.add(antigo)
            estado["categorias"][original.lower()] = k
        db.commit()
        _salvar(db, estado)  # salva a cada lote: o que já foi pago não é reenviado
    out["temas_antigos_recolhidos"] = _recolher_vazios(db, dores_antigas)
    db.commit()
    from .aquisicao import aplicar_mapeamentos
    out["vinculos_criados"] = aplicar_mapeamentos(db)
    out["temas_total"] = len(estado["temas"])
    out["orcamento"] = orcamento(db, s, estado)
    auditar(db, AGENTE, "catalogo.organizado_ia", "catalogo", CHAVE,
            {k: v for k, v in out.items() if isinstance(v, (int, float))})
    db.commit()
    return out


# ------------------------------------------------------------------ títulos da vitrine

SCHEMA_TITULOS = {
    "type": "object",
    "properties": {"itens": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "pt": {"type": "string"}, "es": {"type": "string"}},
        "required": ["id", "pt", "es"], "additionalProperties": False}}},
    "required": ["itens"], "additionalProperties": False,
}
SISTEMA_TITULOS = """Você escreve títulos de produtos para uma vitrine brasileira.
Para cada produto recebido (id e título original, em geral em inglês e cheio de palavras-chave), escreva:
- pt: título curto e natural em português do Brasil (até 70 caracteres), dizendo claramente o que é o produto;
- es: o equivalente em espanhol.
Sem exageros nem promessas, sem marcas inventadas, sem emojis. Mantenha medidas e quantidades relevantes.
Devolva todos os ids recebidos, exatamente como vieram."""
LOTE_TITULOS = 60


def _chamador_titulos(api_key: str) -> Chamador:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=300)

    def chamar(sistema: str, conteudo: str) -> dict[str, Any]:
        resp = client.beta.messages.create(
            model=MODELO, max_tokens=MAX_SAIDA,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=sistema, messages=[{"role": "user", "content": conteudo}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA_TITULOS}},
        )
        uso = {"entrada": resp.usage.input_tokens, "saida": resp.usage.output_tokens}
        if resp.stop_reason in ("refusal", "max_tokens"):
            return {"_uso": uso, "_erro": f"resposta incompleta: {resp.stop_reason}"}
        dados = json.loads(next(b.text for b in resp.content if b.type == "text"))
        dados["_uso"] = uso
        return dados

    return chamar


def _registrar_gasto(estado: dict[str, Any], resp: dict[str, Any]) -> float:
    uso = resp.get("_uso") or {}
    custo = custo_usd(int(uso.get("entrada", 0)), int(uso.get("saida", 0)))
    mes = utcnow().strftime("%Y-%m")
    estado["gasto_usd"] = round(float(estado["gasto_usd"]) + custo, 6)
    estado["gasto_por_mes"][mes] = round(float(estado["gasto_por_mes"].get(mes, 0.0)) + custo, 6)
    estado["chamadas"] = int(estado["chamadas"]) + 1
    return custo


def traduzir_vitrine(db: Session, s: Settings, chamar: Optional[Chamador] = None) -> dict[str, Any]:
    """Traduz só os títulos dos produtos que estão na vitrine (o que o público vê primeiro),
    dentro do mesmo orçamento amarrado às vendas."""
    from . import vitrine
    if chamar is None:
        if not s.anthropic_api_key:
            return {"status": "sem_chave"}
        chamar = _chamador_titulos(s.anthropic_api_key)
    ids = vitrine.ids_em_vitrine(db)
    pendentes = [o for o in db.scalars(select(Oferta).where(Oferta.id.in_(ids)))
                 if not ((o.translations or {}).get("pt") or {}).get("title")] if ids else []
    out: dict[str, Any] = {"titulos_traduzidos": 0, "custo_usd": 0.0}
    estado = _estado(db)
    for i in range(0, len(pendentes), LOTE_TITULOS):
        if orcamento(db, s, estado)["saldo_usd"] < CUSTO_MAX_CHAMADA:
            out["status"] = "orcamento_esgotado"
            break
        lote = pendentes[i:i + LOTE_TITULOS]
        resp = chamar(SISTEMA_TITULOS, "\n".join(f"{o.id}\t{o.title}" for o in lote))
        out["custo_usd"] = round(out["custo_usd"] + _registrar_gasto(estado, resp), 6)
        _salvar(db, estado)
        if resp.get("_erro"):
            raise RuntimeError(str(resp["_erro"]))
        por_id = {o.id: o for o in lote}
        for item in resp.get("itens", []):
            o = por_id.get(str(item.get("id", "")))
            pt, es = str(item.get("pt", "")).strip()[:200], str(item.get("es", "")).strip()[:200]
            if o is None or not pt:
                continue
            tr = dict(o.translations or {})
            tr["pt"] = {**(tr.get("pt") or {}), "title": pt}
            if es:
                tr["es"] = {**(tr.get("es") or {}), "title": es}
            o.translations = tr
            flag_modified(o, "translations")
            out["titulos_traduzidos"] += 1
        db.commit()
    if out["titulos_traduzidos"]:
        vitrine.limpar_cache()
        auditar(db, AGENTE, "vitrine.titulos_ia", "vitrine", "titulos", out)
        db.commit()
    return out
