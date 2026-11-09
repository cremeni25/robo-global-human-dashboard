"""Registro financeiro: uma conversão por (plataforma, id externo).

Regras que o sistema antigo não tinha:
- reenvio do mesmo evento não duplica a venda (idempotência);
- reembolso, chargeback e cancelamento atualizam a venda existente, nunca
  criam venda nova;
- um status final (reembolso/chargeback/cancelamento) não volta a "aprovado"
  por um evento atrasado;
- atribuição ao clique pelo id de rastreio; senão, pelo produto da oferta.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Clique, Conversao, ConversaoEvento, Oferta

STATUSES = ("pending", "approved", "refunded", "chargeback", "canceled")
FINAL = {"refunded", "chargeback", "canceled"}


def to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


@dataclass
class ConversaoIn:
    platform: str
    external_id: str
    status: str
    gross_amount: Decimal = Decimal("0")
    commission_amount: Decimal = Decimal("0")
    currency: str = "BRL"
    occurred_at: Optional[datetime] = None
    product_id: str = ""
    click_id: str = ""
    oferta_id: str = ""
    source: str = "webhook"
    raw: Optional[dict[str, Any]] = None


@dataclass
class Resultado:
    conversao: Conversao
    criada: bool
    alterada: bool


def _atribuir(db: Session, data: ConversaoIn) -> tuple[Optional[str], Optional[str]]:
    if data.click_id:
        clique = db.get(Clique, data.click_id)
        if clique:
            return clique.oferta_id, clique.id
    if data.oferta_id and db.get(Oferta, data.oferta_id):
        return data.oferta_id, None
    if data.product_id:
        oferta = db.scalars(
            select(Oferta).where(Oferta.platform == data.platform,
                                 Oferta.external_product_id == data.product_id)
        ).first()
        if oferta:
            return oferta.id, None
    return None, None


def registrar(db: Session, data: ConversaoIn) -> Resultado:
    if data.status not in STATUSES:
        raise ValueError(f"status invalido: {data.status}")
    if not data.platform or not data.external_id:
        raise ValueError("platform e external_id sao obrigatorios")
    platform = data.platform.lower()
    data.platform = platform
    raw = data.raw or {}

    existente = db.scalars(select(Conversao).where(
        Conversao.platform == platform, Conversao.external_id == data.external_id)).first()

    if existente:
        novo = data.status
        if existente.status == novo or (existente.status in FINAL and novo not in FINAL):
            return Resultado(existente, criada=False, alterada=False)
        existente.status = novo
        if data.commission_amount and existente.commission_amount == 0:
            existente.commission_amount = data.commission_amount
        db.add(ConversaoEvento(conversao_id=existente.id, status=novo, raw=raw))
        db.commit()
        return Resultado(existente, criada=False, alterada=True)

    oferta_id, clique_id = _atribuir(db, data)
    conv = Conversao(
        platform=platform, external_id=data.external_id, status=data.status,
        gross_amount=data.gross_amount, commission_amount=data.commission_amount,
        currency=(data.currency or "BRL").upper()[:3], product_id=data.product_id or "",
        occurred_at=data.occurred_at or datetime.now(timezone.utc),
        oferta_id=oferta_id, clique_id=clique_id, source=data.source,
    )
    db.add(conv)
    try:
        db.flush()
    except IntegrityError:  # corrida entre dois reenvios simultâneos
        db.rollback()
        return registrar(db, data)
    db.add(ConversaoEvento(conversao_id=conv.id, status=data.status, raw=raw))
    db.commit()
    return Resultado(conv, criada=True, alterada=True)


# ------------------------------------------------------------------ Hotmart

HOTMART_STATUS = {
    "PURCHASE_APPROVED": "approved",
    "PURCHASE_COMPLETE": "approved",
    "PURCHASE_REFUNDED": "refunded",
    "PURCHASE_PARTIALLY_REFUNDED": "refunded",
    "PURCHASE_CHARGEBACK": "chargeback",
    "PURCHASE_CANCELED": "canceled",
    "PURCHASE_CANCELLED": "canceled",
    "PURCHASE_EXPIRED": "canceled",
    "PURCHASE_PROTEST": "pending",
    "PURCHASE_DELAYED": "pending",
    "PURCHASE_BILLET_PRINTED": "pending",
    "PURCHASE_WAITING_PAYMENT": "pending",
}


def _ms_to_dt(value: Any) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def normalizar_hotmart(payload: dict[str, Any]) -> Optional[ConversaoIn]:
    """Webhook Hotmart versão 2.0. Retorna None para eventos não financeiros."""
    status = HOTMART_STATUS.get(str(payload.get("event", "")).upper())
    data = payload.get("data") or {}
    purchase = data.get("purchase") or {}
    transaction = purchase.get("transaction")
    if not status or not transaction:
        return None
    price = purchase.get("price") or {}
    commissions = data.get("commissions") or []
    commission = Decimal("0")
    if isinstance(commissions, dict):
        commissions = [commissions]
    if isinstance(commissions, list):
        items = [c for c in commissions if isinstance(c, dict)]
        affiliate = [c for c in items if "AFFILIATE" in str(c.get("source", "")).upper()]
        producer = [c for c in items if "PRODUCER" in str(c.get("source", "")).upper()]
        for c in (affiliate or producer):
            commission += to_decimal(c.get("value"))
    origin = purchase.get("origin") or {}
    tracking = purchase.get("tracking") or {}
    click = (origin.get("sck") or tracking.get("source_sck") or tracking.get("source")
             or tracking.get("external_code") or "")
    return ConversaoIn(
        platform="hotmart",
        external_id=str(transaction),
        status=status,
        gross_amount=to_decimal(price.get("value")),
        commission_amount=commission,
        currency=str(price.get("currency_value") or "BRL"),
        occurred_at=_ms_to_dt(purchase.get("approved_date") or purchase.get("order_date")),
        product_id=str((data.get("product") or {}).get("id") or ""),
        click_id=str(click)[:36],
        source="webhook",
        raw=payload,
    )
