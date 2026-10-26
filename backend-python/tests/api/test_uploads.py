"""Uploading over HTTP - the multipart forms the upload wizards send: a tool's .cwl, a
workflow's .cwl or .zip with one config per step, and packaging from GitHub. Each is
checked for what it saves and for how a bad upload is refused."""

import io
import json
import zipfile

import httpx
import pytest

from app.application.exception.component_exceptions import PackagingServiceUnavailableError
from app.infrastructure.packaging.packaging_service_client import PackagingServiceClient
from tests.conftest import SessionFactory
from tests.db_factories import bearer, save, tool, user

pytestmark = pytest.mark.anyio

TOOL_CWL = """\
cwlVersion: v1.2
class: CommandLineTool
baseCommand: [Rscript, app.R]
inputs:
  tracks:
    type: File
  threshold:
    type: double
    default: 0.5
outputs:
  cleaned:
    type: File
    outputBinding: {glob: out.rds}
"""

PIPELINE = """\
cwlVersion: v1.2
class: Workflow
inputs:
  tracks: File
outputs:
  result:
    type: File
    outputSource: step_clean/cleaned
steps:
  step_clean:
    run: clean-tracks.cwl
    in: {tracks: tracks}
    out: [cleaned]
"""


def form(**fields: object) -> dict[str, str]:
    return {k: json.dumps(v) if isinstance(v, list | dict) else str(v) for k, v in fields.items()}


async def create_tool(client: httpx.AsyncClient, headers: dict, cwl: str = TOOL_CWL, **fields: object) -> httpx.Response:
    data = {"name": "clean-tracks", "domains": "animal_behavior", **fields}
    return await client.post("/tools", data=data, files={"cwlFile": ("tool.cwl", cwl.encode())}, headers=headers)


