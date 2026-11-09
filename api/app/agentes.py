"""Agentes autônomos do Robô Global.

Executam, a cada ciclo, as decisões que antes esperavam uma pessoa. Toda ação
fica na auditoria com o autor "agente", e cada agente pode ser desligado por
variável de ambiente (ver config.py). Guardas que permanecem, por segurança:
- só vai ao ar produto de anunciante cuja afiliação a própria rede confirmou;
- só vai ao ar link https;
- o botão de pausa geral continua valendo para tudo.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Settings
from .core import auditar, filtro_oferta_visivel, is_test_slug
from .inteligencia import aplicar_decisao, gerar_decisoes
from .models import (
    Anunciante, Decisao, Dor, DorOferta, MapeamentoCategoria, Nicho, Oferta, Subnicho, new_id,
)

AGENTE = "agente"


def slugify(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return (t or "outros")[:120]


def aprovar_anunciantes(db: Session) -> int:
    """Anunciante com afiliação confirmada pela rede ('joined') é liberado."""
    pendentes = db.scalars(select(Anunciante).where(Anunciante.membership == "joined",
                                                    Anunciante.approved.is_(False))).all()
    for a in pendentes:
        a.approved = True
        a.notes = (a.notes + " | " if a.notes else "") + "aprovado automaticamente: afiliacao confirmada pela rede"
        auditar(db, AGENTE, "anunciante.aprovado_auto", "anunciante", a.id, {"nome": a.name})
    db.commit()
    return len(pendentes)


def _partes(categoria: str) -> tuple[str, str, str]:
    partes = [p.strip() for p in re.split(r">|/|\|", categoria) if p.strip()]
    if not partes:
        return "Outros", "Outros", "Outros"
    if len(partes) == 1:
        return partes[0], partes[0], partes[0]
    if len(partes) == 2:
        return partes[0], partes[1], partes[1]
    return partes[0], partes[1], partes[-1]


def _obter(db: Session, model, title: str, **parent: str):
    slug = slugify(title)
    q = select(model).where(model.slug == slug, *[getattr(model, k) == v for k, v in parent.items()])
    obj = db.scalars(q).first()
    if obj is None:
        obj = model(id=new_id(), slug=slug, title=title[:200], description="", translations={},
                    published=True, position=0, **parent)
        db.add(obj)
        db.flush()
        auditar(db, AGENTE, f"{model.__tablename__}.criado_auto", model.__tablename__, obj.id, {"titulo": title})
    elif not obj.published and not is_test_slug(obj.slug):
        obj.published = True
    return obj


def organizar_taxonomia(db: Session, limite: int = 500) -> dict[str, int]:
    """Cada categoria de produto sem regra vira nicho › subnicho › dor publicados,
    com regra automática: produtos atuais e futuros da categoria entram na dor."""
    ligados = select(DorOferta.oferta_id)
    # Só produtos que estão de fato no ar: nunca criar uma dor pública vazia.
    categorias = db.execute(
        select(Oferta.category, func.count())
        .outerjoin(Anunciante, Oferta.anunciante_id == Anunciante.id)
        .where(filtro_oferta_visivel(), Oferta.category != "", Oferta.id.not_in(ligados))
        .group_by(Oferta.category).order_by(func.count().desc()).limit(limite)).all()
    existentes = {m.termo.lower() for m in db.scalars(select(MapeamentoCategoria))}
    criadas = 0
    for categoria, _n in categorias:
        if categoria.lower() in existentes:
            continue
        n_title, s_title, d_title = _partes(categoria)
        nicho = _obter(db, Nicho, n_title)
        sub = _obter(db, Subnicho, s_title, nicho_id=nicho.id)
        dor = _obter(db, Dor, d_title, subnicho_id=sub.id)
        db.add(MapeamentoCategoria(id=new_id(), termo=categoria, campo="category", dor_id=dor.id))
        existentes.add(categoria.lower())
        criadas += 1
    db.commit()
    from .aquisicao import aplicar_mapeamentos
    return {"categorias_organizadas": criadas, "vinculos_criados": aplicar_mapeamentos(db) if criadas else 0}


def decidir(db: Session, s: Settings) -> dict[str, int]:
    gerar_decisoes(db, s, AGENTE)
    aplicadas = 0
    for d in db.scalars(select(Decisao).where(Decisao.status == "pendente")).all():
        if d.recomendacao in ("PAUSAR", "ESCALAR", "OTIMIZAR"):
            aplicar_decisao(db, d, aprovar=True, actor=AGENTE, nota="aplicada automaticamente")
            aplicadas += 1
    return {"decisoes_aplicadas": aplicadas}


def executar(db: Session, s: Settings) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if s.auto_aprovar_anunciantes:
        out["anunciantes_aprovados"] = aprovar_anunciantes(db)
    if s.auto_taxonomia:
        out.update(organizar_taxonomia(db))
    if s.auto_decisoes:
        out.update(decidir(db, s))
    return out
