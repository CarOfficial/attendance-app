"""Tiny schema upgrade for pre-existing SQLite databases (no Alembic yet).

`Base.metadata.create_all` creates missing *tables* but never adds missing
*columns* to tables that already exist, so older dev databases would break
after this release. This adds the columns introduced for approvals and the
daily work description.
"""

from sqlalchemy import Engine

NEW_COLUMNS: dict[str, dict[str, str]] = {
    "attendance_records": {
        "check_out_source": "VARCHAR(20)",
        "work_description": "VARCHAR(1000)",
        "approval_status": "VARCHAR(20) DEFAULT 'none'",
        "approval_note": "VARCHAR(255)",
        "approval_by": "INTEGER",
        "approved_at": "TIMESTAMP",
    },
}


def upgrade_sqlite_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        for table, columns in NEW_COLUMNS.items():
            try:
                rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            except Exception:
                continue  # table does not exist yet; create_all will make it
            existing = {row[1] for row in rows}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        # Older rows must have a non-null approval status.
        try:
            conn.exec_driver_sql(
                "UPDATE attendance_records SET approval_status = 'none' WHERE approval_status IS NULL"
            )
        except Exception:
            pass
