"""The /components routers over HTTP: who may read what, who may run which command, and
which status code each refusal comes back as. Authorization lives in the routers, so the
service tests never see it."""

import uuid

import httpx
import pytest

from app.domain.models.component import ComponentStatus
from app.domain.repository.components_repository import ComponentsRepository
from tests.conftest import SessionFactory
from tests.db_factories import bearer, save, tool, user, workflow

pytestmark = pytest.mark.anyio


async def names(response: httpx.Response) -> list[str]:
    assert response.status_code == 200
    return [item["name"] for item in response.json()["content"]]


async def status_of(sessions: SessionFactory, component_id: uuid.UUID) -> str | None:
    async with sessions() as session:
        component = await ComponentsRepository(session).find_by_id(component_id)
        return component.status if component is not None else None


async def test_browsing_lists_only_published_lineages(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    await save(
        sessions,
        owner,
        tool("draft", owner, ComponentStatus.DRAFT),
        tool("published", owner),
        tool("deprecated", owner, ComponentStatus.DEPRECATED),
    )

    assert await names(await client.get("/components")) == ["published"]
    # not even for the owner - drafts come in only on request
    assert await names(await client.get("/components", headers=bearer(owner))) == ["published"]
    own_drafts = await client.get("/components", params={"includeMyDrafts": True}, headers=bearer(owner))
    assert await names(own_drafts) == ["draft", "published"]


async def test_favorites_only_needs_a_login(client: httpx.AsyncClient) -> None:
    assert (await client.get("/components", params={"favoritesOnly": True})).status_code == 401


async def test_a_draft_is_readable_by_its_owner_only(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    draft = tool("draft", owner, ComponentStatus.DRAFT)
    await save(sessions, owner, stranger, draft)

    for path in (f"/components/{draft.id}", f"/components/{draft.id}/versions", f"/components/{draft.id}/download"):
        assert (await client.get(path, headers=bearer(owner))).status_code == 200, path
        # 404, not 403 - a stranger must not learn that the draft exists
        assert (await client.get(path, headers=bearer(stranger))).status_code == 404, path
        assert (await client.get(path)).status_code == 404, path


async def test_a_deprecated_version_stays_readable_by_everyone(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    deprecated = tool("old", owner, ComponentStatus.DEPRECATED)
    await save(sessions, owner, deprecated)

    response = await client.get(f"/components/{deprecated.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "deprecated"


async def test_an_unknown_id_is_404(client: httpx.AsyncClient) -> None:
    assert (await client.get(f"/components/{uuid.uuid4()}")).status_code == 404
    assert (await client.get("/components/not-a-uuid")).status_code == 422


async def test_the_owner_publishes_their_draft(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    draft = tool("t", owner, ComponentStatus.DRAFT)
    await save(sessions, owner, draft)

    response = await client.post(f"/components/{draft.id}/commands", json={"command": "PUBLISH"}, headers=bearer(owner))

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert await status_of(sessions, draft.id) == ComponentStatus.PUBLISHED


async def test_commands_are_refused_by_who_is_asking(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    published = tool("public", owner)
    draft = tool("draft", owner, ComponentStatus.DRAFT)
    await save(sessions, owner, stranger, published, draft)
    deprecate = {"command": "DEPRECATE", "note": "broken"}

    assert (await client.post(f"/components/{published.id}/commands", json=deprecate)).status_code == 401
    forbidden = await client.post(f"/components/{published.id}/commands", json=deprecate, headers=bearer(stranger))
    assert forbidden.status_code == 403
    # someone else's draft does not exist for a stranger
    hidden = await client.post(f"/components/{draft.id}/commands", json={"command": "PUBLISH"}, headers=bearer(stranger))
    assert hidden.status_code == 404
    assert await status_of(sessions, published.id) == ComponentStatus.PUBLISHED
    assert await status_of(sessions, draft.id) == ComponentStatus.DRAFT


async def test_anyone_logged_in_may_favorite_a_public_component(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, stranger = user(), user()
    published = tool("public", owner)
    await save(sessions, owner, stranger, published)

    response = await client.post(
        f"/components/{published.id}/commands", json={"command": "ADD_FAVORITE"}, headers=bearer(stranger)
    )
    assert response.status_code == 200
    favorites = await client.get("/components", params={"favoritesOnly": True}, headers=bearer(stranger))
    assert await names(favorites) == ["public"]


async def test_commands_the_state_does_not_allow_are_409(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    draft = tool("draft", owner, ComponentStatus.DRAFT)
    no_domain = tool("bare", owner, ComponentStatus.DRAFT, domains=())
    published = tool("public", owner)
    await save(sessions, owner, draft, no_domain, published)

    async def run(component_id: uuid.UUID, command: str) -> int:
        body = {"command": command, "note": "why"}
        return (await client.post(f"/components/{component_id}/commands", json=body, headers=bearer(owner))).status_code

    assert await run(draft.id, "DEPRECATE") == 409
    assert await run(published.id, "UNDEPRECATE") == 409
    assert await run(no_domain.id, "PUBLISH") == 409


async def test_a_malformed_command_is_422_and_a_missing_payload_400(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    draft = tool("draft", owner, ComponentStatus.DRAFT)
    await save(sessions, owner, draft)
    path = f"/components/{draft.id}/commands"

    assert (await client.post(path, json={"command": "SELF_DESTRUCT"}, headers=bearer(owner))).status_code == 422
    assert (await client.post(path, json={"command": "UPDATE_DOMAIN"}, headers=bearer(owner))).status_code == 400
    bad_domain = {"command": "UPDATE_DOMAIN", "domains": ["astrology"]}
    assert (await client.post(path, json=bad_domain, headers=bearer(owner))).status_code in (400, 422)


async def test_unpublishing_what_another_users_workflow_runs_is_409(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, stranger = user(), user()
    leaf = tool("leaf", owner)
    await save(sessions, owner, stranger, leaf, workflow("theirs", stranger, leaf))

    response = await client.post(f"/components/{leaf.id}/commands", json={"command": "UNPUBLISH"}, headers=bearer(owner))

    assert response.status_code == 409
    assert await status_of(sessions, leaf.id) == ComponentStatus.PUBLISHED


async def test_only_the_owner_deletes_and_only_a_draft(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    draft = tool("draft", owner, ComponentStatus.DRAFT)
    deprecated = tool("old", owner, ComponentStatus.DEPRECATED)
    await save(sessions, owner, stranger, draft, deprecated)

    assert (await client.delete(f"/components/{draft.id}")).status_code == 401
    # someone else's draft does not exist for a stranger - their public version is just not theirs
    assert (await client.delete(f"/components/{draft.id}", headers=bearer(stranger))).status_code == 404
    assert (await client.delete(f"/components/{deprecated.id}", headers=bearer(stranger))).status_code == 403
    assert (await client.delete(f"/components/{deprecated.id}", headers=bearer(owner))).status_code == 409
    assert await status_of(sessions, draft.id) == ComponentStatus.DRAFT

    assert (await client.delete(f"/components/{draft.id}", headers=bearer(owner))).status_code == 204
    assert await status_of(sessions, draft.id) is None


async def test_impact_previews_are_the_owners(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    published = tool("public", owner)
    draft = tool("draft", owner, ComponentStatus.DRAFT)
    await save(sessions, owner, stranger, published, draft)

    for preview in ("impact", "publish-impact"):
        public_path, draft_path = f"/components/{published.id}/{preview}", f"/components/{draft.id}/{preview}"
        assert (await client.get(public_path, headers=bearer(owner))).status_code == 200, preview
        assert (await client.get(draft_path, headers=bearer(owner))).status_code == 200, preview
        assert (await client.get(public_path, headers=bearer(stranger))).status_code == 403, preview
        assert (await client.get(draft_path, headers=bearer(stranger))).status_code == 404, preview
        assert (await client.get(public_path)).status_code == 401, preview


async def test_a_strangers_draft_takes_no_uploaded_version_and_shows_no_steps(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, stranger = user(), user()
    draft_tool = tool("draft-tool", owner, ComponentStatus.DRAFT)
    public_tool = tool("public-tool", owner)
    draft_flow = workflow("draft-flow", owner, public_tool, status=ComponentStatus.DRAFT)
    public_flow = workflow("public-flow", owner, public_tool)
    await save(sessions, owner, stranger, draft_tool, public_tool, draft_flow, public_flow)
    cwl = {"cwlFile": ("t.cwl", b"cwlVersion: v1.2\nclass: CommandLineTool\ninputs: {}\noutputs: {}\n")}

    async def upload(component_id: uuid.UUID) -> int:
        return (await client.post(f"/tools/{component_id}/versions", files=cwl, headers=bearer(stranger))).status_code

    assert await upload(draft_tool.id) == 404
    assert await upload(public_tool.id) == 403

    async def confirm(flow: object) -> int:
        [step] = flow.workflow.steps  # type: ignore[attr-defined]
        body = {"command": "CONFIRM"}
        return (await client.post(f"/workflows/steps/{step.id}/commands", json=body, headers=bearer(stranger))).status_code

    assert await confirm(draft_flow) == 404
    assert await confirm(public_flow) == 403


async def test_my_components_are_split_by_status_and_hold_nobody_elses(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, stranger = user(), user()
    await save(
        sessions,
        owner,
        stranger,
        tool("draft", owner, ComponentStatus.DRAFT),
        tool("public", owner),
        tool("old", owner, ComponentStatus.DEPRECATED),
        tool("foreign", stranger),
    )

    response = await client.get("/components/mine", headers=bearer(owner))
    assert response.status_code == 200
    body = response.json()
    assert {bucket: [i["name"] for i in body[bucket]["content"]] for bucket in ("published", "unpublished", "deprecated")} == {
        "published": ["public"],
        "unpublished": ["draft"],
        "deprecated": ["old"],
    }
