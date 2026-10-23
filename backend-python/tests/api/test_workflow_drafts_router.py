"""/workflow-drafts over HTTP: a builder canvas is its owner's alone - for anyone else
every route answers as if it did not exist."""

import uuid

import httpx
import pytest

from app.domain.models.workflow_draft import WorkflowDraft
from tests.conftest import SessionFactory
from tests.db_factories import bearer, save, user

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
        unknown = await client.request(method, route.replace(str(draft.id), str(uuid.uuid4())), json=json, headers=bearer(stranger))
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
