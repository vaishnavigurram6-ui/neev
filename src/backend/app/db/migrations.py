"""Additive SQLite demo migration; never reset existing borrower state.

Production migrations and durable storage remain a deployment gate.
"""
from sqlalchemy import inspect, text


def upgrade(engine) -> None:
    additions = {
        "boq_revisions": {"source_artifact": "TEXT"},
        "questions": {"revision_id": "INTEGER REFERENCES boq_revisions(id)"},
        "tranches": {"claimed_stage": "VARCHAR(32)",
                     "assessment_revision_id": "INTEGER REFERENCES boq_revisions(id)"},
    }
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, fields in additions.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in fields.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
        # Legacy questions belonged to the first authored revision, not future runs.
        connection.execute(text(
            "UPDATE questions SET revision_id = (SELECT MIN(id) FROM boq_revisions "
            "WHERE boq_revisions.loan_id = questions.loan_id) WHERE revision_id IS NULL"
        ))