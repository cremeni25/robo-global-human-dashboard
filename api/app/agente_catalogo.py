"""Agente de catálogo com IA (Claude).

Transforma categorias técnicas das lojas ("Consumer Electronics > Headphones &
Earphones > Earbud Headphones") em poucos temas por NECESSIDADE, em português,
com tradução para inglês e espanhol, e religa os produtos a esses temas.

Controle de custo:
- cada categoria é enviada à IA uma única vez (resultado guardado em rg_config);
- no máximo CATEGORIAS_POR_CICLO categorias por ciclo, em lotes;
- sem ANTHROPIC_API_KEY o agente simplesmente não roda (o organizador sem IA assume).
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
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=sistema,
            messages=[{"role": "user", "content": conteudo}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
        if resp.stop_reason in ("refusal", "max_tokens"):
            raise RuntimeError(f"resposta incompleta: {resp.stop_reason}")
        texto = next(b.text for b in resp.content if b.type == "text")
        dados = json.loads(texto)
        dados["_uso"] = {"entrada": resp.usage.input_tokens, "saida": resp.usage.output_tokens}
        return dados

    return chamar


def _estado(db: Session) -> dict[str, Any]:
    row = db.get(Configuracao, CHAVE)
    v = json.loads(json.dumps(row.value)) if row and isinstance(row.value, dict) else {}
    v.setdefault("temas", {})
    v.setdefault("categorias", {})
    v.setdefault("dores", {})  # chave do tema -> id da dor criada
    return v


def _salvar(db: Session, estado: dict[str, Any]) -> None:
    row = db.get(Configuracao, CHAVE)
    if row is None:
        db.add(Configuracao(key=CHAVE, value=estado))
    else:
        row.value = estado
        flag_modified(row, "value")
    db.commit()


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
    out: dict[str, Any] = {"categorias_enviadas": 0, "temas_novos": 0, "produtos_movidos": 0,
                           "temas_antigos_recolhidos": 0, "tokens_entrada": 0, "tokens_saida": 0}
    if not pendentes:
        return out
    dores_antigas: set[str] = set()
    for i in range(0, len(pendentes), LOTE):
        lote = pendentes[i:i + LOTE]
        conteudo = ("Temas existentes:\n" + _resumo_temas(estado["temas"]) +
                    "\n\nCategorias para atribuir (uma por linha):\n" + "\n".join(lote))
        resp = chamar(SISTEMA, conteudo)
        uso = resp.get("_uso") or {}
        out["tokens_entrada"] += int(uso.get("entrada", 0))
        out["tokens_saida"] += int(uso.get("saida", 0))
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
    auditar(db, AGENTE, "catalogo.organizado_ia", "catalogo", CHAVE,
            {k: v for k, v in out.items() if isinstance(v, int)})
    db.commit()
    return out
