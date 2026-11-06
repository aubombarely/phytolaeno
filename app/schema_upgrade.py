"""Add columns introduced after a database was created (create_all never alters tables).

All new columns are nullable, so ALTER TABLE ... ADD COLUMN is safe on SQLite and
PostgreSQL. Called at startup; idempotent.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import Base


def ensure_columns(engine: Engine) -> list[str]:
    """Add missing nullable columns of the ORM models to existing tables; return 'table.column' added."""
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    added: list[str] = []
    with engine.begin() as con:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have or not col.nullable:
                    continue
                coltype = col.type.compile(dialect=engine.dialect)
                con.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {coltype}'))
                added.append(f"{table.name}.{col.name}")
    return added
