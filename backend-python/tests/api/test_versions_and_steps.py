"""The next version of a component over HTTP - packaged again from GitHub, repackaged by
command, uploaded by hand for a tool or a workflow - plus the tool's format labels and
rebinding a workflow's steps. The rules are the services'; these check that the routers
let exactly the right people reach them, and say no with the right status."""

import json
from collections.abc import Iterator

import httpx
import pytest

from app.domain.models.component import Component, ComponentSource, ComponentStatus
from app.domain.models.workflow_step import StepMatchStatus
from app.infrastructure.packaging.packaging_service_client import PackagingResult, PackagingServiceClient
from tests.conftest import SessionFactory
from tests.db_factories import bearer, save, tool, user, workflow

pytestmark = pytest.mark.anyio

REPO = "https://github.com/movestore/remove-outliers"

TOOL_CWL = """\
cwlVersion: v1.2
class: CommandLineTool
baseCommand: [Rscript, app.R]
inputs:
  tracks: File
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
    run:
      class: CommandLineTool
      baseCommand: [Rscript, clean.R]
      inputs: {tracks: File}
      outputs:
        cleaned: {type: File, outputBinding: {glob: out.rds}}
    in: {tracks: tracks}
    out: [cleaned]
"""


class FakePackagingService:
    """GitHub through the packaging service - its repo moves on when a test says so."""

    def __init__(self) -> None:
        self.commit = "c1"

    async def package(self, repo_url: str) -> PackagingResult:
        return PackagingResult(
            repo_name="remove-outliers",
            cwl=TOOL_CWL,
            commit_sha=self.commit,
            description="Removes outliers",
            author="MoveApps",
        )


@pytest.fixture
def github(client: httpx.AsyncClient) -> Iterator[FakePackagingService]:
    from app.main import app

    fake = FakePackagingService()
    app.dependency_overrides[PackagingServiceClient.get_client] = lambda: fake
    yield fake


def packaged(name: str, owner: object, commit: str = "c1", **kwargs: object) -> Component:
    component = tool(name, owner, **kwargs)  # type: ignore[arg-type]
    component.source = ComponentSource.AUTOMATED_PACKAGING
    component.repo_url = REPO
    component.repo_commit_sha = commit
    return component


# --- packaging from GitHub ----------------------------------------------------------------


async def test_a_repo_is_packaged_once_per_commit(
    client: httpx.AsyncClient, sessions: SessionFactory, github: FakePackagingService
) -> None:
    owner = user()
    await save(sessions, owner)
    body = {"repoUrl": REPO, "domains": ["animal_behavior"]}

    preview = await client.post("/tools/package/preview", json={"repoUrl": REPO}, headers=bearer(owner))
    assert preview.status_code == 200
    assert (preview.json()["existing"], preview.json()["alreadyPackaged"]) == (None, False)

    first = await client.post("/tools/package", json=body, headers=bearer(owner))
    assert first.status_code == 201, first.text
    assert (first.json()["version"], first.json()["source"], first.json()["status"]) == (
        1,
        "automated_packaging",
        "draft",
    )

    # the same commit again - nothing new to package
    again = await client.post("/tools/package", json=body, headers=bearer(owner))
    assert again.status_code == 409
    preview = await client.post("/tools/package/preview", json={"repoUrl": REPO}, headers=bearer(owner))
    assert preview.json()["alreadyPackaged"] is True
    assert preview.json()["existing"]["id"] == first.json()["id"]

    # the repo moved on - the next version of the same lineage
    github.commit = "c2"
    second = await client.post("/tools/package", json=body, headers=bearer(owner))
    assert second.status_code == 201, second.text
    assert (second.json()["name"], second.json()["version"]) == (first.json()["name"], 2)


async def test_a_repo_that_moved_on_since_its_review_is_not_packaged(
    client: httpx.AsyncClient, sessions: SessionFactory, github: FakePackagingService
) -> None:
    owner = user()
    await save(sessions, owner)

    reviewed = {"repoUrl": REPO, "domains": ["animal_behavior"], "expectedCommitSha": "c0"}
    response = await client.post("/tools/package", json=reviewed, headers=bearer(owner))

    assert response.status_code == 409
    assert (await client.get("/components/mine", headers=bearer(owner))).json()["unpublished"]["content"] == []


async def test_someone_elses_repo_is_previewed_but_not_packaged_again(
    client: httpx.AsyncClient, sessions: SessionFactory, github: FakePackagingService
) -> None:
    owner, stranger = user(), user()
    await save(sessions, owner, stranger, packaged("remove-outliers", owner))
    github.commit = "c2"

    # the public tool is shown as what the repo already is - but only its owner adds versions
    preview = await client.post("/tools/package/preview", json={"repoUrl": REPO}, headers=bearer(stranger))
    assert preview.status_code == 200
    assert preview.json()["existing"]["name"] == "remove-outliers"
    body = {"repoUrl": REPO, "domains": ["animal_behavior"]}
    assert (await client.post("/tools/package", json=body, headers=bearer(stranger))).status_code == 403


# --- tool commands: repackage, format labels ----------------------------------------------


