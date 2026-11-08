"""Rotas públicas: catálogo, redirecionamento rastreado e captura de demanda.

Os caminhos são compatíveis com o frontend existente (B1)."""
from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core import (
    dor_visivel, nicho_visivel, nichos_publicos, oferta_visivel, ordenar, sistema,
    subnicho_visivel,
)
from ..db import get_db
from ..models import Clique, Dor, Lead, Nicho, Oferta, Subnicho

router = APIRouter()


def _uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="Identificador invalido")


def _editorial(x) -> dict[str, Any]:
    return {"id": x.id, "slug": x.slug, "title": x.title, "description": x.description,
            "translations": x.translations or {}}


def _oferta(o: Oferta) -> dict[str, Any]:
    return {"id": o.id, "title": o.title, "description": o.description,
            "translations": o.translations or {}, "kind": o.kind, "provider": o.provider,
            "market": o.market, "language": o.language, "image_url": o.image_url,
            "url": f"/r/{o.id}"}


def _lista(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"status": "OK", "total": len(items), "data": items}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("select 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "erro", "banco": "indisponivel"})
    return {"status": "ok", "service": "robo-global", "sistema_ativo": sistema(db)["ativo"]}


@router.get("/public/nichos")
def nichos(db: Session = Depends(get_db)):
    return _lista([_editorial(n) for n in nichos_publicos(db)])


@router.get("/public/nichos/{slug}/subnichos")
def subnichos(slug: str, db: Session = Depends(get_db)):
    nicho = db.scalars(select(Nicho).where(Nicho.slug == slug)).first()
    if not nicho_visivel(nicho):
        raise HTTPException(status_code=404, detail="Nicho nao encontrado")
    return _lista([{**_editorial(s), "nicho_id": s.nicho_id}
                   for s in ordenar([s for s in nicho.subnichos if subnicho_visivel(s)])])


@router.get("/public/subnichos/{subnicho_id}/dores")
def dores(subnicho_id: str, db: Session = Depends(get_db)):
    sub = db.get(Subnicho, _uuid(subnicho_id))
    if not subnicho_visivel(sub):
        raise HTTPException(status_code=404, detail="Subnicho nao encontrado")
    return _lista([{**_editorial(d), "subnicho_id": d.subnicho_id}
                   for d in ordenar([d for d in sub.dores if dor_visivel(d)])])


@router.get("/public/dores/{dor_id}/solucoes")
def solucoes(dor_id: str, db: Session = Depends(get_db)):
    dor = db.get(Dor, _uuid(dor_id))
    if not dor_visivel(dor):
        raise HTTPException(status_code=404, detail="Dor nao encontrada")
    vinculos = sorted((v for v in dor.vinculos if oferta_visivel(v.oferta)),
                      key=lambda v: (-v.priority, v.oferta.title.lower()))
    return _lista([_oferta(v.oferta) for v in vinculos])


@router.get("/public/ofertas")
def ofertas(db: Session = Depends(get_db)):
    items = [o for o in db.scalars(select(Oferta).order_by(Oferta.title)) if oferta_visivel(o)]
    return _lista([_oferta(o) for o in items])


def _destino(url: str, param: Optional[str], click_id: str) -> str:
    if not param:
        return url
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != param]
    query.append((param, click_id))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@router.get("/r/{oferta_id}")
def redirecionar(oferta_id: str, request: Request, db: Session = Depends(get_db),
                 d: Optional[str] = Query(default=None, max_length=36),
                 utm_source: str = Query(default="", max_length=120),
                 utm_medium: str = Query(default="", max_length=120),
                 utm_campaign: str = Query(default="", max_length=120)):
    """Único caminho de saída para um parceiro: valida, registra o clique e redireciona."""
    oferta = db.get(Oferta, _uuid(oferta_id))
    if not oferta_visivel(oferta):
        raise HTTPException(status_code=404, detail="Oferta indisponivel")
    if not sistema(db)["ativo"]:
        raise HTTPException(status_code=503, detail="Redirecionamentos pausados pela operacao")

    dor_id = None
    if d:
        try:
            dor = db.get(Dor, str(uuid.UUID(d)))
            dor_id = dor.id if dor else None
        except ValueError:
            dor_id = None

    salt = request.app.state.settings.visitor_salt
    ip = request.client.host if request.client else ""
    visitor = hashlib.sha256(f"{salt}|{ip}|{request.headers.get('user-agent', '')}".encode()).hexdigest()[:32]
    clique = Clique(oferta_id=oferta.id, dor_id=dor_id,
                    referrer=(request.headers.get("referer") or "")[:500],
                    utm_source=utm_source, utm_medium=utm_medium, utm_campaign=utm_campaign,
                    visitor_hash=visitor)
    db.add(clique)
    db.commit()
    return RedirectResponse(_destino(oferta.destination_url, oferta.subid_param, clique.id), status_code=302)


EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


class LeadIn(BaseModel):
    email: str = Field(max_length=254)
    name: str = Field(default="", max_length=160)
    dor_id: Optional[str] = None
    consent: bool = False
    language: str = Field(default="pt", max_length=10)
    website: str = ""  # armadilha anti-robô: humanos não preenchem


@router.post("/public/leads", status_code=201)
def criar_lead(payload: LeadIn, db: Session = Depends(get_db)):
    """Registra uma pessoa interessada em solução para uma dor (com consentimento LGPD)."""
    if payload.website:
        return {"status": "OK"}
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="E-mail invalido")
    if not payload.consent:
        raise HTTPException(status_code=422, detail="Consentimento obrigatorio")
    dor_id = None
    if payload.dor_id:
        dor = db.get(Dor, _uuid(payload.dor_id))
        if not dor_visivel(dor):
            raise HTTPException(status_code=404, detail="Dor nao encontrada")
        dor_id = dor.id
    db.add(Lead(email=email, name=payload.name.strip(), dor_id=dor_id, consent=True,
                language=payload.language[:10]))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # já cadastrado: resposta idêntica, sem revelar a existência
    return {"status": "OK"}
