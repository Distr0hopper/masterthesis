"""The format service is asked before a use case opens its unit of work, never while it
is open: a transaction waiting on HTTP would hold its locks - the new rows, a renamed
lineage - for as long as the service takes to answer, up to its timeout."""

import io
import json
import zipfile

import httpx
import pytest

from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.format_service.format_service_client import FormatServiceClient
from tests.conftest import SessionFactory
from tests.db_factories import bearer, save, user

pytestmark = pytest.mark.anyio

FORMATS = """\
$namespaces: {eo: "https://dfg-sos.github.io/ontologies/eo-formats#"}
$schemas: ["https://dfg-sos.github.io/ontologies/eo-formats.owl"]
"""

TOOL = f"""\
cwlVersion: v1.2
class: CommandLineTool
{FORMATS}baseCommand: [echo]
inputs:
  tracks:
    type: File
    format: eo:GeoJSON
outputs: {{}}
"""

PIPELINE = f"""\
cwlVersion: v1.2
class: Workflow
{FORMATS}inputs:
  tracks:
    type: File
    format: eo:GeoJSON
outputs: {{}}
steps:
  step_clean:
    run: clean.cwl
    in: {{tracks: tracks}}
    out: []
"""


class RecordingFormatService:
    """Answers every label - and remembers whether a unit of work was open when asked."""

    def __init__(self) -> None:
        self.asked_inside_a_unit: list[bool] = []

    async def resolve_labels(self, identifiers: set[str], schema_url: str) -> dict[str, str | None]:
        self.asked_inside_a_unit.append(_open_units > 0)
        return {identifier: "GeoJSON" for identifier in identifiers}

    async def check_compatibility(self, expected_format: str, actual_format: str, ontology_url: str) -> bool | None:
        return None


_open_units = 0


@pytest.fixture
def format_service(monkeypatch: pytest.MonkeyPatch) -> RecordingFormatService:
    from app.main import app

    enter, exit_ = SqlUnitOfWork.__aenter__, SqlUnitOfWork.__aexit__

    async def counting_enter(self: SqlUnitOfWork) -> SqlUnitOfWork:
        global _open_units
        result = await enter(self)
        _open_units += 1
        return result

    async def counting_exit(self: SqlUnitOfWork, *args: object) -> None:
        global _open_units
        _open_units -= 1
        await exit_(self, *args)  # type: ignore[arg-type]

    monkeypatch.setattr(SqlUnitOfWork, "__aenter__", counting_enter)
    monkeypatch.setattr(SqlUnitOfWork, "__aexit__", counting_exit)
    fake = RecordingFormatService()
    app.dependency_overrides[FormatServiceClient.get_client] = lambda: fake
    return fake


async def test_no_save_asks_the_format_service_inside_its_transaction(
    client: httpx.AsyncClient, sessions: SessionFactory, format_service: RecordingFormatService
) -> None:
    owner = user()
    await save(sessions, owner)
    headers = bearer(owner)

    # a tool, and its next version
    created = await client.post(
        "/tools",
        data={"name": "clean", "domains": "animal_behavior"},
        files={"cwlFile": ("clean.cwl", TOOL.encode())},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["parameters"][0]["formatLabel"] == "GeoJSON"
    version = await client.post(
        f"/tools/{created.json()['id']}/versions",
        files={"cwlFile": ("clean.cwl", (TOOL + "# v2\n").encode())},
        headers=headers,
    )
    assert version.status_code == 201, version.text

    # a workflow upload: its new tool and the workflow itself, in one transaction
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("pipeline.cwl", PIPELINE)
        zf.writestr("clean.cwl", TOOL + "# uploaded\n")
    config = [{"stepId": "step_clean", "name": "clean-uploaded", "domains": ["animal_behavior"]}]
    workflow = await client.post(
        "/workflows",
        data={"name": "pipeline", "domains": "animal_behavior", "componentConfigs": json.dumps(config)},
        files={"file": ("pipeline.zip", buffer.getvalue())},
        headers=headers,
    )
    assert workflow.status_code == 201, workflow.text

    # a builder canvas synced into My Components
    canvas = {"nodes": [{"id": "n0", "position": {"x": 0, "y": 0}, "data": {"componentId": created.json()["id"]}}]}
    draft = await client.post(
        "/workflow-drafts", json={"name": "canvas", "canvasState": json.dumps(canvas), "nodeCount": 1}, headers=headers
    )
    synced = await client.post(f"/workflow-drafts/{draft.json()['id']}/sync", headers=headers)
    assert synced.status_code == 201, synced.text

    assert format_service.asked_inside_a_unit and not any(format_service.asked_inside_a_unit)
