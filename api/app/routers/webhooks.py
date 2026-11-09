"""Entrada de vendas reais.

- /webhooks/hotmart: formato oficial da Hotmart (token "hottok").
- /webhooks/conversao: formato normalizado do Robô Global, para qualquer
  outra plataforma (Eduzz, Monetizze, Kiwify, Awin...) via integração
  própria ou ferramentas como Make/Zapier/n8n.
Eventos aceitos sempre respondem 200, inclusive duplicados, para a
plataforma não reenviar sem fim.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..conversions import STATUSES, ConversaoIn, normalizar_hotmart, registrar
from ..db import get_db
from ..security import token_matches

router = APIRouter(prefix="/webhooks")
log = logging.getLogger("robo_global.webhooks")


@router.post("/hotmart")
async def hotmart(request: Request, db: Session = Depends(get_db),
                  x_hotmart_hottok: Optional[str] = Header(default=None)):
    expected = request.app.state.settings.hotmart_hottok
    if not expected:
        raise HTTPException(status_code=503, detail="Webhook Hotmart nao configurado (HOTMART_HOTTOK)")
    try:
        payload = json.loads(await request.body())
    except ValueError:
        raise HTTPException(status_code=400, detail="JSON invalido")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON invalido")
    received = x_hotmart_hottok or str(payload.get("hottok") or "")
    if not token_matches(expected, received):
        raise HTTPException(status_code=401, detail="hottok invalido")

    data = normalizar_hotmart(payload)
    if data is None:
        log.info("hotmart evento ignorado: %s", payload.get("event"))
        return {"status": "ignorado", "evento": payload.get("event")}
    r = registrar(db, data)
    return {"status": "registrado" if r.alterada else "duplicado", "conversao_id": r.conversao.id,
            "situacao": r.conversao.status}


class ConversaoPayload(BaseModel):
    platform: str = Field(min_length=2, max_length=40)
    external_id: str = Field(min_length=1, max_length=160)
    status: str
    gross_amount: Decimal = Decimal("0")
    commission_amount: Decimal = Decimal("0")
    currency: str = Field(default="BRL", max_length=3)
    occurred_at: Optional[datetime] = None
    product_id: str = Field(default="", max_length=120)
    click_id: str = Field(default="", max_length=36)
    oferta_id: str = Field(default="", max_length=36)

    def to_in(self, source: str, raw: Optional[dict] = None) -> ConversaoIn:
        if self.status not in STATUSES:
            raise HTTPException(status_code=422, detail=f"status deve ser um de {', '.join(STATUSES)}")
        return ConversaoIn(platform=self.platform, external_id=self.external_id, status=self.status,
                           gross_amount=self.gross_amount, commission_amount=self.commission_amount,
                           currency=self.currency, occurred_at=self.occurred_at,
                           product_id=self.product_id, click_id=self.click_id,
                           oferta_id=self.oferta_id, source=source,
                           raw=raw if raw is not None else self.model_dump(mode="json"))


@router.post("/conversao")
def conversao_generica(payload: ConversaoPayload, request: Request, db: Session = Depends(get_db),
                       x_webhook_token: Optional[str] = Header(default=None)):
    expected = request.app.state.settings.webhook_token
    if not expected:
        raise HTTPException(status_code=503, detail="Webhook nao configurado (WEBHOOK_TOKEN)")
    if not token_matches(expected, x_webhook_token):
        raise HTTPException(status_code=401, detail="Token invalido")
    r = registrar(db, payload.to_in("webhook"))
    return {"status": "registrado" if r.alterada else "duplicado", "conversao_id": r.conversao.id,
            "situacao": r.conversao.status}


# Endereço antigo do Core V1, já cadastrado na Hotmart: continua aceito.
legacy_router = APIRouter()
legacy_router.add_api_route("/v1/webhooks/hotmart", hotmart, methods=["POST"], include_in_schema=False)
