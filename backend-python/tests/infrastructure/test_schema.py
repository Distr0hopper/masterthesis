"""The hand-written migrations build exactly the schema the SQLModel entities describe - a
column, index or constraint added to one but not the other shows up here, not in
production. And the checked-in openapi.json is the one the app generates."""

import json
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlmodel import SQLModel

import app.domain.models  # noqa: F401 - registers every table with SQLModel.metadata
from app.main import app

OPENAPI_JSON = Path(__file__).resolve().parents[3] / "openapi.json"


@pytest.mark.anyio
async def test_the_migrated_schema_matches_the_entities(connection: AsyncConnection) -> None:
    def diff(sync_connection) -> list:  # type: ignore[no-untyped-def]
        context = MigrationContext.configure(sync_connection, opts={"compare_type": True})
        return compare_metadata(context, SQLModel.metadata)

    differences = await connection.run_sync(diff)
    # alembic's own bookkeeping table is the only thing the entities don't know
    differences = [d for d in differences if not (d[0] == "remove_table" and d[1].name == "alembic_version")]
    assert differences == [], "\n".join(map(str, differences))


@pytest.mark.skipif(not OPENAPI_JSON.is_file(), reason="needs the mono-repo's openapi.json")
def test_the_checked_in_openapi_spec_is_up_to_date() -> None:
    checked_in = json.loads(OPENAPI_JSON.read_text())
    assert checked_in == app.openapi(), "openapi.json is stale - run `make openapi`"
