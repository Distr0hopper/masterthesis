"""The ComponentsRepository's SQL against a real Postgres - what the in-memory fakes of the
service tests only imitate: DISTINCT ON per lineage, the list filters, favorites first,
the recursive tree loads and the superseded_by column."""

import pytest

from app.domain.models.component import ComponentKind, ComponentStatus
from app.domain.models.favorite import Favorite
from app.domain.pagination.pagination import PaginatedList
from app.domain.repository.components_repository import ComponentListFilter, ComponentsRepository
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from tests.db_factories import SessionFactory, save, tool, user, workflow

pytestmark = pytest.mark.anyio

PUBLISHED = frozenset({ComponentStatus.PUBLISHED})
PAGE = PaginatedList(limit=50, offset=0)


async def page(
    sessions: SessionFactory, filter: ComponentListFilter, pagination: PaginatedList = PAGE
) -> tuple[list[tuple[str, int]], int]:
    async with sessions() as session:
        items, total = await ComponentsRepository(session).find_paginated(filter, pagination)
        return [(c.name, c.version) for c in items], total


async def test_a_lineage_is_listed_once_as_its_newest_matching_version(sessions: SessionFactory) -> None:
    owner = user()
    await save(
        sessions,
        owner,
        tool("a", owner, ComponentStatus.DEPRECATED, version=1),
        tool("a", owner, version=2),
        tool("a", owner, ComponentStatus.DRAFT, version=3),
        tool("b", owner),
    )

    assert await page(sessions, ComponentListFilter(statuses=PUBLISHED)) == ([("a", 2), ("b", 1)], 2)
    # without a status filter the draft v3 is the newest
    assert (await page(sessions, ComponentListFilter()))[0] == [("a", 3), ("b", 1)]


async def test_the_total_counts_lineages_not_rows_and_paging_cuts_after_distinct(sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner, *[tool(f"t{i}", owner, version=v) for i in range(3) for v in (1, 2)])

    items, total = await page(sessions, ComponentListFilter(), PaginatedList(limit=2, offset=1))
    assert total == 3
    assert items == [("t1", 2), ("t2", 2)]


