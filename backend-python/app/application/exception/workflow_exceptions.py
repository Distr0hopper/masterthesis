import uuid


class WorkflowStepNotFoundError(Exception):
    def __init__(self, step_id: uuid.UUID) -> None:
        super().__init__(f"Workflow step {step_id} not found")


class InvalidWorkflowArchiveError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid workflow archive: {reason}")


class InvalidWorkflowCwlError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid workflow CWL: {reason}")


class WorkflowStepNotMatchedError(Exception):
    def __init__(self, step_id: uuid.UUID) -> None:
        super().__init__(f"Workflow step {step_id} has no matched component to confirm")


class ConflictingAuxiliaryFileError(Exception):
    """Two sources in one workflow disagree about the contents of the same imported path.
    There is no correct file to hand back, so the download fails rather than guessing."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(
            f"Imported file '{path}' has conflicting contents across this workflow's components "
            "- the archive cannot be assembled"
        )


class ConflictingStepFileError(Exception):
    """Two different step documents of one workflow tree claim the same file name - e.g. a
    nested workflow running another version of a tool its parent also runs. Every `run:`
    reference resolves in one flat archive, which cannot hold both."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(
            f"Two different step documents of this workflow are both named '{path}' - the archive cannot hold "
            "both (does a nested workflow use another version of a tool this workflow uses too?)"
        )


class MissingImportedFileError(Exception):
    """A $import/$include target is not in the archive. Saving anyway would store a
    workflow whose CWL references a file nothing can produce - broken only at run time."""

    def __init__(self, paths: list[str]) -> None:
        self.paths = paths
        super().__init__(
            f"Imported file(s) not found in archive: {', '.join(paths)} - add them and try again"
        )


class WorkflowHasUnpublishedComponentsError(Exception):
    """A workflow may only be public once every component it uses is public - otherwise
    browsing users would hit steps pointing at components they cannot see."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        super().__init__(
            f"Component(s) {', '.join(names)} are still drafts - publish them before publishing this workflow"
        )


class UnpublishableWorkflowComponentsError(Exception):
    """The workflow depends on draft components owned by someone else, so the current user
    cannot clear the blocker themselves."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        super().__init__(
            f"Component(s) {', '.join(names)} are drafts owned by another user - ask their owner to "
            "publish them before publishing this workflow"
        )


class WorkflowNotReadyToPublishError(Exception):
    def __init__(self, workflow_id: uuid.UUID) -> None:
        super().__init__(f"Workflow {workflow_id} cannot be published until every step is confirmed")


class NestedWorkflowsNotReadyError(Exception):
    """A nested workflow publishes along with its parent, so it has to be publishable too."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        super().__init__(
            f"Nested workflow(s) {', '.join(names)} still have unconfirmed steps - confirm them before "
            "publishing this workflow"
        )


class WorkflowCycleError(Exception):
    """A step may run another workflow, but never one that (eventually) runs this one."""

    def __init__(self, workflow_name: str, child_name: str) -> None:
        super().__init__(
            f"'{child_name}' cannot be a step of '{workflow_name}' - it already contains '{workflow_name}', "
            "so the workflow would contain itself"
        )


class PublishedWorkflowStepsLockedError(Exception):
    """A published workflow is what other users see and nest - its steps only change after
    it is unpublished, or as a new version."""

    def __init__(self, workflow_id: uuid.UUID) -> None:
        super().__init__(f"Workflow {workflow_id} is published - unpublish it before changing its steps")


class UnconfiguredWorkflowStepError(Exception):
    def __init__(self, step_ids: list[str]) -> None:
        super().__init__(
            f"Step(s) {', '.join(step_ids)} have no component configuration - every step must either "
            "reuse an existing component or configure a new one before the workflow can be created"
        )


class InvalidComponentConfigError(Exception):
    def __init__(self, step_id: str, reason: str) -> None:
        super().__init__(f"Component configuration for step '{step_id}' is invalid: {reason}")


class InvalidExtractedComponentNameError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Extracted component name '{name}' is blank")


class DuplicateExtractedComponentNameError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Multiple extracted components would be named '{name}' - names must be unique within one upload")


class ExtractedComponentNameCollisionError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"A component named '{name}' already exists - rename it before creating this workflow")



class InlineStepNotBindableError(Exception):
    """An inline step carries its definition inside the pipeline - there is no component to bind."""

    def __init__(self, step_id: uuid.UUID) -> None:
        super().__init__(f"Workflow step {step_id} runs an inline definition and cannot be bound to a component")


class WorkflowRunsDeprecatedComponentsError(Exception):
    """Publishing would give deprecated versions a new public dependent - only replacing the
    steps that run them resolves it."""

    def __init__(self, components: list[str]) -> None:
        self.components = components
        super().__init__(
            f"Runs deprecated component(s) {', '.join(components)} - replace them with newer versions "
            "before publishing"
        )
