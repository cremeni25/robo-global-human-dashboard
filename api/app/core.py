"""Regras centrais: visibilidade pública, estado do sistema e auditoria."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Auditoria, Configuracao, Dor, Nicho, Oferta, Subnicho

TEST_PREFIXES = ("teste-", "test-")


def is_test_slug(slug: str | None) -> bool:
    return str(slug or "").lower().startswith(TEST_PREFIXES)


def is_safe_url(url: str | None) -> bool:
    try:
        parts = urlsplit(str(url or ""))
    except ValueError:
        return False
    return parts.scheme == "https" and bool(parts.netloc)


# ---------------------------------------------------------------- visibilidade

def nicho_visivel(n: Nicho | None) -> bool:
    return bool(n and n.published and not is_test_slug(n.slug))


def subnicho_visivel(s: Subnicho | None) -> bool:
    return bool(s and s.published and not is_test_slug(s.slug) and nicho_visivel(s.nicho))


def dor_visivel(d: Dor | None) -> bool:
    return bool(d and d.published and not is_test_slug(d.slug) and subnicho_visivel(d.subnicho))


def oferta_visivel(o: Oferta | None) -> bool:
    return bool(o and o.active and o.published and is_safe_url(o.destination_url))


# ---------------------------------------------------------------- estado

SISTEMA_KEY = "sistema"


def sistema(db: Session) -> dict[str, Any]:
    row = db.get(Configuracao, SISTEMA_KEY)
    value = dict(row.value) if row else {}
    value.setdefault("ativo", True)
    value.setdefault("motivo", "")
    return value


def definir_sistema(db: Session, *, ativo: bool, motivo: str, actor: str) -> dict[str, Any]:
    row = db.get(Configuracao, SISTEMA_KEY)
    value = {"ativo": ativo, "motivo": motivo, "alterado_por": actor}
    if row:
        row.value = value
    else:
        db.add(Configuracao(key=SISTEMA_KEY, value=value))
    auditar(db, actor, "sistema.ativo" if ativo else "sistema.pausado", "sistema", SISTEMA_KEY, value)
    db.commit()
    return value


# ---------------------------------------------------------------- auditoria

def auditar(db: Session, actor: str, action: str, entity: str = "", entity_id: str = "",
            detail: dict[str, Any] | None = None) -> None:
    db.add(Auditoria(actor=actor, action=action, entity=entity, entity_id=str(entity_id),
                     detail=detail or {}))


def ordenar(items: list, key=lambda x: (x.position, x.title.lower())) -> list:
    return sorted(items, key=key)


def nichos_publicos(db: Session) -> list[Nicho]:
    return ordenar([n for n in db.scalars(select(Nicho)) if nicho_visivel(n)])
