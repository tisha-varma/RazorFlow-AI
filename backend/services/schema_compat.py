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


def purge_orphans(engine: Engine) -> dict:
    """Delete child rows whose parent was removed without cascade.

    Belt-and-braces for DB files dirtied before FK enforcement (M1): runs at
    every startup so a stale file can never resurrect phantom cart items.
    Returns counts per table for the startup log.
    """
    if engine.dialect.name != "sqlite":
        return {}
    counts: dict = {}
    purges = [
        ("cart_items", "cart_id", "carts", "id"),
        ("order_items", "order_id", "orders", "id"),
        ("razorpay_payments", "order_id", "orders", "id"),
        ("approvals", "cart_id", "carts", "id"),
    ]
    with engine.begin() as conn:
        tables = set(inspect(engine).get_table_names())
        for child, fk, parent, pk in purges:
            if child not in tables or parent not in tables:
                continue
            result = conn.execute(text(
                f"DELETE FROM {child} "
                f"WHERE {fk} NOT IN (SELECT {pk} FROM {parent})"
            ))
            counts[child] = result.rowcount
    return counts