async def command(client: httpx.AsyncClient, component: Component, headers: dict, **body: object) -> httpx.Response:
    return await client.post(f"/tools/{component.id}/commands", json=body, headers=headers)


async def test_repackaging_is_the_packaged_tools_owners_only(
    client: httpx.AsyncClient, sessions: SessionFactory, github: FakePackagingService
) -> None:
    owner, stranger = user(), user()
    from_github = packaged("remove-outliers", owner)
    by_hand = tool("by-hand", owner)
    await save(sessions, owner, stranger, from_github, by_hand)

    assert (await command(client, from_github, bearer(owner), command="REPACKAGE")).status_code == 409
    github.commit = "c2"
    assert (await command(client, from_github, bearer(stranger), command="REPACKAGE")).status_code == 403
    assert (await command(client, from_github, {}, command="REPACKAGE")).status_code == 401
    # nothing to repackage a hand-made tool from
    assert (await command(client, by_hand, bearer(owner), command="REPACKAGE")).status_code == 403

    response = await command(client, from_github, bearer(owner), command="REPACKAGE")
    assert response.status_code == 200, response.text
    assert (response.json()["version"], response.json()["status"]) == (2, "draft")


async def test_the_owner_labels_a_port_without_a_format(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    await save(sessions, owner, stranger)
    created = await client.post(
        "/tools",
        data={"name": "clean-tracks", "domains": "animal_behavior"},
        files={"cwlFile": ("tool.cwl", TOOL_CWL.encode())},
        headers=bearer(owner),
    )
    tool_id = created.json()["id"]
    path = f"/tools/{tool_id}/commands"
    labels = {
        "command": "UPDATE_FORMAT_LABELS",
        "formatLabels": [{"name": "tracks", "direction": "input", "label": "RDS"}],
    }

    assert (await client.post(path, json=labels, headers=bearer(stranger))).status_code == 404
    assert (await client.post(path, json={"command": "UPDATE_FORMAT_LABELS"}, headers=bearer(owner))).status_code == 400
    too_long = {**labels, "formatLabels": [{"name": "tracks", "direction": "input", "label": "x" * 65}]}
    assert (await client.post(path, json=too_long, headers=bearer(owner))).status_code == 422

    response = await client.post(path, json=labels, headers=bearer(owner))
    assert response.status_code == 200, response.text
    ports = {p["name"]: p for p in response.json()["parameters"]}
    assert (ports["tracks"]["formatLabel"], ports["tracks"]["formatLabelSource"]) == ("RDS", "manual")
    assert ports["cleaned"]["formatLabel"] is None

    # a blank label clears it again
    cleared = {**labels, "formatLabels": [{"name": "tracks", "direction": "input", "label": " "}]}
    response = await client.post(path, json=cleared, headers=bearer(owner))
    assert {p["name"]: p["formatLabel"] for p in response.json()["parameters"]}["tracks"] is None


# --- uploaded versions ------------------------------------------------------------------


async def upload_tool_version(client: httpx.AsyncClient, component: Component, headers: dict) -> httpx.Response:
    return await client.post(
        f"/tools/{component.id}/versions", files={"cwlFile": ("v2.cwl", TOOL_CWL.encode())}, headers=headers
    )


async def test_an_uploaded_tool_version_continues_the_lineage(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, stranger = user(), user()
    v1 = tool("clean-tracks", owner)
    draft = tool("secret", owner, ComponentStatus.DRAFT)
    from_github = packaged("remove-outliers", owner)
    await save(sessions, owner, stranger, v1, draft, from_github)

    assert (await upload_tool_version(client, v1, bearer(stranger))).status_code == 403
    assert (await upload_tool_version(client, draft, bearer(stranger))).status_code == 404
    # a packaged tool's versions come from its repo
    assert (await upload_tool_version(client, from_github, bearer(owner))).status_code == 409

    response = await upload_tool_version(client, v1, bearer(owner))
    assert response.status_code == 201, response.text
    assert (response.json()["name"], response.json()["version"], response.json()["status"]) == (
        "clean-tracks",
        2,
        "draft",
    )
    versions = await client.get(f"/components/{v1.id}/versions", headers=bearer(owner))
    assert [v["version"] for v in versions.json()] == [1, 2]


async def create_uploaded_workflow(client: httpx.AsyncClient, headers: dict) -> dict:
    response = await client.post(
        "/workflows",
        data={
            "name": "track-pipeline",
            "domains": "animal_behavior",
            "componentConfigs": json.dumps(
                [{"stepId": "step_clean", "name": "clean-tracks", "domains": ["animal_behavior"]}]
            ),
        },
        files={"file": ("pipeline.cwl", PIPELINE.encode())},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_an_uploaded_workflow_version_continues_the_lineage(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, stranger = user(), user()
    await save(sessions, owner, stranger)
    v1 = await create_uploaded_workflow(client, bearer(owner))
    [step] = v1["steps"]

    # the preview says what each step ran in the version it continues
    preview = await client.post(
        "/workflows/parse",
        data={"parentId": v1["id"]},
        files={"file": ("pipeline.cwl", PIPELINE.encode())},
        headers=bearer(owner),
    )
    assert preview.status_code == 200, preview.text
    [step_preview] = preview.json()["componentPreviews"]
    assert step_preview["previous"]["componentId"] == step["component"]["id"]

    # someone else's draft is no parent - for them it does not exist
    hidden = await client.post(
        "/workflows/parse",
        data={"parentId": v1["id"]},
        files={"file": ("pipeline.cwl", PIPELINE.encode())},
        headers=bearer(stranger),
    )
    assert hidden.status_code == 404

    async def add_version(headers: dict) -> httpx.Response:
        return await client.post(
            f"/workflows/{v1['id']}/versions",
            data={
                "componentConfigs": json.dumps([{"stepId": "step_clean", "reuseComponentId": step["component"]["id"]}])
            },
            files={"file": ("pipeline.cwl", PIPELINE.encode())},
            headers=headers,
        )

    assert (await add_version(bearer(stranger))).status_code == 404
    assert (await add_version({})).status_code == 401
    response = await add_version(bearer(owner))
    assert response.status_code == 201, response.text
    assert (response.json()["name"], response.json()["version"]) == ("track-pipeline", 2)
    assert response.json()["steps"][0]["component"]["id"] == step["component"]["id"]


async def test_a_builder_workflow_takes_no_uploaded_version(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    from app.domain.models.workflow_draft import WorkflowDraft

    owner = user()
    canvas = WorkflowDraft(name="canvas", canvas_state='{"nodes": [], "edges": []}', created_by_id=owner.id)
    built = workflow("built", owner, status=ComponentStatus.DRAFT)
    built.source = ComponentSource.WORKFLOW_BUILDER
    built.workflow.draft_id = canvas.id  # type: ignore[union-attr]
    await save(sessions, owner, canvas, built)

    response = await client.post(
        f"/workflows/{built.id}/versions",
        data={"componentConfigs": "[]"},
        files={"file": ("pipeline.cwl", PIPELINE.encode())},
        headers=bearer(owner),
    )
    # its versions come from its canvas
    assert response.status_code == 409


# --- rebinding steps --------------------------------------------------------------------


async def test_the_owner_rebinds_and_confirms_a_draft_workflows_step(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner, stranger = user(), user()
    old, new = tool("old", owner), tool("new", owner)
    foreign_draft = tool("foreign-draft", stranger, ComponentStatus.DRAFT)
    flow = workflow("flow", owner, old, status=ComponentStatus.DRAFT)
    await save(sessions, owner, stranger, old, new, foreign_draft, flow)
    [step] = flow.workflow.steps  # type: ignore[union-attr]
    path = f"/workflows/steps/{step.id}"

    assert (await client.patch(path, json={"componentId": str(new.id)}, headers=bearer(stranger))).status_code == 404
    # a step only runs what its owner may read
    bound_foreign = await client.patch(path, json={"componentId": str(foreign_draft.id)}, headers=bearer(owner))
    assert bound_foreign.status_code == 404

    rebound = await client.patch(path, json={"componentId": str(new.id)}, headers=bearer(owner))
    assert rebound.status_code == 200, rebound.text
    assert (rebound.json()["component"]["id"], rebound.json()["matchStatus"]) == (
        str(new.id),
        StepMatchStatus.SUGGESTED.value,
    )

    confirmed = await client.post(f"{path}/commands", json={"command": "CONFIRM"}, headers=bearer(owner))
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["matchStatus"] == StepMatchStatus.CONFIRMED.value

    cleared = await client.patch(path, json={"componentId": None}, headers=bearer(owner))
    assert (cleared.json()["component"], cleared.json()["matchStatus"]) == (None, StepMatchStatus.UNMATCHED.value)
    # nothing bound, nothing to confirm
    assert (
        await client.post(f"{path}/commands", json={"command": "CONFIRM"}, headers=bearer(owner))
    ).status_code == 400


async def test_a_step_cannot_make_its_workflow_contain_itself(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    leaf = tool("leaf", owner)
    flow = workflow("flow", owner, leaf, status=ComponentStatus.DRAFT)
    await save(sessions, owner, leaf, flow)
    [step] = flow.workflow.steps  # type: ignore[union-attr]

    response = await client.patch(
        f"/workflows/steps/{step.id}", json={"componentId": str(flow.id)}, headers=bearer(owner)
    )
    assert response.status_code == 409


async def test_a_published_workflows_steps_are_locked(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner, stranger = user(), user()
    old, new = tool("old", owner), tool("new", owner)
    flow = workflow("flow", owner, old)
    await save(sessions, owner, stranger, old, new, flow)
    [step] = flow.workflow.steps  # type: ignore[union-attr]
    path = f"/workflows/steps/{step.id}"

    assert (await client.patch(path, json={"componentId": str(new.id)}, headers=bearer(owner))).status_code == 409
    assert (await client.patch(path, json={"componentId": str(new.id)}, headers=bearer(stranger))).status_code == 403
    assert (await client.patch(path, json={"componentId": str(new.id)})).status_code == 401
