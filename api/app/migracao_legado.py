"""Importa automaticamente, uma única vez, os dados dos sistemas anteriores
(sql/002 catálogo legado e sql/003 Core V1) no primeiro start em PostgreSQL.

Só roda se as tabelas de origem existirem. Os scripts são idempotentes e
não alteram nem apagam nada da origem. O resultado fica em rg_config.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import Configuracao

log = logging.getLogger("robo_global.migracao")
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
KEY = "migracao_legado"
SCRIPTS = (
    ("002_importar_catalogo_legado.sql", ("robo_global.nichos", "robo_global.subnichos", "robo_global.dores",
                                         "public.solucoes", "robo_global.dor_solucoes")),
    ("003_importar_core_v1.sql", ("robo_global_core.offers", "robo_global_core.opportunities",
                                  "robo_global_core.demands", "robo_global_core.interactions",
                                  "robo_global_core.conversions")),
)


def _corpo(sql: str) -> str:
    """Remove begin/commit e a consulta final de conferência: a transação é nossa."""
    body = sql.split("\ncommit;")[0]
    return "\n".join(line for line in body.splitlines() if line.strip().lower() != "begin;")


def importar_legado(engine: Engine, sessionmaker) -> dict:
    if engine.dialect.name != "postgresql":
        return {"status": "ignorado", "motivo": "nao_postgresql"}
    with sessionmaker() as db:
        if db.get(Configuracao, KEY):
            return {"status": "ja_executado"}
    resultado: dict = {}
    for arquivo, origens in SCRIPTS:
        with engine.connect() as conn:
            faltando = [t for t in origens if conn.execute(text("select to_regclass(:t)"), {"t": t}).scalar() is None]
        if faltando:
            resultado[arquivo] = {"status": "sem_origem", "faltando": faltando}
            continue
        raw = engine.raw_connection()  # driver direto: o SQL usa '%' em LIKE
        try:
            with raw.cursor() as cur:
                cur.execute(_corpo((SQL_DIR / arquivo).read_text(encoding="utf-8")))
            raw.commit()
            resultado[arquivo] = {"status": "ok"}
        except Exception as exc:  # não impede a API de subir
            raw.rollback()
            resultado[arquivo] = {"status": "falhou", "erro": type(exc).__name__}
            log.error("migracao %s falhou: %s", arquivo, type(exc).__name__)
        finally:
            raw.close()
    # Só marca como concluída se nada falhou; senão tenta de novo no próximo start.
    concluida = all(r["status"] != "falhou" for r in resultado.values())
    with sessionmaker() as db:
        key = KEY if concluida else KEY + "_tentativa"
        row = db.get(Configuracao, key)
        if row:
            row.value = resultado
        else:
            db.add(Configuracao(key=key, value=resultado))
        db.commit()
    log.info("migracao legado: %s", resultado)
    return resultado
