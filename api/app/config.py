"""Configuração única do Robô Global, lida do ambiente.

Toda variável tem um padrão seguro: sem token configurado, a área
administrativa e os webhooks ficam fechados (fail closed).
"""
from __future__ import annotations

import json
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


def _feed_urls() -> list[str]:
    urls: list[str] = []
    single = os.getenv("AWIN_FEED_URL", "").strip()
    if single:
        urls.append(single)
    try:
        extra = json.loads(os.getenv("AWIN_FEED_URLS", "[]") or "[]")
        if isinstance(extra, list):
            urls.extend(str(u).strip() for u in extra if str(u).strip())
    except ValueError:
        pass
    return list(dict.fromkeys(urls))


def _json_list(name: str) -> list[dict]:
    try:
        data = json.loads(os.getenv(name, "[]") or "[]")
    except ValueError:
        return []
    return [d for d in data if isinstance(d, dict) and str(d.get("url", "")).startswith("https://")] if isinstance(data, list) else []


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
    # Aquisição automática (Awin). Sem credenciais, o ciclo simplesmente pula a etapa.
    awin_publisher_id: str = field(default_factory=lambda: os.getenv("AWIN_PUBLISHER_ID", "").strip())
    awin_api_token: str = field(default_factory=lambda: os.getenv("AWIN_API_TOKEN", "").strip())
    awin_feed_urls: list[str] = field(default_factory=_feed_urls)
    # Fontes universais (qualquer rede/loja): JSON [{"rede": "cj", "url": "https://...", ...}].
    # Também podem ser cadastradas no painel (Aquisição → Fontes), sem mexer no Render.
    fontes_feeds: list[dict] = field(default_factory=lambda: _json_list("FONTES_FEEDS"))
    aquisicao_automatica: bool = field(default_factory=lambda: os.getenv("AQUISICAO_AUTOMATICA", "1") == "1")
    aquisicao_intervalo_horas: float = field(default_factory=lambda: _float("AQUISICAO_INTERVALO_HORAS", 6))
    # Importa uma vez os dados do catálogo legado e do Core V1 (mesmo banco Supabase)
    importar_legado: bool = field(default_factory=lambda: os.getenv("IMPORTAR_LEGADO", "1") == "1")
    # Autonomia: agentes que substituem as decisões humanas recorrentes.
    # AUTO_APROVAR_ANUNCIANTES: anunciante com afiliação confirmada pela rede vai ao ar sozinho.
    # AUTO_TAXONOMIA: categorias dos produtos viram nicho/subnicho/dor publicados automaticamente.
    # AUTO_DECISOES: recomendações (PAUSAR/ESCALAR) são aplicadas sem esperar aprovação.
    auto_aprovar_anunciantes: bool = field(default_factory=lambda: os.getenv("AUTO_APROVAR_ANUNCIANTES", "1") == "1")
    auto_taxonomia: bool = field(default_factory=lambda: os.getenv("AUTO_TAXONOMIA", "1") == "1")
    auto_decisoes: bool = field(default_factory=lambda: os.getenv("AUTO_DECISOES", "1") == "1")
    # Parâmetros da inteligência (recomendações sempre aprovadas por um humano)
    min_cliques_decisao: int = field(default_factory=lambda: _int("MIN_CLIQUES_DECISAO", 100))
    epc_alvo: float = field(default_factory=lambda: _float("EPC_ALVO", 0.50))
    taxa_reembolso_max: float = field(default_factory=lambda: _float("TAXA_REEMBOLSO_MAX", 0.30))
