"""A workflow's archive - its download and the builder's export - holds its whole tree,
each nested workflow in a folder of its own: every `run:` must resolve next to the
document that writes it, even where a nested workflow runs another version of a tool its
parent runs too."""

import io
import json
import posixpath
import zipfile

import httpx
import pytest
import yaml

from app.domain.models.component import ComponentStatus
from app.domain.models.workflow_draft import WorkflowDraft
from tests.conftest import SessionFactory
from tests.db_factories import TOOL_CWL, bearer, save, tool, user, workflow

pytestmark = pytest.mark.anyio


def pipeline(*children: str) -> str:
    """A pipeline in the shape db_factories.workflow binds: step_<name> runs <name>.cwl."""
    steps = "".join(f"  step_{c}:\n    run: {c}.cwl\n    in: {{}}\n    out: []\n" for c in children)
    return f"cwlVersion: v1.2\nclass: Workflow\ninputs: {{}}\noutputs: {{}}\nsteps:\n{steps}"


def unresolved_runs(content: bytes) -> list[str]:
    """Every `run:` in the archive that names no file next to its document."""
    archive = zipfile.ZipFile(io.BytesIO(content))
    names = set(archive.namelist())
    missing = []
    for name in names:
        document = yaml.safe_load(archive.read(name))
        if not isinstance(document, dict) or document.get("class") != "Workflow":
            continue
        for step in document["steps"].values():
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), step["run"]))
            if target not in names:
                missing.append(f"{name}: {step['run']}")
    return missing


async def test_a_workflow_downloads_although_a_nested_one_runs_another_version_of_its_tool(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    v1 = tool("clean", owner, ComponentStatus.DEPRECATED)
    v1.cwl_content = TOOL_CWL + "# v1\n"
    v2 = tool("clean", owner, version=2)
    v2.cwl_content = TOOL_CWL + "# v2\n"
    inner = workflow("inner", owner, v1)
    inner.cwl_content = pipeline("clean")
    outer = workflow("outer", owner, v2, inner)
    outer.cwl_content = pipeline("clean", "inner")
    await save(sessions, owner, v1, v2)
    await save(sessions, inner)
    await save(sessions, outer)

    response = await client.get(f"/components/{outer.id}/download")

    assert response.status_code == 200, response.text
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert sorted(archive.namelist()) == ["clean.cwl", "inner/clean.cwl", "inner/inner.cwl", "outer.cwl"]
    assert archive.read("clean.cwl").decode().endswith("# v2\n")
    assert archive.read("inner/clean.cwl").decode().endswith("# v1\n")
    assert unresolved_runs(response.content) == []
    # the stored pipeline is untouched - only the archive's copy points into the folder
    assert "run: inner.cwl" in outer.cwl_content


async def test_a_canvas_running_a_workflow_exports_it_in_its_own_folder(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    clean = tool("clean", owner)
    inner = workflow("inner", owner, clean)
    inner.cwl_content = pipeline("clean")
    other = tool("other", owner)
    await save(sessions, owner, clean, other)
    await save(sessions, inner)
    nodes = [
        {"id": f"n{i}", "position": {"x": i * 200, "y": 0}, "data": {"componentId": str(c.id)}}
        for i, c in enumerate((other, inner))
    ]
    draft = WorkflowDraft(name="Outer", canvas_state=json.dumps({"nodes": nodes, "edges": []}), created_by_id=owner.id)
    await save(sessions, draft)

    response = await client.get(f"/workflow-drafts/{draft.id}/export", headers=bearer(owner))

    assert response.status_code == 200, response.text
    names = sorted(zipfile.ZipFile(io.BytesIO(response.content)).namelist())
    assert names == ["inner/clean.cwl", "inner/inner.cwl", "other.cwl", "outer.cwl"]
    assert unresolved_runs(response.content) == []
