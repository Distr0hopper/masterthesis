import uuid


class ComponentNotFoundError(Exception):
    def __init__(self, component_id: uuid.UUID) -> None:
        super().__init__(f"Component {component_id} not found")


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
    def __init__(self, name: str) -> None:
        super().__init__(f"A component named '{name}' already exists - add a new version instead of creating a new component")


class MissingCommandPayloadError(Exception):
    """A command was sent without the payload field it needs (e.g. UPDATE_DOMAIN with no domain).

    The request DTO can't enforce this: one model serves every component command, so each
    payload field has to stay optional there and the per-command requirement lands here.
    """

    def __init__(self, command: str, field: str) -> None:
        super().__init__(f"Command {command} requires a '{field}'")
