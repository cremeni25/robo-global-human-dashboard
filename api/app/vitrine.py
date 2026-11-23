"""Vitrine pública: o que o visitante vê primeiro, em qualquer tela.

Seleciona, entre os produtos no ar, seções por tema (um tema por nicho, os mais
fartos primeiro) e "achados até R$ 50". A seleção gira uma vez por semana: o
visitante que volta vê novidades, e a tradução dos títulos (paga) não é refeita
a cada hora.
"""
from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .core import select_ofertas_visiveis
from .models import Dor, DorOferta, Nicho, Oferta, Subnicho

SECOES = 8
ITENS = 8
ACHADOS = 12
CANDIDATOS = 300
_cache: dict[str, Any] = {"ts": 0.0, "data": None}
_lock = threading.Lock()


def _semente() -> str:
    ano, semana, _ = datetime.now(timezone.utc).isocalendar()
    return f"{ano}-{semana}"


def _amostra(ids: list[str], n: int, chave: str) -> list[str]:
    rnd = random.Random(_semente() + chave)
    return rnd.sample(ids, min(n, len(ids)))


def _com_foto_e_preco(q):
    return q.where(Oferta.image_url != "", Oferta.price.is_not(None), Oferta.price > 0)


def montar(db: Session) -> dict[str, Any]:
    visiveis = select_ofertas_visiveis().subquery()
    contagem = (select(DorOferta.dor_id, func.count().label("n"))
                .join(visiveis, visiveis.c.id == DorOferta.oferta_id)
                .group_by(DorOferta.dor_id).subquery())
    linhas = db.execute(
        select(Dor, Subnicho, Nicho, contagem.c.n)
        .join(contagem, contagem.c.dor_id == Dor.id)
        .join(Subnicho, Subnicho.id == Dor.subnicho_id).join(Nicho, Nicho.id == Subnicho.nicho_id)
        .where(Dor.published.is_(True), Subnicho.published.is_(True), Nicho.published.is_(True))
        .order_by(contagem.c.n.desc())).all()
    escolhidas, nichos_usados = [], set()
    for dor, sub, nicho, n in linhas:
        if nicho.id in nichos_usados or n < 4:
            continue
        nichos_usados.add(nicho.id)
        escolhidas.append((dor, nicho, n))
    escolhidas = _amostra(escolhidas, SECOES, "secoes") if len(escolhidas) > SECOES else escolhidas

    secoes = []
    for dor, nicho, n in escolhidas:
        ids = db.scalars(_com_foto_e_preco(select_ofertas_visiveis().with_only_columns(Oferta.id)
                                           .join(DorOferta, DorOferta.oferta_id == Oferta.id)
                                           .where(DorOferta.dor_id == dor.id))
                         .order_by(DorOferta.priority.desc(), Oferta.id).limit(CANDIDATOS)).all()
        itens = _amostra(list(ids), ITENS, dor.id)
        if len(itens) >= 4:
            secoes.append({"dor": _editorial(dor), "nicho": _editorial(nicho), "total": n, "itens": itens})

    baratos = db.scalars(_com_foto_e_preco(select_ofertas_visiveis().with_only_columns(Oferta.id))
                         .where(Oferta.currency == "BRL", Oferta.price <= Decimal("50"))
                         .order_by(Oferta.id).limit(CANDIDATOS * 4)).all()
    achados = _amostra(list(baratos), ACHADOS, "achados")

    todos = {i for s in secoes for i in s["itens"]} | set(achados)
    ofertas = {o.id: o for o in db.scalars(select(Oferta).where(Oferta.id.in_(todos)))} if todos else {}
    from .routers.public import _oferta
    def lista(ids):
        return [_oferta(ofertas[i]) for i in ids if i in ofertas]
    return {"status": "OK", "semana": _semente(),
            "achados": lista(achados),
            "secoes": [{**{k: v for k, v in s.items() if k != "itens"}, "itens": lista(s["itens"])} for s in secoes]}


def _editorial(x) -> dict[str, Any]:
    return {"id": x.id, "slug": x.slug, "title": x.title, "description": x.description,
            "translations": x.translations or {}}


def ids_em_vitrine(db: Session) -> list[str]:
    data = obter(db, renovar=True)
    return [o["id"] for o in data["achados"]] + [o["id"] for s in data["secoes"] for o in s["itens"]]


def obter(db: Session, renovar: bool = False, ttl: float = 600) -> dict[str, Any]:
    with _lock:
        if not renovar and _cache["data"] is not None and time.time() - _cache["ts"] < ttl:
            return _cache["data"]
    data = montar(db)
    with _lock:
        _cache.update(ts=time.time(), data=data)
    return data


def limpar_cache() -> None:
    with _lock:
        _cache.update(ts=0.0, data=None)
