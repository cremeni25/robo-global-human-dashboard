from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request


def token_matches(expected: str, received: str | None) -> bool:
    if not expected or not received:
        return False
    return hmac.compare_digest(expected.encode(), received.encode())


def require_admin(request: Request, authorization: str | None = Header(default=None)) -> str:
    """Retorna o nome do operador humano. Sem tokens configurados, a área
    administrativa fica fechada (503)."""
    tokens: dict[str, str] = request.app.state.settings.admin_tokens
    if not tokens:
        raise HTTPException(status_code=503, detail="Area administrativa nao configurada (ADMIN_TOKEN)")
    received = (authorization or "").removeprefix("Bearer ").strip()
    for token, name in tokens.items():
        if token_matches(token, received):
            return name
    raise HTTPException(status_code=401, detail="Token administrativo invalido")
