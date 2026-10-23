"""The frontend shows an action only when its rel is among a response's links - so a rel it
asks for that the backend never offers is a button that silently never appears. Every rel
the frontend source asks for must be one some link builder offers."""

import re
import uuid
from pathlib import Path

import pytest

from app.api.link.component import ComponentLinkBuilder
from app.api.link.workflow_step import WorkflowStepLinkBuilder
from app.domain.models.component import Component, ComponentKind
from app.domain.models.tool import Tool
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import WorkflowStep

FRONTEND_SRC = Path(__file__).resolve().parents[3] / "frontend" / "src"

pytestmark = pytest.mark.skipif(not FRONTEND_SRC.is_dir(), reason="needs the mono-repo's frontend/ next to the backend")

#: hasLink(links, 'publish'), getLink(model._links, 'impact'), hasAnyLink(links, ['a', 'b'])
_LINK_CALL = re.compile(r"\b(?:hasLink|getLink|hasAnyLink|hasAllLinks)\(\s*[^,]+,\s*(\[[^\]]*\]|'[^']*'|\"[^\"]*\")")
_QUOTED = re.compile(r"['\"]([A-Za-z]+)['\"]")


def _frontend_rels() -> dict[str, list[str]]:
    """{rel: [files asking for it]} across the frontend source, tests left out."""
    found: dict[str, list[str]] = {}
    for path in FRONTEND_SRC.rglob("*.ts*"):
        if ".test." in path.name:
            continue
        for argument in _LINK_CALL.findall(path.read_text(encoding="utf-8")):
            for rel in _QUOTED.findall(argument):
                found.setdefault(rel, []).append(str(path.relative_to(FRONTEND_SRC)))
    return found


def _offered_rels() -> set[str]:
    """Every rel any builder can offer - before filtering by who asks and the state."""
    tool = Component(id=uuid.uuid4(), kind=ComponentKind.TOOL, name="t", cwl_content="")
    tool.tool = Tool()
    builder_workflow = Component(id=uuid.uuid4(), kind=ComponentKind.WORKFLOW, name="w", cwl_content="")
    builder_workflow.workflow = Workflow(draft_id=uuid.uuid4())
    step = WorkflowStep(id=uuid.uuid4(), step_id="s", run_reference="t.cwl", step_order=0)

    rels: set[str] = set()
    for component in (tool, builder_workflow):
        rels |= set(ComponentLinkBuilder(None)._get_available_links(component))
    rels |= set(WorkflowStepLinkBuilder(None)._get_available_links(step))
    return rels


def test_the_frontend_finds_its_rels_in_its_own_source() -> None:
    # the scan itself works - an empty result would make the contract below pass vacuously
    assert {"publish", "delete", "confirm"} <= set(_frontend_rels())


def test_every_rel_the_frontend_asks_for_is_offered_by_the_backend() -> None:
    offered = _offered_rels()
    unknown = {rel: files for rel, files in _frontend_rels().items() if rel not in offered}
    assert unknown == {}, f"rels no backend link builder offers: {unknown}"
