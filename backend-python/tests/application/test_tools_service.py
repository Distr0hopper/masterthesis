"""A tool's two paths into the catalogue - previewed first, then saved - must agree, and so
must the two ways a packaged lineage gets its next version."""

import asyncio
import uuid

import pytest

from app.application.commands.commands import ManualFormatLabel
from app.application.exception.component_exceptions import (
    AlreadyPackagedError,
    ComponentKindMismatchError,
    ManualUploadCannotBeRepackagedError,
    PackagedCommitChangedError,
    PackagedToolCannotTakeUploadError,
)
from app.application.service.components_service import ComponentsService
from app.application.service.tools_service import ToolsService
from app.domain.models.component import MAX_DESCRIPTION_LENGTH, Component, ComponentKind, ComponentSource
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.parameter import Parameter, ParameterDirection
from app.infrastructure.packaging.packaging_service_client import PackagingResult
from tests.application.fake_unit_of_work import FakeUnitOfWork
from tests.application.test_composite_workflows import FakeComponentsRepository

OWNER = uuid.uuid4()
REPO = "https://github.com/movestore/thin-data"

TOOL_CWL = """
cwlVersion: v1.2
class: CommandLineTool
doc: {doc}
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/movestore/thin-data:1.0
baseCommand: echo
inputs:
  data: File
  window: int
outputs:
  out: File
"""


class FakeRepository(FakeComponentsRepository):
    async def find_tool_by_repo_url(self, repo_url: str) -> Component | None:
        tools = [c for c in self.by_id.values() if c.repo_url == repo_url]
        return max(tools, key=lambda c: c.version, default=None)


class FakePackagingClient:
    def __init__(self, commit_sha: str = "c2", description: str | None = "From the README", cwl: str | None = None):
        self.commit_sha = commit_sha
        self.description = description
        self.cwl = cwl

    async def package(self, repo_url: str) -> PackagingResult:
        # the packager writes no top-level doc: - the README description comes alongside
        return PackagingResult(
            repo_name="thin-data",
            cwl=self.cwl or TOOL_CWL.replace("doc: {doc}\n", ""),
            inputs_yaml="",
            commit_sha=self.commit_sha,
            description=self.description,
            author="MoveApps",
        )


def service(*components: Component, packaging: FakePackagingClient | None = None) -> tuple[ToolsService, FakeRepository]:
    repository = FakeRepository(*components)
    uow = FakeUnitOfWork(components=repository)
    components_service = ComponentsService(uow, None)  # type: ignore[arg-type]
    return ToolsService(uow, components_service, packaging or FakePackagingClient()), repository  # type: ignore[arg-type]


def packaged(version: int, commit_sha: str, domains: tuple[str, ...] = ("animal_behavior",)) -> Component:
    return Component(
        id=uuid.uuid4(),
        kind=ComponentKind.TOOL,
        name="thin-data",
        version=version,
        author_name="MoveApps",
        created_by_id=OWNER,
        repo_url=REPO,
        repo_commit_sha=commit_sha,
        cwl_content="class: CommandLineTool",
        source=ComponentSource.AUTOMATED_PACKAGING,
        domains=[ComponentDomain(domain=d) for d in domains],
    )


# --- the preview is what gets saved -----------------------------------------------------


def test_the_preview_is_exactly_what_gets_saved() -> None:
    long_doc = "x" * (MAX_DESCRIPTION_LENGTH + 50)
    cwl = TOOL_CWL.format(doc=long_doc)
    tools_service, _ = service()

    preview = asyncio.run(tools_service.parse_cwl(cwl.encode()))
    saved = asyncio.run(
        tools_service.create_manual(Component(name="t", cwl_content=cwl, created_by_id=OWNER, domains=[]))
    )

    assert preview.cwl_type == saved.tool.cwl_type == "CommandLineTool"
    assert preview.docker_pull_reference == saved.tool.docker_pull_reference == "ghcr.io/movestore/thin-data:1.0"
    assert preview.dockerfile_content == saved.tool.dockerfile_content
    assert preview.ontology_url == saved.ontology_url
    assert [(p.name, p.direction, p.cwl_type) for p in preview.parameters] == [
        (p.name, p.direction, p.cwl_type) for p in saved.parameters
    ]
    # the description is cut to what the column holds - in the preview too, not only on save
    assert preview.description == saved.description == long_doc[:MAX_DESCRIPTION_LENGTH]


