import uuid


class ComponentNotFoundError(Exception):
    def __init__(self, component_id: uuid.UUID, kind: str = "Component") -> None:
        # kind names what the caller asked for - /tools/{id} with a workflow's id is a
        # "Tool ... not found", even though a component with that id exists
        super().__init__(f"{kind} {component_id} not found")


class InvalidCwlError(Exception):
    def __init__(self, context: str, reason: str) -> None:
        super().__init__(f"{context} CWL could not be parsed: {reason}")


class PackagingFailedError(Exception):
    def __init__(self, repo_name: str, reason: str) -> None:
        super().__init__(f"Packaging '{repo_name}' failed: {reason}")


class PackagedCommitChangedError(Exception):
    def __init__(self, repo_name: str, expected_commit_sha: str, commit_sha: str | None) -> None:
        super().__init__(
            f"'{repo_name}' changed since it was reviewed (commit {expected_commit_sha[:7]} is now "
            f"{(commit_sha or 'unknown')[:7]}) - please review it again"
        )


class PackagingServiceUnavailableError(Exception):
    def __init__(self) -> None:
        super().__init__("The packaging service is currently unavailable, please try again later")


class AlreadyPackagedError(Exception):
    def __init__(self, repo_name: str, commit_sha: str) -> None:
        super().__init__(f"Component '{repo_name}' at commit {commit_sha} is already packaged")


class ManualUploadCannotBeRepackagedError(Exception):
    def __init__(self) -> None:
        super().__init__("Cannot repackage a manually uploaded component")


class ComponentNameAlreadyExistsError(Exception):
    """Names are the lineage key, unique across tools and workflows alike."""

    def __init__(self, name: str, hint: str = "add a new version instead of creating a new component") -> None:
        self.name = name
        super().__init__(f"A component named '{name}' already exists - {hint}")


class ComponentKindMismatchError(Exception):
    """A new version must keep its lineage's kind - a lineage never mixes tools and workflows."""

    def __init__(self, name: str, kind: str) -> None:
        super().__init__(f"'{name}' is a {kind} - a new version of it must be a {kind} too")


class MissingCommandPayloadError(Exception):
    """A command was sent without the payload field it needs (e.g. UPDATE_DOMAIN with no domain).

    The request DTO can't enforce this: one model serves every component command, so each
    payload field has to stay optional there and the per-command requirement lands here.
    """

    def __init__(self, command: str, field: str) -> None:
        super().__init__(f"Command {command} requires a '{field}'")


class ComponentUsedByOthersError(Exception):
    """Unpublishing or deleting this version would break public workflows of other users -
    they run it, and only their owners may take them out of public view."""

    def __init__(self, workflows: list[str]) -> None:
        self.workflows = workflows
        super().__init__(
            f"Used by public workflow(s) of other users: {', '.join(workflows)} - contact their owners "
            "or publish a fixed version instead"
        )


class ComponentHasPublicParentsError(Exception):
    """Unpublishing or deleting this version takes the caller's own public workflows that run
    it out of public view too - which they have to opt into."""

    def __init__(self, workflows: list[str]) -> None:
        self.workflows = workflows
        super().__init__(
            f"Used by your public workflow(s) {', '.join(workflows)} - confirm that they become drafts as well"
        )
