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


class AlreadyPackagedError(Exception):
    def __init__(self, repo_name: str, commit_sha: str) -> None:
        super().__init__(f"Component '{repo_name}' at commit {commit_sha} is already packaged")


class ManualUploadCannotBeRepackagedError(Exception):
    def __init__(self) -> None:
        super().__init__("Cannot repackage a manually uploaded component")


class ComponentNameAlreadyExistsError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"A component named '{name}' already exists - add a new version instead of creating a new component")