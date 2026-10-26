"""/workflow-drafts over HTTP: a builder canvas is its owner's alone - for anyone else
every route answers as if it did not exist. And a canvas only ever runs what its owner
may read, whatever ids its client-written JSON names."""

import io
import json
import uuid
import zipfile

import httpx
import pytest
import yaml

from app.domain.models.component import ComponentStatus
from app.domain.models.parameter import ParameterDirection
from app.domain.models.workflow_draft import WorkflowDraft
from tests.conftest import SessionFactory
from tests.db_factories import bearer, port, save, tool, user

pytestmark = pytest.mark.anyio

CANVAS = '{"nodes": [], "edges": []}'


async def test_the_owner_opens_updates_and_deletes_their_canvas(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    draft = WorkflowDraft(name="canvas", canvas_state=CANVAS, created_by_id=owner.id)
    await save(sessions, owner, draft)
    path = f"/workflow-drafts/{draft.id}"
    body = {"name": "renamed", "canvasState": CANVAS, "nodeCount": 0}

    assert (await client.get(path, headers=bearer(owner))).status_code == 200
    updated = await client.put(path, json=body, headers=bearer(owner))
    assert updated.status_code == 200
    assert updated.json()["name"] == "renamed"
    assert (await client.delete(path, headers=bearer(owner))).status_code == 204
    assert (await client.get(path, headers=bearer(owner))).status_code == 404


async def test_someone_elses_canvas_is_404_on_every_route(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    draft = WorkflowDraft(name="canvas", canvas_state=CANVAS, created_by_id=owner.id)
    await save(sessions, owner, stranger, draft)
    path = f"/workflow-drafts/{draft.id}"
    body = {"name": "taken", "canvasState": CANVAS, "nodeCount": 0}

    for method, route, json in (
        ("GET", path, None),
        ("PUT", path, body),
        ("DELETE", path, None),
        ("GET", f"{path}/export", None),
        ("GET", f"{path}/export/inputs", None),
        ("POST", f"{path}/sync", None),
    ):
        response = await client.request(method, route, json=json, headers=bearer(stranger))
        # the same answer as for an id nobody has - nothing tells the two apart
        unknown = await client.request(
            method, route.replace(str(draft.id), str(uuid.uuid4())), json=json, headers=bearer(stranger)
        )
        assert response.status_code == unknown.status_code == 404, f"{method} {route}"
        assert (await client.request(method, route, json=json)).status_code == 401, f"{method} {route}"

    # untouched
    response = await client.get(path, headers=bearer(owner))
    assert response.json()["name"] == "canvas"


async def test_the_list_holds_only_the_callers_canvases(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    await save(
        sessions,
        owner,
        stranger,
        WorkflowDraft(name="mine", canvas_state=CANVAS, created_by_id=owner.id),
        WorkflowDraft(name="theirs", canvas_state=CANVAS, created_by_id=stranger.id),
    )

    response = await client.get("/workflow-drafts", headers=bearer(owner))
    assert [d["name"] for d in response.json()] == ["mine"]


def canvas(*components: object, wired: bool = True) -> str:
    """One node per component, left to right; with `wired`, each `out` feeds the next `in`."""
    nodes = [
        {"id": f"n{i}", "position": {"x": i * 200, "y": 0}, "data": {"componentId": str(c.id)}}  # type: ignore[attr-defined]
        for i, c in enumerate(components)
    ]
    edges = [
        {"id": f"e{i}", "source": f"n{i}", "target": f"n{i + 1}", "sourceHandle": "out", "targetHandle": "in"}
        for i in range(len(components) - 1)
        if wired
    ]
    return json.dumps({"nodes": nodes, "edges": edges})


def pipeline_tools(owner: object) -> tuple[object, object]:
    source = tool("read-tracks", owner, ports=(port("out", ParameterDirection.OUTPUT),))
    sink = tool(
        "clean-tracks", owner, ports=(port("in", ParameterDirection.INPUT), port("cleaned", ParameterDirection.OUTPUT))
    )
    return source, sink


async def test_a_canvas_exports_as_a_runnable_archive(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    source, sink = pipeline_tools(owner)
    draft = WorkflowDraft(name="Track pipeline", canvas_state=canvas(source, sink), created_by_id=owner.id)
    await save(sessions, owner, source, sink, draft)

    response = await client.get(f"/workflow-drafts/{draft.id}/export", headers=bearer(owner))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    assert {"read-tracks.cwl", "clean-tracks.cwl"} <= names
    [main] = [n for n in names if yaml.safe_load(archive.read(n)).get("class") == "Workflow"]
    pipeline = yaml.safe_load(archive.read(main))
    steps = list(pipeline["steps"].values())
    assert [s["run"] for s in steps] == ["read-tracks.cwl", "clean-tracks.cwl"]
    # the edge became the wiring: the second step reads the first one's output
    assert any(str(v).endswith("/out") for v in steps[1]["in"].values())

    inputs = await client.get(f"/workflow-drafts/{draft.id}/export/inputs", headers=bearer(owner))
    assert inputs.status_code == 200
    assert inputs.headers["content-type"].startswith("application/yaml")


@pytest.mark.parametrize(
    "canvas_state",
    ['{"nodes": [], "edges": []}', "not json", '{"nodes": [{"data": {}}]}', '{"nodes": [{"id": "n0", "data": {}}]}'],
    ids=["empty", "unreadable", "node without id", "node without component"],
)
async def test_an_unexportable_canvas_is_400(
    client: httpx.AsyncClient, sessions: SessionFactory, canvas_state: str
) -> None:
    owner = user()
    draft = WorkflowDraft(name="broken", canvas_state=canvas_state, created_by_id=owner.id)
    await save(sessions, owner, draft)

    for route in ("export", "export/inputs", "sync"):
        method = "POST" if route == "sync" else "GET"
        response = await client.request(method, f"/workflow-drafts/{draft.id}/{route}", headers=bearer(owner))
        assert response.status_code == 400, route


async def test_a_cycle_on_the_canvas_is_400(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    a = tool("a", owner, ports=(port("in", ParameterDirection.INPUT), port("out", ParameterDirection.OUTPUT)))
    b = tool("b", owner, ports=(port("in", ParameterDirection.INPUT), port("out", ParameterDirection.OUTPUT)))
    state = json.loads(canvas(a, b))
    state["edges"].append({"id": "back", "source": "n1", "target": "n0", "sourceHandle": "out", "targetHandle": "in"})
    draft = WorkflowDraft(name="loop", canvas_state=json.dumps(state), created_by_id=owner.id)
    await save(sessions, owner, a, b, draft)

    response = await client.get(f"/workflow-drafts/{draft.id}/export", headers=bearer(owner))
    assert response.status_code == 400
    assert "cycle" in response.json()["detail"]


async def test_syncing_saves_one_draft_workflow_and_resyncs_it_in_place(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    source, sink = pipeline_tools(owner)
    draft = WorkflowDraft(name="Track pipeline", canvas_state=canvas(source, sink), created_by_id=owner.id)
    await save(sessions, owner, source, sink, draft)
    path = f"/workflow-drafts/{draft.id}/sync"

    first = await client.post(path, headers=bearer(owner))
    assert first.status_code == 201
    assert (first.json()["status"], first.json()["version"], first.json()["stepCount"]) == ("draft", 1, 2)

    again = await client.post(path, headers=bearer(owner))
    assert (again.json()["workflowId"], again.json()["version"]) == (first.json()["workflowId"], 1)

    # its steps run exactly the components on the canvas
    workflow = (await client.get(f"/components/{first.json()['workflowId']}", headers=bearer(owner))).json()
    assert [s["component"]["id"] for s in workflow["steps"]] == [str(source.id), str(sink.id)]
    mine = (await client.get("/components/mine", params={"kind": "workflow"}, headers=bearer(owner))).json()
    assert [w["name"] for w in mine["unpublished"]["content"]] == ["Track pipeline"]


async def test_someone_elses_draft_on_a_canvas_counts_as_missing(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, prober = user(), user()
    secret = tool("secret", owner, ComponentStatus.DRAFT)
    public = tool("public", owner)
    # a canvas is client-written JSON - nothing stops it from naming any id
    draft = WorkflowDraft(name="probe", canvas_state=canvas(public, secret, wired=False), created_by_id=prober.id)
    await save(sessions, owner, prober, secret, public, draft)

    detail = await client.get(f"/workflow-drafts/{draft.id}", headers=bearer(prober))
    assert detail.json()["missingComponentIds"] == [str(secret.id)]
    for method, route in (("GET", "export"), ("GET", "export/inputs"), ("POST", "sync")):
        response = await client.request(method, f"/workflow-drafts/{draft.id}/{route}", headers=bearer(prober))
        assert response.status_code == 400, route
        assert "secret" not in response.text

    # the owner's own canvas runs it fine
    own = WorkflowDraft(name="own", canvas_state=canvas(public, secret, wired=False), created_by_id=owner.id)
    await save(sessions, own)
    assert (await client.get(f"/workflow-drafts/{own.id}/export", headers=bearer(owner))).status_code == 200
