"""Modelo de dados canônico do Robô Global v2.

Fluxo: Nicho → Subnicho → Dor ← vínculo → Oferta → Clique → Conversão.
Leads registram demanda de pessoas reais, inclusive para dores sem oferta.
Decisões são recomendações da inteligência; só têm efeito após aprovação humana.
Todas as tabelas usam o prefixo rg_ para não colidir com o legado no Supabase.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, datetime: DateTime(timezone=True)}


class _Editorial:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(140))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    # {"en": {"title": ..., "description": ...}, "es": {...}}
    translations: Mapped[dict[str, Any]] = mapped_column(default=dict)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Nicho(_Editorial, Base):
    __tablename__ = "rg_nichos"
    __table_args__ = (UniqueConstraint("slug", name="uq_rg_nichos_slug"),)
    subnichos: Mapped[list["Subnicho"]] = relationship(back_populates="nicho")


class Subnicho(_Editorial, Base):
    __tablename__ = "rg_subnichos"
    __table_args__ = (UniqueConstraint("nicho_id", "slug", name="uq_rg_subnichos_slug"),)
    nicho_id: Mapped[str] = mapped_column(ForeignKey("rg_nichos.id"), index=True)
    nicho: Mapped[Nicho] = relationship(back_populates="subnichos")
    dores: Mapped[list["Dor"]] = relationship(back_populates="subnicho")


class Dor(_Editorial, Base):
    __tablename__ = "rg_dores"
    __table_args__ = (UniqueConstraint("subnicho_id", "slug", name="uq_rg_dores_slug"),)
    subnicho_id: Mapped[str] = mapped_column(ForeignKey("rg_subnichos.id"), index=True)
    subnicho: Mapped[Subnicho] = relationship(back_populates="dores")
    vinculos: Mapped[list["DorOferta"]] = relationship(back_populates="dor")


class Anunciante(Base):
    """Empresa/programa dentro de uma rede (ex.: anunciante Awin).

    A rede informa se você é afiliado aprovado (membership). Uma pessoa revisa
    os termos UMA vez por anunciante (approved); a partir daí todos os produtos
    dele entram e saem do ar automaticamente.
    """
    __tablename__ = "rg_anunciantes"
    __table_args__ = (UniqueConstraint("platform", "external_id", name="uq_rg_anunciante_externo"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    platform: Mapped[str] = mapped_column(String(40))
    external_id: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200), default="")
    membership: Mapped[str] = mapped_column(String(20), default="unknown")  # joined|pending|not_joined|unknown
    membership_checked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    ofertas: Mapped[list["Oferta"]] = relationship(back_populates="anunciante")

    @property
    def liberado(self) -> bool:
        return self.approved and self.membership == "joined"


class Oferta(Base):
    """Qualquer forma de monetizar uma dor: afiliado, produto próprio,
    serviço próprio ou parceiro que paga por lead."""
    __tablename__ = "rg_ofertas"
    __table_args__ = (UniqueConstraint("platform", "external_product_id", name="uq_rg_oferta_externa"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    translations: Mapped[dict[str, Any]] = mapped_column(default=dict)
    kind: Mapped[str] = mapped_column(String(30), default="afiliado")
    platform: Mapped[str] = mapped_column(String(40), default="manual")
    provider: Mapped[str] = mapped_column(String(200), default="")
    destination_url: Mapped[str] = mapped_column(String(2000))
    # Parâmetro de rastreio aceito pela plataforma (ex.: "sck" na Hotmart).
    # O id do clique é anexado nele para atribuir a venda ao clique.
    subid_param: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    external_product_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    market: Mapped[str] = mapped_column(String(10), default="BR")
    language: Mapped[str] = mapped_column(String(10), default="pt")
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    commission_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    image_url: Mapped[str] = mapped_column(String(2000), default="")
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    category: Mapped[str] = mapped_column(String(300), default="", index=True)
    source: Mapped[str] = mapped_column(String(30), default="manual")  # manual|awin_feed|legado
    anunciante_id: Mapped[Optional[str]] = mapped_column(ForeignKey("rg_anunciantes.id"), nullable=True, index=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    vinculos: Mapped[list["DorOferta"]] = relationship(back_populates="oferta")
    anunciante: Mapped[Optional[Anunciante]] = relationship(back_populates="ofertas")


class MapeamentoCategoria(Base):
    """Regra definida UMA vez por uma pessoa: produtos cuja categoria (ou título)
    contém `termo` são ligados automaticamente à dor — hoje e nas próximas importações."""
    __tablename__ = "rg_mapeamentos"
    __table_args__ = (UniqueConstraint("termo", "dor_id", name="uq_rg_mapeamento"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    termo: Mapped[str] = mapped_column(String(200))
    campo: Mapped[str] = mapped_column(String(20), default="category")  # category|title
    dor_id: Mapped[str] = mapped_column(ForeignKey("rg_dores.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Alias(Base):
    """Ids antigos (oportunidades do Core V1) que continuam redirecionando."""
    __tablename__ = "rg_aliases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    oferta_id: Mapped[str] = mapped_column(ForeignKey("rg_ofertas.id"))


class DorOferta(Base):
    __tablename__ = "rg_dor_ofertas"
    __table_args__ = (UniqueConstraint("dor_id", "oferta_id", name="uq_rg_dor_oferta"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dor_id: Mapped[str] = mapped_column(ForeignKey("rg_dores.id"), index=True)
    oferta_id: Mapped[str] = mapped_column(ForeignKey("rg_ofertas.id"), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    dor: Mapped[Dor] = relationship(back_populates="vinculos")
    oferta: Mapped[Oferta] = relationship(back_populates="vinculos")


class Clique(Base):
    """Clique rastreado. Não guarda IP: apenas um hash anônimo do visitante."""
    __tablename__ = "rg_cliques"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    oferta_id: Mapped[str] = mapped_column(ForeignKey("rg_ofertas.id"), index=True)
    dor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("rg_dores.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    referrer: Mapped[str] = mapped_column(String(500), default="")
    utm_source: Mapped[str] = mapped_column(String(120), default="")
    utm_medium: Mapped[str] = mapped_column(String(120), default="")
    utm_campaign: Mapped[str] = mapped_column(String(120), default="")
    visitor_hash: Mapped[str] = mapped_column(String(64), default="")


class Conversao(Base):
    """Uma venda (ou lead pago) por (plataforma, id externo). Idempotente:
    reenvios do mesmo evento não duplicam; mudança de status atualiza."""
    __tablename__ = "rg_conversoes"
    __table_args__ = (UniqueConstraint("platform", "external_id", name="uq_rg_conversao_externa"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    platform: Mapped[str] = mapped_column(String(40))
    external_id: Mapped[str] = mapped_column(String(160))
    oferta_id: Mapped[Optional[str]] = mapped_column(ForeignKey("rg_ofertas.id"), nullable=True, index=True)
    clique_id: Mapped[Optional[str]] = mapped_column(ForeignKey("rg_cliques.id"), nullable=True)
    product_id: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20))  # pending|approved|refunded|chargeback|canceled
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    occurred_at: Mapped[datetime] = mapped_column(default=utcnow)
    source: Mapped[str] = mapped_column(String(20), default="webhook")  # webhook|manual|csv
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class ConversaoEvento(Base):
    """Histórico imutável de cada mudança de status recebida."""
    __tablename__ = "rg_conversao_eventos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversao_id: Mapped[str] = mapped_column(ForeignKey("rg_conversoes.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    received_at: Mapped[datetime] = mapped_column(default=utcnow)
    raw: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Lead(Base):
    __tablename__ = "rg_leads"
    __table_args__ = (UniqueConstraint("dor_id", "email", name="uq_rg_lead_dor_email"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("rg_dores.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(254))
    name: Mapped[str] = mapped_column(String(160), default="")
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str] = mapped_column(String(10), default="pt")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Decisao(Base):
    __tablename__ = "rg_decisoes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    oferta_id: Mapped[str] = mapped_column(ForeignKey("rg_ofertas.id"), index=True)
    recomendacao: Mapped[str] = mapped_column(String(20))
    motivo: Mapped[str] = mapped_column(Text)
    metricas: Mapped[dict[str, Any]] = mapped_column(default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente|aprovada|rejeitada|substituida
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    decided_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    decided_by: Mapped[str] = mapped_column(String(80), default="")
    nota: Mapped[str] = mapped_column(Text, default="")


class Configuracao(Base):
    __tablename__ = "rg_config"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(default=dict)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Auditoria(Base):
    __tablename__ = "rg_auditoria"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(40), default="")
    entity_id: Mapped[str] = mapped_column(String(160), default="")
    detail: Mapped[dict[str, Any]] = mapped_column(default=dict)
