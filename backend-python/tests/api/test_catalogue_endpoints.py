"""The smaller endpoints around the catalogue over HTTP: favorites, the profile, name
availability while typing, the home page's stats and latest additions, domains, health."""

import httpx
import pytest

from app.domain.models.component import ComponentStatus
from app.domain.models.component_domain import VALID_DOMAINS
from tests.conftest import SessionFactory
from tests.db_factories import bearer, save, tool, user, workflow

pytestmark = pytest.mark.anyio


async def favorite(client: httpx.AsyncClient, component: object, headers: dict, command: str = "ADD_FAVORITE") -> int:
    path = f"/components/{component.id}/commands"  # type: ignore[attr-defined]
    return (await client.post(path, json={"command": command}, headers=headers)).status_code


async def favorite_names(client: httpx.AsyncClient, headers: dict) -> list[str]:
    response = await client.get("/components", params={"favoritesOnly": True}, headers=headers)
    return [item["name"] for item in response.json()["content"]]


async def test_a_favorite_is_the_whole_lineage_and_adding_twice_is_harmless(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, fan = user(), user()
    v1 = tool("t", owner, ComponentStatus.DEPRECATED)
    v2 = tool("t", owner, version=2)
    await save(sessions, owner, fan, v1, v2)

    assert await favorite(client, v1, bearer(fan)) == 200
    assert await favorite(client, v1, bearer(fan)) == 200
    assert await favorite_names(client, bearer(fan)) == ["t"]
    # every version of it reads as a favorite
    detail = await client.get(f"/components/{v2.id}", headers=bearer(fan))
    assert detail.json()["isFavorite"] is True
    # and nobody else's list changes
    assert await favorite_names(client, bearer(owner)) == []

    assert await favorite(client, v2, bearer(fan), "REMOVE_FAVORITE") == 200
    assert await favorite(client, v2, bearer(fan), "REMOVE_FAVORITE") == 200
    assert await favorite_names(client, bearer(fan)) == []


async def test_someone_elses_draft_cannot_be_favorited(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    draft = tool("draft", owner, ComponentStatus.DRAFT)
    await save(sessions, owner, stranger, draft)

    assert await favorite(client, draft, bearer(stranger)) == 404
    assert await favorite(client, draft, {}) == 401


async def test_the_profile_changes_only_the_fields_sent(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    owner.first_name, owner.last_name, owner.affiliation = "Ada", "Lovelace", "Uni"
    await save(sessions, owner)

    response = await client.patch("/users/me", json={"affiliation": "JMU"}, headers=bearer(owner))
    assert response.status_code == 200
    assert (response.json()["firstName"], response.json()["affiliation"]) == ("Ada", "JMU")

    # an explicit null clears - unlike a field left out
    response = await client.patch("/users/me", json={"lastName": None}, headers=bearer(owner))
    assert (response.json()["firstName"], response.json()["lastName"]) == ("Ada", None)

    # saved, not just echoed
    me = (await client.get("/users/me", headers=bearer(owner))).json()
    assert (me["firstName"], me["lastName"], me["affiliation"]) == ("Ada", None, "JMU")


async def test_the_profile_cannot_change_the_email(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user("me@example.com")
    await save(sessions, owner)

    await client.patch("/users/me", json={"email": "other@example.com"}, headers=bearer(owner))
    assert (await client.get("/users/me", headers=bearer(owner))).json()["email"] == "me@example.com"


async def test_a_name_is_taken_across_kinds_but_a_strangers_draft_shows_no_details(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, stranger = user(), user()
    public = tool("public-tool", owner)
    await save(sessions, owner, stranger, public, tool("secret-draft", owner, ComponentStatus.DRAFT))

    async def availability(name: str, headers: dict, **params: str) -> dict:
        response = await client.get("/components/name-availability", params={"name": name, **params}, headers=headers)
        assert response.status_code == 200
        return response.json()

    free = await availability("brand-new", bearer(stranger))
    assert (free["available"], free["existing"]) == (True, None)

    taken = await availability("public-tool", bearer(stranger))
    assert taken["available"] is False
    assert taken["existing"]["id"] == str(public.id)

    # taken, but nothing about whose draft it is
    hidden = await availability("secret-draft", bearer(stranger))
    assert (hidden["available"], hidden["existing"]) == (False, None)
    assert (await availability("secret-draft", bearer(owner)))["existing"] is not None

    # renaming a component keeps its own name free for itself
    own = await availability("public-tool", bearer(owner), excludeId=str(public.id))
    assert own["available"] is True

    assert (await client.get("/components/name-availability", params={"name": ""})).status_code == 422


async def test_stats_count_published_lineages_and_their_contributors(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, other, drafter = user(), user(), user()
    leaf = tool("leaf", owner)
    await save(
        sessions,
        owner,
        other,
        drafter,
        leaf,
        tool("leaf", owner, ComponentStatus.DEPRECATED, version=2),
        tool("other", other),
        tool("draft", drafter, ComponentStatus.DRAFT),
        workflow("flow", owner, leaf),
    )

    response = await client.get("/stats")
    assert response.json() == {"toolsPublished": 2, "workflowsPublished": 1, "contributors": 2}


async def test_the_latest_additions_are_only_published_ones(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner, tool("public", owner), tool("draft", owner, ComponentStatus.DRAFT))

    response = await client.get("/components/latest", params={"limit": 6})
    assert [item["name"] for item in response.json()] == ["public"]


async def test_domains_and_health(client: httpx.AsyncClient) -> None:
    domains = (await client.get("/domains")).json()
    assert [d["id"] for d in domains] == VALID_DOMAINS
    assert all(d["color"].startswith("#") for d in domains)

    assert (await client.get("/health")).json() == {"status": "ok", "database": "connected"}
