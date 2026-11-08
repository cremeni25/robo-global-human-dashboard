"""Configuração única do Robô Global, lida do ambiente.

Toda variável tem um padrão seguro: sem token configurado, a área
administrativa e os webhooks ficam fechados (fail closed).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./robo_global.db").strip()
    # Supabase e Render entregam "postgres://" ou "postgresql://";
    # o SQLAlchemy precisa do driver explícito.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _admin_tokens() -> dict[str, str]:
    """Retorna {token: nome}. Aceita ADMIN_TOKENS="ana:tok1,bruno:tok2"
    e/ou ADMIN_TOKEN="tok" (nome "admin")."""
    tokens: dict[str, str] = {}
    for entry in os.getenv("ADMIN_TOKENS", "").split(","):
        entry = entry.strip()
        if ":" in entry:
            name, token = entry.split(":", 1)
            if len(token.strip()) >= 16:
                tokens[token.strip()] = name.strip() or "admin"
    single = os.getenv("ADMIN_TOKEN", "").strip()
    if len(single) >= 16:
        tokens[single] = "admin"
    return tokens


@dataclass
class Settings:
    database_url: str = field(default_factory=_database_url)
    admin_tokens: dict[str, str] = field(default_factory=_admin_tokens)
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS",
            "https://www.roboglobal.com.br,https://roboglobal.com.br,"
            "https://robo-global-frontend.onrender.com,http://localhost:5173",
        ).split(",") if o.strip()
    ])
    hotmart_hottok: str = field(default_factory=lambda: os.getenv("HOTMART_HOTTOK", "").strip())
    webhook_token: str = field(default_factory=lambda: os.getenv("WEBHOOK_TOKEN", "").strip())
    visitor_salt: str = field(default_factory=lambda: os.getenv("VISITOR_HASH_SALT", "robo-global"))
    # Parâmetros da inteligência (recomendações sempre aprovadas por um humano)
    min_cliques_decisao: int = field(default_factory=lambda: _int("MIN_CLIQUES_DECISAO", 100))
    epc_alvo: float = field(default_factory=lambda: _float("EPC_ALVO", 0.50))
    taxa_reembolso_max: float = field(default_factory=lambda: _float("TAXA_REEMBOLSO_MAX", 0.30))
