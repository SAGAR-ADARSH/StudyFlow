"""Keep the documented MySQL schema in sync with the SQLAlchemy models."""
import re
from pathlib import Path

from app.models.base import Base
import app.models  # noqa: F401  (registers every table on the metadata)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_FILES = [REPO_ROOT / "mysql_setup.sql", REPO_ROOT / "apps" / "api" / "mysql_setup.sql"]


def _table_block(sql: str, table: str) -> str:
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS `{table}` \((.*?)\n\) ENGINE=",
        sql,
        re.DOTALL,
    )
    assert match, f"{table} is missing from the documented schema"
    return match.group(1)


def test_both_schema_copies_are_identical():
    contents = [path.read_text() for path in SCHEMA_FILES]
    assert contents[0] == contents[1], "mysql_setup.sql copies have drifted apart"


def test_every_model_table_is_documented_with_its_columns():
    sql = SCHEMA_FILES[0].read_text()
    for table_name, table in Base.metadata.tables.items():
        block = _table_block(sql, table_name)
        for column in table.columns:
            assert re.search(rf"^\s*`{column.name}`\s", block, re.MULTILINE), (
                f"column {table_name}.{column.name} is not documented in mysql_setup.sql"
            )


def test_new_phase_tables_are_additive_and_cascade_to_their_owner():
    sql = SCHEMA_FILES[0].read_text()
    for table_name in ("documents", "document_summaries", "quizzes", "quiz_questions", "quiz_attempts", "quiz_attempt_answers"):
        block = _table_block(sql, table_name)
        assert "IF NOT EXISTS" in sql  # additive: never DROPs existing tables
        assert "ON DELETE CASCADE" in block
    assert "DROP TABLE" not in sql, "the documented schema must never drop existing tables"
