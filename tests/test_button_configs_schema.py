import pytest

from core.database import Database


@pytest.mark.asyncio
async def test_button_configs_table_exists(tmp_path):
    db = Database()
    await db.initialize(str(tmp_path / "test.sqlite"))

    row = await db.fetchone(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='button_configs'"
    )
    assert row is not None

    columns = await db.fetchall("PRAGMA table_info(button_configs)")
    column_names = {column["name"] for column in columns}

    assert {
        "id",
        "custom_id",
        "label",
        "emoji",
        "enabled",
        "row_position",
        "created_by",
        "created_at",
        "updated_at",
    }.issubset(column_names)

    await db.close()