async def test_drafts_are_listed_only_for_their_owner(sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    await save(sessions, owner, stranger, tool("mine", owner, ComponentStatus.DRAFT), tool("public", stranger))

    assert (await page(sessions, ComponentListFilter(statuses=PUBLISHED)))[0] == [("public", 1)]
    own = ComponentListFilter(statuses=PUBLISHED, drafts_of=owner.id)
    assert (await page(sessions, own))[0] == [("mine", 1), ("public", 1)]
    others = ComponentListFilter(statuses=PUBLISHED, drafts_of=stranger.id)
    assert (await page(sessions, others))[0] == [("public", 1)]


async def test_kind_creator_and_exclusion_filters(sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    leaf = tool("leaf", owner)
    await save(sessions, owner, stranger, leaf, workflow("flow", owner, leaf), tool("foreign", stranger), tool("orphan", None))

    assert (await page(sessions, ComponentListFilter(kind=ComponentKind.WORKFLOW)))[0] == [("flow", 1)]
    assert (await page(sessions, ComponentListFilter(created_by=owner.id)))[0] == [("flow", 1), ("leaf", 1)]
    # a component without creator is nobody's, so excluding mine keeps it
    assert (await page(sessions, ComponentListFilter(exclude_created_by=owner.id)))[0] == [
        ("foreign", 1),
        ("orphan", 1),
    ]


async def test_search_is_a_case_insensitive_substring_of_the_name(sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner, tool("Remove-Outliers", owner), tool("speed-filter", owner))

    assert (await page(sessions, ComponentListFilter(search="outlier")))[0] == [("Remove-Outliers", 1)]
    assert (await page(sessions, ComponentListFilter(search="nothing")))[0] == []


async def test_search_takes_wildcard_characters_literally(sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner, tool("speed_filter", owner), tool("speed-filter", owner), tool("100%-cover", owner))

    assert (await page(sessions, ComponentListFilter(search="_")))[0] == [("speed_filter", 1)]
    assert (await page(sessions, ComponentListFilter(search="%")))[0] == [("100%-cover", 1)]
    assert (await page(sessions, ComponentListFilter(search="\\")))[0] == []


async def test_favorites_filter_and_favorites_first(sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner, tool("a", owner), tool("b", owner), tool("c", owner))
    await save(sessions, Favorite(user_id=owner.id, component_name="c"))

    assert (await page(sessions, ComponentListFilter(favorited_by=owner.id)))[0] == [("c", 1)]
    favorites_first = ComponentListFilter(favorites_first_for=owner.id)
    assert await page(sessions, favorites_first) == ([("c", 1), ("a", 1), ("b", 1)], 3)


async def test_domains_filter_counts_domain_agnostic_as_every_domain(sessions: SessionFactory) -> None:
    owner = user()
    await save(
        sessions,
        owner,
        tool("animals", owner, domains=("animal_behavior",)),
        tool("earth", owner, domains=("earth_observation",)),
        tool("anywhere", owner, domains=("domain_agnostic",)),
    )

    assert (await page(sessions, ComponentListFilter(domains=["earth_observation"])))[0] == [
        ("anywhere", 1),
        ("earth", 1),
    ]


async def test_the_whole_tree_loads_without_lazy_loads(sessions: SessionFactory) -> None:
    owner = user()
    leaf = tool("leaf", owner)
    inner = workflow("inner", owner, leaf)
    middle = workflow("middle", owner, inner)
    outer = workflow("outer", owner, middle, leaf)
    await save(sessions, owner, leaf, inner, middle, outer)

    async with sessions() as session:
        repository = ComponentsRepository(session)
        root = await repository.find_by_id(outer.id)
        assert root is not None
        await repository.load_tree(root)

        # three levels down - any lazy load here would raise MissingGreenlet
        [middle_loaded, leaf_loaded] = root.children
        [inner_loaded] = middle_loaded.children
        assert [c.name for c in inner_loaded.children] == ["leaf"]
        assert leaf_loaded.tool is not None


async def test_ancestors_are_every_workflow_above_at_any_depth_each_once(sessions: SessionFactory) -> None:
    owner = user()
    leaf = tool("leaf", owner)
    other_version = tool("leaf", owner, version=2)
    inner = workflow("inner", owner, leaf)
    outer = workflow("outer", owner, inner, leaf)
    unrelated = workflow("unrelated", owner, other_version)
    await save(sessions, owner, leaf, other_version, inner, outer, unrelated)

    async with sessions() as session:
        ancestors = await ComponentsRepository(session).find_ancestors(leaf.id)
    assert sorted(c.name for c in ancestors) == ["inner", "outer"]


async def test_a_version_knows_the_newest_published_one_above_it(sessions: SessionFactory) -> None:
    owner = user()
    v1 = tool("t", owner, ComponentStatus.DEPRECATED, version=1)
    v2 = tool("t", owner, version=2)
    v3 = tool("t", owner, version=3)
    v4 = tool("t", owner, ComponentStatus.DRAFT, version=4)
    await save(sessions, owner, v1, v2, v3, v4)

    async with sessions() as session:
        repository = ComponentsRepository(session)
        superseded = {c.version: c.superseded_by for c in await repository.find_versions_by_name("t")}
    assert superseded == {1: (v3.id, 3), 2: (v3.id, 3), 3: None, 4: None}


async def test_renaming_a_lineage_renames_every_version_and_its_favorites(sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner, tool("old", owner), tool("old", owner, version=2), tool("keep", owner))
    await save(sessions, Favorite(user_id=owner.id, component_name="old"))

    async with sessions() as session:
        uow = SqlUnitOfWork(session)
        async with uow:
            await uow.components.rename_lineage("old", "new")
            await uow.commit()

    async with sessions() as session:
        repository = ComponentsRepository(session)
        assert [c.version for c in await repository.find_versions_by_name("new")] == [1, 2]
        assert await repository.find_versions_by_name("old") == []
        assert (await page(sessions, ComponentListFilter(favorited_by=owner.id)))[0] == [("new", 2)]


async def test_stats_count_lineages_and_contributors_of_listed_components(sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    await save(
        sessions,
        owner,
        stranger,
        tool("a", owner),
        tool("a", owner, version=2),
        tool("b", stranger, ComponentStatus.DRAFT),
    )

    async with sessions() as session:
        repository = ComponentsRepository(session)
        assert await repository.count_distinct_names(PUBLISHED) == 1
        assert await repository.count_distinct_names() == 2
        assert await repository.count_distinct_contributors(PUBLISHED) == 1
