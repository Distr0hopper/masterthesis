"""Operations over the Component composite - a Workflow's steps run Tools (the leaves) or
other Workflows (nested composites).

Pure functions over already-loaded Components: nothing here queries the database, so a
tree has to be loaded first (see ComponentsRepository.load_tree). Each one walks the
structure the same way a caller would want it treated - uniformly, whatever the kind.
"""

from collections.abc import Iterator

from app.domain.models.component import Component


class ConflictingTreeFileError(ValueError):
    """Two components in one tree need different contents under the same file name - a
    flat archive cannot hold both."""

    def __init__(self, path: str) -> None:
        self.path = path
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


def step_files(root: Component) -> list[tuple[str, str]]:
    """(file name, CWL) for every step document the tree needs, recursively.

    Each step is written under its stored `run_reference` - that is what the referencing
    pipeline's `run:` points at - and a nested workflow contributes its own step files too,
    since its `run:` references resolve next to it. Raises ConflictingTreeFileError when
    two different documents claim one file name.
    """
    files: dict[str, str] = {}
    for component in walk(root):
        for step in component.steps:
            if step.component is None:
                continue
            existing = files.get(step.run_reference)
            if existing is not None and existing != step.component.cwl_content:
                raise ConflictingTreeFileError(step.run_reference)
            files[step.run_reference] = step.component.cwl_content
    return sorted(files.items())


def auxiliary_files(root: Component) -> list[tuple[str, str]]:
    """(path, content) of every $import/$include target any component in the tree needs.

    The same type file legitimately arrives from several components - identical content,
    so de-duplication is right. Genuinely different content under one path has no correct
    answer, so it raises ConflictingTreeFileError rather than picking a winner.
    """
    merged: dict[str, str] = {}
    for component in walk(root):
        for file in component.files:
            existing = merged.get(file.path)
            if existing is not None and existing != file.content:
                raise ConflictingTreeFileError(file.path)
            merged[file.path] = file.content
    return sorted(merged.items())


def has_nested_workflows(root: Component) -> bool:
    """Whether any step of the tree runs a workflow - CWL then needs SubworkflowFeatureRequirement."""
    return any(child.is_workflow for child in descendants(root))
