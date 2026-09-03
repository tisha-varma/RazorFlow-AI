from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_sqlite_schema(engine: Engine) -> None:
    """Apply tiny additive schema updates for the local demo SQLite DB."""
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "audit_events" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("audit_events")}
    statements = []
    if "llm_reason_text" not in columns:
        statements.append("ALTER TABLE audit_events ADD COLUMN llm_reason_text TEXT")
    if "policy_snapshot_id" not in columns:
        statements.append("ALTER TABLE audit_events ADD COLUMN policy_snapshot_id VARCHAR(120)")

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
