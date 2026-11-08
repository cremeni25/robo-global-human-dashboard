"""Robô Global v2 — API única.

Substitui o main.py legado (2.162 linhas, rotas duplicadas e abertas) e o
serviço externo Core V1: catálogo, rastreio, vendas e inteligência ficam
em um só lugar, com banco persistente e auditoria.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .db import make_engine, make_sessionmaker
from .models import Base
from .routers import admin, public, webhooks

VERSION = "2.0.0"


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)  # idempotente: cria só as tabelas rg_* que faltarem

    app = FastAPI(title="Robô Global", version=VERSION,
                  description="Necessidades reais → soluções rastreadas → receita auditável, com decisão humana.")
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"])
    app.include_router(public.router)
    app.include_router(webhooks.router)
    app.include_router(admin.router)

    log = logging.getLogger("robo_global")
    log.info("Robo Global %s | admin=%s | hotmart=%s | webhook=%s", VERSION,
             "configurado" if settings.admin_tokens else "FECHADO",
             "configurado" if settings.hotmart_hottok else "fechado",
             "configurado" if settings.webhook_token else "fechado")
    return app


app = create_app()
