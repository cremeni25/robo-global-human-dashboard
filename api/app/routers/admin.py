"""Operação humana. Toda rota exige token e toda escrita é auditada."""
from __future__ import annotations

import csv
import io
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..conversions import STATUSES, ConversaoIn, registrar, to_decimal
from ..core import (
    auditar, definir_sistema, is_safe_url, is_test_slug, nicho_visivel, sistema,
    subnicho_visivel,
)
from ..db import get_db
from ..inteligencia import aplicar_decisao, demanda_dores, gerar_decisoes, metricas_ofertas, resumo_humano
from ..models import (
    Auditoria, Conversao, Decisao, Dor, DorOferta, Lead, Nicho, Oferta, Subnicho, new_id,
)
from ..security import require_admin
from .webhooks import ConversaoPayload

router = APIRouter(prefix="/admin")
SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def _commit(db: Session, conflict: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=conflict)


def _row(obj) -> dict[str, Any]:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# ------------------------------------------------------------------ leitura humana

@router.get("/resumo")
def resumo(request: Request, db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    data = resumo_humano(db, request.app.state.settings)
    data["sistema"] = sistema(db)
    data["operador"] = actor
    return data


@router.get("/metricas")
def metricas(days: Optional[int] = Query(default=None, ge=1, le=3650),
             db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return {"ofertas": metricas_ofertas(db, days), "dores": demanda_dores(db)}


# ------------------------------------------------------------------ catálogo

class EditorialIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=140, pattern=SLUG)
    description: str = Field(default="", max_length=4000)
    translations: dict[str, dict[str, str]] = Field(default_factory=dict)
    position: int = 0
    parent_id: Optional[str] = None  # nicho_id para subnicho, subnicho_id para dor


class EditorialPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)
    translations: Optional[dict[str, dict[str, str]]] = None
    position: Optional[int] = None
    published: Optional[bool] = None


NIVEIS: dict[str, Any] = {"nichos": Nicho, "subnichos": Subnicho, "dores": Dor}


