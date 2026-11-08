"""Gera sql/001_schema.sql (PostgreSQL/Supabase) a partir de app/models.py.

Uso: python scripts/gerar_schema_sql.py
A API também cria as tabelas sozinha ao iniciar; este arquivo serve para
revisão humana ou para rodar manualmente no SQL Editor do Supabase.
"""
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.models import Base  # noqa: E402

out = ["-- Robô Global v2 — esquema gerado de app/models.py. Não edite à mão.", "begin;"]
for table in Base.metadata.sorted_tables:
    ddl = str(CreateTable(table, if_not_exists=True).compile(dialect=postgresql.dialect())).strip()
    out.append(ddl + ";")
    for index in sorted(table.indexes, key=lambda i: i.name):
        out.append(str(CreateIndex(index, if_not_exists=True).compile(dialect=postgresql.dialect())).strip() + ";")
out.append("commit;")
target = Path(__file__).resolve().parents[1] / "sql" / "001_schema.sql"
target.write_text("\n\n".join(out) + "\n", encoding="utf-8")
print(f"escrito {target}")
