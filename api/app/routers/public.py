"""Rotas públicas: catálogo, redirecionamento rastreado e captura de demanda.

Os caminhos são compatíveis com o frontend existente (B1)."""
from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any, Literal, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core import (
    dor_visivel, nicho_visivel, nichos_publicos, oferta_visivel, ordenar, select_ofertas_visiveis,
    sistema, subnicho_visivel,
)
from ..db import get_db
from ..models import Alias, Clique, Dor, DorOferta, Feedback, Inscricao, Lead, Nicho, Oferta, Subnicho

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
            "price": float(o.price) if o.price is not None else None, "currency": o.currency,
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
def solucoes(dor_id: str, db: Session = Depends(get_db), limit: int = Query(default=24, ge=1, le=100)):
    dor = db.get(Dor, _uuid(dor_id))
    if not dor_visivel(dor):
        raise HTTPException(status_code=404, detail="Dor nao encontrada")
    q = (select_ofertas_visiveis().join(DorOferta, DorOferta.oferta_id == Oferta.id)
         .where(DorOferta.dor_id == dor.id).order_by(DorOferta.priority.desc(), Oferta.title))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = [_oferta(o) for o in db.scalars(q.limit(limit))]
    return {"status": "OK", "total": total, "data": items}


@router.get("/public/problemas")
def problemas(request: Request, db: Session = Depends(get_db)):
    """Temas e problemas que têm página no ar (com pelo menos 2 produtos bons)."""
    from .. import problemas as pb
    return {"status": "OK", "temas": pb.obter(db, request.app.state.settings)["temas"]}


@router.get("/public/problemas/{slug}")
def problema(slug: str, request: Request, db: Session = Depends(get_db)):
    from .. import problemas as pb
    d = pb.obter(db, request.app.state.settings)["detalhes"].get(slug)
    if d is None:
        raise HTTPException(status_code=404, detail="Pagina nao encontrada")
    return {"status": "OK", "data": d}


@router.get("/public/vitrine")
def vitrine(request: Request, db: Session = Depends(get_db)):
    """Seções por tema e achados baratos (só lojas confiáveis), girando semanalmente."""
    from .. import vitrine as v
    return v.obter(db, lojas=request.app.state.settings.lojas_confiaveis)


@router.get("/public/ofertas")
def ofertas(request: Request, db: Session = Depends(get_db), q: str = Query(default="", max_length=100),
            dor: Optional[str] = Query(default=None, max_length=36),
            language: str = Query(default="", max_length=10), market: str = Query(default="", max_length=10),
            page: int = Query(default=1, ge=1, le=10_000), limit: int = Query(default=48, ge=1, le=100)):
    """Catálogo público paginado (preparado para centenas de milhares de itens)."""
    from ..problemas import filtro_lojas_publicas
    query = select_ofertas_visiveis().where(filtro_lojas_publicas(request.app.state.settings))
    if q.strip():
        term = f"%{q.strip()}%"
        # Busca também pelos temas (em português, com palavras-chave da IA):
        # "fone" encontra produtos cadastrados como "Earbud Headphones".
        temas = (select(DorOferta.oferta_id).join(Dor, Dor.id == DorOferta.dor_id)
                 .where(Dor.published.is_(True),
                        or_(Dor.title.ilike(term), cast(Dor.translations, String).ilike(term))))
        query = query.where(or_(Oferta.title.ilike(term), Oferta.category.ilike(term),
                                Oferta.provider.ilike(term), Oferta.description.ilike(term),
                                Oferta.id.in_(temas)))
    if dor:
        query = query.join(DorOferta, DorOferta.oferta_id == Oferta.id).where(DorOferta.dor_id == _uuid(dor))
    if language:
        query = query.where(Oferta.language.ilike(f"{language}%"))
    if market:
        query = query.where(Oferta.market == market.upper())
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Oferta.title).offset((page - 1) * limit).limit(limit))
    return {"status": "OK", "total": total, "page": page, "limit": limit, "data": [_oferta(o) for o in rows]}


def _destino(url: str, param: Optional[str], click_id: str) -> str:
    if not param:
        return url
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != param]
    query.append((param, click_id))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@router.get("/go/{oferta_id}", include_in_schema=False)
@router.get("/r/{oferta_id}")
def redirecionar(oferta_id: str, request: Request, db: Session = Depends(get_db),
                 d: Optional[str] = Query(default=None, max_length=36),
                 utm_source: str = Query(default="", max_length=120),
                 utm_medium: str = Query(default="", max_length=120),
                 utm_campaign: str = Query(default="", max_length=120)):
    """Único caminho de saída para um parceiro: valida, registra o clique e redireciona."""
    oid = _uuid(oferta_id)
    oferta = db.get(Oferta, oid)
    if oferta is None:  # links antigos do Core V1 continuam funcionando
        alias = db.get(Alias, oid)
        oferta = db.get(Oferta, alias.oferta_id) if alias else None
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


class InscricaoIn(BaseModel):
    canal: Literal["whatsapp", "email"]
    contato: str = Field(max_length=254)
    consent: bool = False
    language: str = Field(default="pt", max_length=10)
    origem: str = Field(default="", max_length=120)
    utm_source: str = Field(default="", max_length=120)
    website: str = ""  # armadilha anti-robô


def _normalizar_contato(canal: str, contato: str) -> Optional[str]:
    if canal == "email":
        e = contato.strip().lower()
        return e if EMAIL_RE.match(e) else None
    d = re.sub(r"\D", "", contato)
    if d.startswith("00"):
        d = d[2:]
    if len(d) in (10, 11):  # número brasileiro sem DDI
        d = "55" + d
    return "+" + d if 12 <= len(d) <= 15 else None


@router.post("/public/inscricoes", status_code=201)
def inscrever(payload: InscricaoIn, db: Session = Depends(get_db)):
    """Inscrição nos "achados da semana". Resposta idêntica para quem já estava inscrito."""
    if payload.website:
        return {"status": "OK"}
    if not payload.consent:
        raise HTTPException(status_code=422, detail="Consentimento obrigatorio")
    contato = _normalizar_contato(payload.canal, payload.contato)
    if not contato:
        raise HTTPException(status_code=422, detail="Contato invalido")
    db.add(Inscricao(canal=payload.canal, contato=contato, consent=True, language=payload.language[:10],
                     origem=payload.origem.strip()[:120], utm_source=payload.utm_source.strip()[:120]))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"status": "OK"}


class FeedbackIn(BaseModel):
    pagina: str = Field(max_length=120)
    util: Optional[bool] = None
    sugestao: str = Field(default="", max_length=500)
    language: str = Field(default="pt", max_length=10)
    website: str = ""


@router.post("/public/feedback", status_code=201)
def feedback(payload: FeedbackIn, db: Session = Depends(get_db)):
    """"Isso te ajudou?" e "Qual problema você quer que a gente resolva?"."""
    if payload.website:
        return {"status": "OK"}
    if payload.util is None and not payload.sugestao.strip():
        raise HTTPException(status_code=422, detail="Resposta vazia")
    db.add(Feedback(pagina=payload.pagina.strip()[:120], util=payload.util,
                    sugestao=payload.sugestao.strip()[:500], language=payload.language[:10]))
    db.commit()
    return {"status": "OK"}


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
