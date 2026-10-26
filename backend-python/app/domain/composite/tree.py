"""Operations over the Component composite - a Workflow's steps run Tools (the leaves) or
other Workflows (nested composites).

Pure functions over already-loaded Components: nothing here queries the database, so a
tree has to be loaded first (see ComponentsRepository.load_tree). Each one walks the
structure the same way a caller would want it treated - uniformly, whatever the kind.
"""

import posixpath
from collections.abc import Iterator
from dataclasses import dataclass, field

from app.domain.models.component import Component


class ConflictingTreeFileError(ValueError):
    """Two components in one tree need different contents under the same file name in one
    folder - an archive cannot hold both."""

    def __init__(self, path: str, imported: bool = False) -> None:
        self.path = path
        #: an imported file rather than a step document
        self.imported = imported
        super().__init__(path)


def walk(root: Component) -> Iterator[Component]:
    """Every component in the tree, depth-first and parent before children, each once.

    A component used by several steps (or at several levels) is yielded only the first
    time it is reached - the tree is really a DAG.
    """
    seen: set = set()
    pending = [root]
    while pending:
        component = pending.pop()
        if component.id in seen:
            continue
        seen.add(component.id)
        yield component
        # reversed, so the first child is visited first
        pending.extend(reversed(component.children))


def descendants(root: Component) -> list[Component]:
    """Every component below `root`, without `root` itself."""
    return [c for c in walk(root) if c.id != root.id]


def leaf_tools(root: Component) -> list[Component]:
    """Every Tool the tree eventually runs - the leaves of the composite."""
    return [c for c in walk(root) if c.is_tool]


def contains_lineage(root: Component, name: str) -> bool:
    """Whether any component in the tree, `root` included, belongs to the lineage `name`."""
    return any(c.name == name for c in walk(root))


def would_create_cycle(parent: Component, child: Component) -> bool:
    """Whether running `child` as a step of `parent` would make a workflow contain itself.

    Compared by lineage, not by version row: v1 of a workflow nesting its own v2 is just
    as much a self-reference - the next version would nest the one after, forever.
    """
    return contains_lineage(child, parent.name)


def _join(folder: str, path: str) -> str:
    return posixpath.normpath(posixpath.join(folder, path)) if folder else posixpath.normpath(path)


@dataclass
class ArchiveLayout:
    """Where every document of a tree goes in one archive - each nested workflow in a
    folder of its own, so its steps resolve next to it and two nested workflows never
    fight over a file name (e.g. each running another version of the same tool).

    Paths are relative to the root document's folder. A tool step keeps its `run:`; a step
    running a nested workflow points into that workflow's folder - `run: inner.cwl`
    becomes `run: inner/inner.cwl` - recorded in `retargets` for the archive's copy only:
    the stored CWL never changes. Raises ConflictingTreeFileError when one folder would
    need two different files under one name."""

    #: {path: component} of every document below the root
    documents: dict[str, Component] = field(default_factory=dict)
    #: {path: content} of every $import/$include target, next to the document importing it
    imported: dict[str, str] = field(default_factory=dict)
    #: {document path, "" for the root: {step id: its new run:}} - only the steps that move
    retargets: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def of(cls, root: Component) -> "ArchiveLayout":
        """The layout of `root`'s whole tree - `root` with its tree loaded."""
        layout = cls()
        layout._place_contents(root, "", "")
        return layout

    def place(self, child: Component, run_reference: str, folder: str) -> str:
        """Put `child`, run as `run_reference` by a document in `folder`, into the archive
        with everything below it. Returns the `run:` that document needs for it."""
        if not child.is_workflow:
            path = _join(folder, run_reference)
            if self._add_document(path, child):
                self._add_imports(child, folder)
            return run_reference

        subfolder = _join(folder, posixpath.splitext(run_reference)[0])
        path = _join(subfolder, posixpath.basename(run_reference))
        if self._add_document(path, child):
            self._place_contents(child, path, subfolder)
        return posixpath.relpath(path, folder or ".")

    def _place_contents(self, workflow: Component, path: str, folder: str) -> None:
        self._add_imports(workflow, folder)
        for step in workflow.steps:
            if step.component is None:
                continue
            run = self.place(step.component, step.run_reference, folder)
            if run != step.run_reference:
                self.retargets.setdefault(path, {})[step.step_id] = run

    def _add_document(self, path: str, component: Component) -> bool:
        """Whether `component` is new at `path` - False when it already sits there. Two
        workflows with one CWL can still run different children, so those must be one."""
        existing = self.documents.get(path)
        if existing is None:
            self.documents[path] = component
            return True
        same_workflow = not component.is_workflow or existing.id == component.id
        if existing.cwl_content != component.cwl_content or not same_workflow:
            raise ConflictingTreeFileError(path)
        return False

    def _add_imports(self, component: Component, folder: str) -> None:
        # the same type file legitimately arrives from several components - identical
        # content, so de-duplication is right; different content has no correct answer
        for file in component.files:
            path = _join(folder, file.path)
            if self.imported.setdefault(path, file.content) != file.content:
                raise ConflictingTreeFileError(path, imported=True)


def has_nested_workflows(root: Component) -> bool:
    """Whether any step of the tree runs a workflow - CWL then needs SubworkflowFeatureRequirement."""
    return any(child.is_workflow for child in descendants(root))