async def test_a_tool_upload_is_saved_as_a_draft_with_its_ports(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    await save(sessions, owner)

    response = await create_tool(client, bearer(owner), description="Drops outliers")

    assert response.status_code == 201
    body = response.json()
    assert (body["name"], body["version"], body["status"], body["description"]) == (
        "clean-tracks",
        1,
        "draft",
        "Drops outliers",
    )
    ports = {(p["name"], p["direction"]) for p in body["parameters"]}
    assert ports == {("tracks", "input"), ("threshold", "input"), ("cleaned", "output")}
    # and it is in My Components, nowhere public yet
    mine = (await client.get("/components/mine", headers=bearer(owner))).json()
    assert [c["name"] for c in mine["unpublished"]["content"]] == ["clean-tracks"]
    assert (await client.get("/components")).json()["content"] == []


async def test_the_preview_of_a_tool_saves_nothing(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner)

    response = await client.post("/tools/parse", files={"cwlFile": ("tool.cwl", TOOL_CWL.encode())}, headers=bearer(owner))

    assert response.status_code == 200
    assert (await client.get("/components/mine", headers=bearer(owner))).json()["unpublished"]["content"] == []


async def test_bad_tool_uploads_are_refused(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner, tool("taken", owner))

    assert (await create_tool(client, {})).status_code == 401
    assert (await create_tool(client, bearer(owner), cwl="class: [broken")).status_code == 400
    assert (await create_tool(client, bearer(owner), cwl=PIPELINE)).status_code == 400
    assert (await create_tool(client, bearer(owner), name="taken")).status_code == 409
    assert (await create_tool(client, bearer(owner), domains="astrology")).status_code == 422
    no_file = await client.post("/tools", data={"name": "x", "domains": "animal_behavior"}, headers=bearer(owner))
    assert no_file.status_code == 422
    too_big = TOOL_CWL + "#" * (11 * 1024 * 1024)
    assert (await create_tool(client, bearer(owner), cwl=too_big, name="big")).status_code == 400


def archive(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


async def create_workflow(
    client: httpx.AsyncClient, headers: dict, content: bytes, configs: list[dict], name: str = "track-pipeline"
) -> httpx.Response:
    return await client.post(
        "/workflows",
        data=form(name=name, domains="animal_behavior", componentConfigs=configs),
        files={"file": ("pipeline.zip", content)},
        headers=headers,
    )


async def test_a_workflow_archive_creates_its_new_tools_along(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    await save(sessions, owner)
    content = archive({"pipeline.cwl": PIPELINE, "clean-tracks.cwl": TOOL_CWL})

    preview = await client.post("/workflows/parse", files={"file": ("pipeline.zip", content)}, headers=bearer(owner))
    assert preview.status_code == 200
    assert (preview.json()["isZip"], preview.json()["stepCount"]) == (True, 1)
    assert [s["stepId"] for s in preview.json()["componentPreviews"]] == ["step_clean"]

    config = {"stepId": "step_clean", "name": "clean-tracks", "domains": ["animal_behavior"]}
    response = await create_workflow(client, bearer(owner), content, [config])

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["name"], body["status"]) == ("track-pipeline", "draft")
    [step] = body["steps"]
    assert step["component"]["name"] == "clean-tracks"
    mine = (await client.get("/components/mine", headers=bearer(owner))).json()
    assert sorted(c["name"] for c in mine["unpublished"]["content"]) == ["clean-tracks", "track-pipeline"]


async def test_a_workflow_step_can_reuse_a_catalogue_tool(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, author = user(), user()
    existing = tool("clean-tracks", author)
    await save(sessions, owner, author, existing)
    content = archive({"pipeline.cwl": PIPELINE, "clean-tracks.cwl": TOOL_CWL})

    response = await create_workflow(
        client, bearer(owner), content, [{"stepId": "step_clean", "reuseComponentId": str(existing.id)}]
    )

    assert response.status_code == 201, response.text
    assert response.json()["steps"][0]["component"]["id"] == str(existing.id)


async def test_bad_workflow_uploads_are_refused_and_save_nothing(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    await save(sessions, owner)
    good = archive({"pipeline.cwl": PIPELINE, "clean-tracks.cwl": TOOL_CWL})
    config = [{"stepId": "step_clean", "name": "clean-tracks", "domains": ["animal_behavior"]}]

    assert (await create_workflow(client, bearer(owner), archive({"tool.cwl": TOOL_CWL}), config)).status_code == 400
    assert (await create_workflow(client, bearer(owner), b"not a zip at all", config)).status_code == 400
    missing_step_file = archive({"pipeline.cwl": PIPELINE})
    assert (await create_workflow(client, bearer(owner), missing_step_file, config)).status_code == 400
    # every step has to be configured
    assert (await create_workflow(client, bearer(owner), good, [])).status_code == 400
    assert (await create_workflow(client, {}, good, config)).status_code == 401

    mine = (await client.get("/components/mine", headers=bearer(owner))).json()
    assert mine["unpublished"]["content"] == []


async def test_packaging_while_the_packaging_service_is_down_is_503(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    from app.main import app

    class DownPackagingService:
        async def package(self, repo_url: str) -> None:
            raise PackagingServiceUnavailableError()

    owner = user()
    await save(sessions, owner)
    app.dependency_overrides[PackagingServiceClient.get_client] = DownPackagingService

    body = {"repoUrl": "https://github.com/movestore/some-app", "domains": ["animal_behavior"]}
    for path in ("/tools/package/preview", "/tools/package"):
        assert (await client.post(path, json=body, headers=bearer(owner))).status_code == 503, path
    bad_url = {"repoUrl": "not a url", "domains": ["animal_behavior"]}
    assert (await client.post("/tools/package", json=bad_url, headers=bearer(owner))).status_code == 422


async def test_a_workflow_step_cannot_reuse_someone_elses_draft(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    from app.domain.models.component import ComponentStatus

    owner, author = user(), user()
    secret = tool("clean-tracks", author, ComponentStatus.DRAFT)
    await save(sessions, owner, author, secret)
    content = archive({"pipeline.cwl": PIPELINE, "clean-tracks.cwl": TOOL_CWL})

    response = await create_workflow(
        client, bearer(owner), content, [{"stepId": "step_clean", "reuseComponentId": str(secret.id)}]
    )

    # like any id it may not read - 404, as if the draft did not exist
    assert response.status_code == 404, response.text
    assert (await client.get("/components/mine", headers=bearer(owner))).json()["unpublished"]["content"] == []


INLINE_PIPELINE = """\
cwlVersion: v1.2
class: Workflow
inputs: {}
outputs: {}
steps:
  clean-tracks:
    run:
      class: CommandLineTool
      baseCommand: echo
      inputs: {}
      outputs: {}
    in: {}
    out: []
"""


async def test_the_preview_never_names_someone_elses_draft_as_a_name_conflict(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    from app.domain.models.component import ComponentStatus

    owner, author = user(), user()
    published = tool("clean-tracks", author, version=1)
    secret = tool("clean-tracks", author, ComponentStatus.DRAFT, version=2)
    await save(sessions, owner, author, published, secret)

    def conflict(response: httpx.Response) -> dict | None:
        assert response.status_code == 200, response.text
        return response.json()["componentPreviews"][0]["nameConflict"]

    files = {"file": ("pipeline.cwl", INLINE_PIPELINE.encode())}
    # the newest version the caller may read - the public v1, never the private v2 above it
    assert conflict(await client.post("/workflows/parse", files=files, headers=bearer(owner)))["version"] == 1
    # its owner sees their own draft
    assert conflict(await client.post("/workflows/parse", files=files, headers=bearer(author)))["version"] == 2



async def test_a_new_workflow_version_cannot_nest_its_own_lineage(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    from app.domain.models.component import ComponentStatus
    from tests.db_factories import workflow

    owner = user()
    v1 = workflow("track-pipeline", owner, status=ComponentStatus.DRAFT)
    await save(sessions, owner, v1)

    response = await client.post(
        f"/workflows/{v1.id}/versions",
        data=form(componentConfigs=[{"stepId": "step_clean", "reuseComponentId": str(v1.id)}]),
        files={"file": ("pipeline.zip", archive({"pipeline.cwl": PIPELINE, "clean-tracks.cwl": TOOL_CWL}))},
        headers=bearer(owner),
    )

    # v2 running v1 would make the lineage contain itself
    assert response.status_code == 409, response.text
    assert len((await client.get(f"/components/{v1.id}/versions", headers=bearer(owner))).json()) == 1