def test_a_package_preview_describes_the_tool_like_the_packaged_save() -> None:
    tools_service, _ = service()

    preview = asyncio.run(tools_service.preview_package(REPO))
    saved = asyncio.run(tools_service.create_from_url(REPO, ["animal_behavior"], None, OWNER))

    assert preview.parsed.description == saved.description == "From the README"
    assert [p.name for p in preview.parsed.parameters] == [p.name for p in saved.parameters]


# --- the next version of a packaged lineage ---------------------------------------------


def test_packaging_a_new_commit_adds_the_next_version_from_the_lineage_head() -> None:
    v1, v2 = packaged(1, "c0", ("earth_observation",)), packaged(2, "c1")
    tools_service, _ = service(v1, v2)

    v3 = asyncio.run(tools_service.package_next_version(v2, "My own words", expected_commit_sha="c2"))

    assert (v3.name, v3.version, v3.repo_commit_sha, v3.description) == ("thin-data", 3, "c2", "My own words")
    assert (v3.source, v3.repo_url, v3.author_name) == (ComponentSource.AUTOMATED_PACKAGING, REPO, "MoveApps")
    assert [d.domain for d in v3.domains] == ["animal_behavior"]


def test_packaging_an_unchanged_repo_is_refused() -> None:
    tools_service, repository = service(packaged(1, "c2"))
    with pytest.raises(AlreadyPackagedError):
        asyncio.run(tools_service.package_next_version(next(iter(repository.by_id.values())), None))


def test_packaging_a_commit_other_than_the_reviewed_one_is_refused() -> None:
    v1 = packaged(1, "c1")
    tools_service, _ = service(v1)
    with pytest.raises(PackagedCommitChangedError):
        asyncio.run(tools_service.package_next_version(v1, None, expected_commit_sha="c-reviewed"))


def test_repackaging_takes_the_readme_description_and_compares_against_the_lineage_head() -> None:
    # repackaging from an old version's page: the head (v2) is already at the repo's
    # commit, so there is nothing new - even though v1 itself is older
    v1, v2 = packaged(1, "c1"), packaged(2, "c2")
    tools_service, _ = service(v1, v2)
    with pytest.raises(AlreadyPackagedError):
        asyncio.run(tools_service.repackage(v1))

    tools_service, _ = service(packaged(1, "c1"), packaging=FakePackagingClient(commit_sha="c9"))
    v2 = asyncio.run(tools_service.repackage(next(iter(tools_service.uow.components.by_id.values()))))  # type: ignore[attr-defined]
    assert (v2.version, v2.repo_commit_sha, v2.description) == (2, "c9", "From the README")


def test_a_manual_upload_cannot_be_repackaged() -> None:
    manual = Component(id=uuid.uuid4(), kind=ComponentKind.TOOL, name="m", cwl_content="", created_by_id=OWNER)
    tools_service, _ = service(manual)
    with pytest.raises(ManualUploadCannotBeRepackagedError):
        asyncio.run(tools_service.repackage(manual))


def test_a_packaged_tool_takes_no_uploaded_version() -> None:
    v1 = packaged(1, "c1")
    tools_service, _ = service(v1)
    with pytest.raises(PackagedToolCannotTakeUploadError):
        asyncio.run(tools_service.add_uploaded_version(packaged(2, "c-hand")))


LABELLED_CWL = """
cwlVersion: v1.2
class: CommandLineTool
baseCommand: echo
inputs:
  data:
    type: File
outputs:
  out:
    type: File
"""