@router.get("/catalogo")
def catalogo(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    out = []
    for n in sorted(db.scalars(select(Nicho)), key=lambda x: (x.position, x.title.lower())):
        subs = []
        for s in sorted(n.subnichos, key=lambda x: (x.position, x.title.lower())):
            subs.append({**_row(s), "dores": [
                {**_row(d), "vinculos": [{"id": v.id, "oferta_id": v.oferta_id, "priority": v.priority,
                                          "oferta": v.oferta.title} for v in d.vinculos]}
                for d in sorted(s.dores, key=lambda x: (x.position, x.title.lower()))]})
        out.append({**_row(n), "subnichos": subs})
    return {"data": out}


@router.post("/catalogo/{nivel}", status_code=201)
def criar_editorial(nivel: Literal["nichos", "subnichos", "dores"], payload: EditorialIn,
                    db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    fields = payload.model_dump(exclude={"parent_id"})
    if nivel == "nichos":
        obj = Nicho(**fields)
        obj.id = new_id()
    else:
        parent_model = Nicho if nivel == "subnichos" else Subnicho
        if not payload.parent_id or not db.get(parent_model, payload.parent_id):
            raise HTTPException(status_code=404, detail="Item pai nao encontrado")
        key = "nicho_id" if nivel == "subnichos" else "subnicho_id"
        obj = NIVEIS[nivel](**fields, **{key: payload.parent_id})
    obj.id = new_id()
    db.add(obj)
    auditar(db, actor, f"{nivel}.criado", nivel, obj.id or "", {"slug": payload.slug})
    _commit(db, "Slug ja existe neste nivel")
    return _row(obj)


@router.patch("/catalogo/{nivel}/{item_id}")
def editar_editorial(nivel: Literal["nichos", "subnichos", "dores"], item_id: str,
                     payload: EditorialPatch, db: Session = Depends(get_db),
                     actor: str = Depends(require_admin)):
    obj = db.get(NIVEIS[nivel], item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Registro nao encontrado")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("published"):
        if is_test_slug(obj.slug):
            raise HTTPException(status_code=409, detail="Registros de teste nao podem ser publicados")
        if nivel == "subnichos" and not nicho_visivel(obj.nicho):
            raise HTTPException(status_code=409, detail="Publique primeiro o nicho")
        if nivel == "dores" and not subnicho_visivel(obj.subnicho):
            raise HTTPException(status_code=409, detail="Publique primeiro o subnicho e o nicho")
    for k, v in changes.items():
        setattr(obj, k, v)
    auditar(db, actor, f"{nivel}.editado", nivel, obj.id, changes)
    _commit(db, "Conflito ao salvar")
    return _row(obj)


# ------------------------------------------------------------------ ofertas

Kind = Literal["afiliado", "produto_proprio", "servico", "lead_parceiro"]


class OfertaIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    destination_url: str = Field(max_length=2000)
    description: str = Field(default="", max_length=4000)
    translations: dict[str, dict[str, str]] = Field(default_factory=dict)
    kind: Kind = "afiliado"
    platform: str = Field(default="manual", min_length=2, max_length=40)
    provider: str = Field(default="", max_length=200)
    subid_param: Optional[str] = Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9_]+$")
    external_product_id: Optional[str] = Field(default=None, max_length=120)
    market: str = Field(default="BR", max_length=10)
    language: str = Field(default="pt", max_length=10)
    currency: str = Field(default="BRL", max_length=3)
    commission_estimate: float = 0
    image_url: str = Field(default="", max_length=2000)


class OfertaPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    destination_url: Optional[str] = Field(default=None, max_length=2000)
    description: Optional[str] = Field(default=None, max_length=4000)
    translations: Optional[dict[str, dict[str, str]]] = None
    kind: Optional[Kind] = None
    platform: Optional[str] = Field(default=None, min_length=2, max_length=40)
    provider: Optional[str] = Field(default=None, max_length=200)
    subid_param: Optional[str] = Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9_]*$")
    external_product_id: Optional[str] = Field(default=None, max_length=120)
    market: Optional[str] = Field(default=None, max_length=10)
    language: Optional[str] = Field(default=None, max_length=10)
    commission_estimate: Optional[float] = None
    image_url: Optional[str] = Field(default=None, max_length=2000)
    active: Optional[bool] = None
    published: Optional[bool] = None


def _check_url(url: Optional[str]):
    if url is not None and not is_safe_url(url):
        raise HTTPException(status_code=422, detail="O link de destino precisa comecar com https://")


@router.get("/ofertas")
def listar_ofertas(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return {"data": [_row(o) for o in db.scalars(select(Oferta).order_by(Oferta.title))]}


@router.post("/ofertas", status_code=201)
def criar_oferta(payload: OfertaIn, db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    _check_url(payload.destination_url)
    data = payload.model_dump()
    data["platform"] = data["platform"].lower()
    data["commission_estimate"] = to_decimal(data["commission_estimate"])
    o = Oferta(id=new_id(), **data)
    db.add(o)
    auditar(db, actor, "oferta.criada", "oferta", o.id, {"title": o.title})
    _commit(db, "Conflito ao salvar oferta")
    return _row(o)


@router.patch("/ofertas/{oferta_id}")
def editar_oferta(oferta_id: str, payload: OfertaPatch, db: Session = Depends(get_db),
                  actor: str = Depends(require_admin)):
    o = db.get(Oferta, oferta_id)
    if not o:
        raise HTTPException(status_code=404, detail="Oferta nao encontrada")
    changes = payload.model_dump(exclude_unset=True)
    _check_url(changes.get("destination_url"))
    if "commission_estimate" in changes:
        changes["commission_estimate"] = to_decimal(changes["commission_estimate"])
    if "platform" in changes:
        changes["platform"] = changes["platform"].lower()
    if changes.get("subid_param") == "":
        changes["subid_param"] = None
    for k, v in changes.items():
        setattr(o, k, v)
    if o.published and not is_safe_url(o.destination_url):
        raise HTTPException(status_code=409, detail="Oferta sem link https valido nao pode ser publicada")
    auditar(db, actor, "oferta.editada", "oferta", o.id,
            {k: (str(v) if k == "commission_estimate" else v) for k, v in changes.items()})
    _commit(db, "Conflito ao salvar oferta")
    return _row(o)


class VinculoIn(BaseModel):
    dor_id: str
    oferta_id: str
    priority: int = Field(default=1, ge=0, le=1000)


@router.post("/vinculos", status_code=201)
def vincular(payload: VinculoIn, db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    if not db.get(Dor, payload.dor_id) or not db.get(Oferta, payload.oferta_id):
        raise HTTPException(status_code=404, detail="Dor ou oferta nao encontrada")
    v = DorOferta(id=new_id(), **payload.model_dump())
    db.add(v)
    auditar(db, actor, "vinculo.criado", "vinculo", v.id, payload.model_dump())
    _commit(db, "Esta oferta ja esta vinculada a esta dor")
    return _row(v)


@router.delete("/vinculos/{vinculo_id}")
def desvincular(vinculo_id: str, db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    v = db.get(DorOferta, vinculo_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vinculo nao encontrado")
    auditar(db, actor, "vinculo.removido", "vinculo", v.id, {"dor_id": v.dor_id, "oferta_id": v.oferta_id})
    db.delete(v)
    db.commit()
    return {"status": "OK"}


# ------------------------------------------------------------------ conversões

@router.get("/conversoes")
def listar_conversoes(limit: int = Query(default=100, ge=1, le=1000),
                      db: Session = Depends(get_db), _: str = Depends(require_admin)):
    rows = db.scalars(select(Conversao).order_by(Conversao.occurred_at.desc()).limit(limit))
    return {"data": [_row(c) for c in rows]}


@router.post("/conversoes", status_code=201)
def conversao_manual(payload: ConversaoPayload, db: Session = Depends(get_db),
                     actor: str = Depends(require_admin)):
    """Lançamento manual a partir do relatório da plataforma."""
    r = registrar(db, payload.to_in("manual"))
    auditar(db, actor, "conversao.manual", "conversao", r.conversao.id,
            {"external_id": payload.external_id, "status": payload.status, "alterada": r.alterada})
    db.commit()
    return {"criada": r.criada, "alterada": r.alterada, "conversao": _row(r.conversao)}


CSV_COLUMNS = ("platform", "external_id", "status", "gross_amount", "commission_amount",
               "currency", "occurred_at", "product_id", "click_id", "oferta_id")


@router.post("/conversoes/importar")
async def importar_csv(request: Request, db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    """Importa CSV (cabeçalho: platform,external_id,status,commission_amount,...).
    Reimportar o mesmo arquivo não duplica vendas."""
    body = (await request.body()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(body))
    if not reader.fieldnames or not {"platform", "external_id", "status"} <= set(reader.fieldnames):
        raise HTTPException(status_code=422, detail="CSV precisa das colunas platform, external_id e status")
    resumo = {"criadas": 0, "atualizadas": 0, "duplicadas": 0, "erros": []}
    for n, line in enumerate(reader, start=2):
        try:
            row = {k: (line.get(k) or "").strip() for k in CSV_COLUMNS}
            if row["status"] not in STATUSES:
                raise ValueError(f"status invalido '{row['status']}'")
            p = ConversaoPayload(**{k: v for k, v in row.items() if v != ""})
            r = registrar(db, p.to_in("csv", raw={"linha": n, **row}))
            key = "criadas" if r.criada else "atualizadas" if r.alterada else "duplicadas"
            resumo[key] += 1
        except Exception as exc:  # erro por linha não interrompe o restante
            db.rollback()
            resumo["erros"].append({"linha": n, "erro": str(exc)[:200]})
    auditar(db, actor, "conversao.csv", "conversao", "", {k: v for k, v in resumo.items() if k != "erros"})
    db.commit()
    return resumo


# ------------------------------------------------------------------ leads

@router.get("/leads")
def listar_leads(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    rows = db.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(2000))
    return {"data": [_row(x) for x in rows]}


@router.get("/leads.csv", response_class=PlainTextResponse)
def exportar_leads(db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["email", "nome", "dor", "idioma", "criado_em"])
    for lead in db.scalars(select(Lead).order_by(Lead.created_at)):
        dor = db.get(Dor, lead.dor_id) if lead.dor_id else None
        w.writerow([lead.email, lead.name, dor.title if dor else "", lead.language, lead.created_at.isoformat()])
    auditar(db, actor, "leads.exportados")
    db.commit()
    return PlainTextResponse(out.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=leads.csv"})


# ------------------------------------------------------------------ decisões

@router.get("/decisoes")
def listar_decisoes(status: Optional[str] = None, db: Session = Depends(get_db),
                    _: str = Depends(require_admin)):
    q = select(Decisao).order_by(Decisao.created_at.desc()).limit(200)
    if status:
        q = q.where(Decisao.status == status)
    out = []
    for d in db.scalars(q):
        o = db.get(Oferta, d.oferta_id)
        out.append({**_row(d), "oferta": o.title if o else ""})
    return {"data": out}


@router.post("/decisoes/gerar")
def gerar(request: Request, db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    criadas = gerar_decisoes(db, request.app.state.settings, actor)
    return {"criadas": len(criadas)}


class DecisaoAcao(BaseModel):
    nota: str = Field(default="", max_length=1000)


@router.post("/decisoes/{decisao_id}/{acao}")
def decidir(decisao_id: str, acao: Literal["aprovar", "rejeitar"], payload: DecisaoAcao,
            db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    d = db.get(Decisao, decisao_id)
    if not d:
        raise HTTPException(status_code=404, detail="Decisao nao encontrada")
    try:
        aplicar_decisao(db, d, aprovar=acao == "aprovar", actor=actor, nota=payload.nota)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _row(d)


# ------------------------------------------------------------------ sistema

class SistemaIn(BaseModel):
    ativo: bool
    motivo: str = Field(default="", max_length=500)


@router.get("/sistema")
def ver_sistema(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return sistema(db)


@router.put("/sistema")
def alterar_sistema(payload: SistemaIn, db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    return definir_sistema(db, ativo=payload.ativo, motivo=payload.motivo, actor=actor)


@router.get("/auditoria")
def auditoria(limit: int = Query(default=200, ge=1, le=1000), db: Session = Depends(get_db),
              _: str = Depends(require_admin)):
    rows = db.scalars(select(Auditoria).order_by(Auditoria.created_at.desc()).limit(limit))
    return {"data": [_row(a) for a in rows]}