def test_an_uploaded_version_applies_its_reviewed_labels_over_the_carried_over_ones() -> None:
    cwl = LABELLED_CWL
    v1 = Component(id=uuid.uuid4(), kind=ComponentKind.TOOL, name="m", cwl_content=cwl, created_by_id=OWNER)
    tools_service, _ = service()
    asyncio.run(tools_service.create_manual(v1, format_labels=[ManualFormatLabel("data", ParameterDirection.INPUT, "CSV")]))

    v2 = asyncio.run(
        tools_service.add_uploaded_version(
            Component(kind=ComponentKind.TOOL, name="m", cwl_content=cwl, created_by_id=OWNER),
            format_labels=[ManualFormatLabel("out", ParameterDirection.OUTPUT, "GeoTIFF")],
        )
    )

    assert v2.version == 2
    labels = {p.name: p.format_label for p in v2.parameters if p.format_label}
    assert labels == {"data": "CSV", "out": "GeoTIFF"}


def test_repackaging_from_an_old_version_builds_on_the_lineage_head() -> None:
    # the head's metadata is the lineage's current truth - e.g. its domains were fixed in v2
    v1, v2 = packaged(1, "c0", ("earth_observation",)), packaged(2, "c1", ("animal_behavior",))
    tools_service, _ = service(v1, v2, packaging=FakePackagingClient(commit_sha="c9"))

    v3 = asyncio.run(tools_service.repackage(v1))

    assert v3.version == 3
    assert [d.domain for d in v3.domains] == ["animal_behavior"]


# --- a tool's next version, read and saved ------------------------------------------------

#: File ports written out in full - the shorthand `data: File` is read as a string port
LABELLABLE_CWL = """
cwlVersion: v1.2
class: CommandLineTool
baseCommand: echo
inputs:
  data:
    type: File
outputs:
  out:
    type: File
"""


def manual(version: int) -> Component:
    return Component(
        id=uuid.uuid4(),
        kind=ComponentKind.TOOL,
        name="m",
        version=version,
        cwl_content=LABELLABLE_CWL,
        created_by_id=OWNER,
    )


def upload(name: str = "m") -> Component:
    """A tool's next version as the upload endpoint hands it over - not yet numbered."""
    return Component(kind=ComponentKind.TOOL, name=name, cwl_content=LABELLABLE_CWL, created_by_id=OWNER)


def test_an_uploaded_version_follows_the_lineages_newest_one() -> None:
    # uploaded from v1's page while v2 already exists - the new one is v3, not a second v2
    v1, v2 = manual(1), manual(2)
    tools_service, _ = service(v1, v2)

    v3 = asyncio.run(tools_service.add_uploaded_version(upload()))

    assert v3.version == 3


def test_a_workflow_lineage_takes_no_tool_version() -> None:
    workflow = Component(
        id=uuid.uuid4(), kind=ComponentKind.WORKFLOW, name="m", cwl_content="class: Workflow", created_by_id=OWNER
    )
    tools_service, _ = service(workflow)

    with pytest.raises(ComponentKindMismatchError):
        asyncio.run(tools_service.add_uploaded_version(upload()))


@pytest.mark.parametrize(("commit_sha", "already_packaged"), [("c1", True), ("c2", False)])
def test_the_preview_of_a_packaged_repo_names_its_tool_and_carries_its_labels(
    commit_sha: str, already_packaged: bool
) -> None:
    head = packaged(1, "c1")
    head.parameters = [Parameter(name="data", cwl_type="File", direction=ParameterDirection.INPUT, format_label="CSV")]
    tools_service, _ = service(head, packaging=FakePackagingClient(commit_sha=commit_sha, cwl=LABELLABLE_CWL))

    preview = asyncio.run(tools_service.preview_package(REPO))

    # the wizard locks name and domains to it, or stops when there's nothing new
    assert preview.existing is head
    assert preview.already_packaged is already_packaged
    # reviewed on top of the labels the new version will carry over anyway
    assert {p.name: p.format_label for p in preview.parsed.parameters if p.format_label} == {"data": "CSV"}


def test_a_repo_never_packaged_has_no_tool_to_version() -> None:
    tools_service, _ = service()
    preview = asyncio.run(tools_service.preview_package(REPO))
    assert (preview.existing, preview.already_packaged) == (None, False)
