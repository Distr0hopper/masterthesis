import uuid
import zipfile
from io import BytesIO
from typing import Annotated

from fastapi import Depends

from app.application.exception.component_exceptions import ComponentNotFoundError
from app.application.exception.workflow_exceptions import (
    InvalidWorkflowArchiveError,
    WorkflowNotFoundError,
    WorkflowStepNotFoundError,
)
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_domain import WorkflowDomain
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep
from app.domain.repository.components_repository import ComponentsRepository
from app.domain.repository.workflows_repository import WorkflowsRepository
from app.infrastructure.cwl.cwl_matcher import best_match
from app.infrastructure.cwl.workflow_parser import extract_workflow_steps, find_workflow_file


class WorkflowsService:
    def __init__(self, workflows_repository: WorkflowsRepository, components_repository: ComponentsRepository):
        self.workflows_repository = workflows_repository
        self.components_repository = components_repository

    @staticmethod
    def get_service(
        workflows_repository: Annotated[WorkflowsRepository, Depends(WorkflowsRepository.get_repository)],
        components_repository: Annotated[ComponentsRepository, Depends(ComponentsRepository.get_repository)],
    ) -> "WorkflowsService":
        return WorkflowsService(workflows_repository, components_repository)

    async def list_workflows(self, domain: str | None = None) -> list[Workflow]:
        return await self.workflows_repository.find_all(domain)

    async def get_workflow(self, workflow_id: uuid.UUID) -> Workflow:
        workflow = await self.workflows_repository.find_by_id(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)
        return workflow

    async def create_from_zip(
        self,
        zip_bytes: bytes,
        name: str,
        description: str | None,
        domains: list[str],
        created_by_id: uuid.UUID,
    ) -> Workflow:
        files = self._extract_zip_files(zip_bytes)

        try:
            _pipeline_filename, pipeline_content = find_workflow_file(files)
        except ValueError as err:
            raise InvalidWorkflowArchiveError(str(err)) from err

        try:
            parsed_steps = extract_workflow_steps(pipeline_content)
        except ValueError as err:
            raise InvalidWorkflowArchiveError(str(err)) from err

        missing = [s.run_reference for s in parsed_steps if s.run_reference not in files]
        if missing:
            raise InvalidWorkflowArchiveError(f"Referenced step file(s) not found in archive: {', '.join(missing)}")

        # latest version per lineage of every existing Component - the fuzzy matcher
        # compares against lineage names, but the id returned still pins one specific version
        all_components = await self.components_repository.find_all()
        candidates = [(c.id, c.name) for c in all_components]

        steps: list[WorkflowStep] = []
        for parsed in parsed_steps:
            match = best_match(parsed.run_reference, candidates)
            if match is not None:
                component_id, _name, score = match
                steps.append(
                    WorkflowStep(
                        step_id=parsed.step_id,
                        run_reference=parsed.run_reference,
                        step_order=parsed.order,
                        component_id=component_id,
                        match_status=StepMatchStatus.SUGGESTED,
                        match_score=score,
                    )
                )
            else:
                steps.append(
                    WorkflowStep(
                        step_id=parsed.step_id,
                        run_reference=parsed.run_reference,
                        step_order=parsed.order,
                        match_status=StepMatchStatus.UNMATCHED,
                    )
                )

        workflow = Workflow(
            name=name,
            description=description,
            created_by_id=created_by_id,
            cwl_content=pipeline_content,
            steps=steps,
            domains=[WorkflowDomain(domain=d) for d in domains],
        )
        return await self._save_and_reload(workflow)

    async def get_step_with_workflow(self, step_id: uuid.UUID) -> tuple[WorkflowStep, Workflow]:
        step = await self.workflows_repository.find_step_by_id(step_id)
        if step is None:
            raise WorkflowStepNotFoundError(step_id)
        workflow = await self.get_workflow(step.workflow_id)
        return step, workflow

    async def update_step_component(self, step_id: uuid.UUID, component_id: uuid.UUID | None) -> WorkflowStep:
        step = await self.workflows_repository.find_step_by_id(step_id)
        if step is None:
            raise WorkflowStepNotFoundError(step_id)

        if component_id is not None:
            component = await self.components_repository.find_by_id(component_id)
            if component is None:
                raise ComponentNotFoundError(component_id)
            step.component_id = component_id
            step.match_status = StepMatchStatus.CONFIRMED
        else:
            step.component_id = None
            step.match_status = StepMatchStatus.UNMATCHED
            step.match_score = None

        return await self.workflows_repository.save_step(step)

    async def remove(self, workflow: Workflow) -> None:
        await self.workflows_repository.delete(workflow)

    async def get_download(self, workflow: Workflow) -> tuple[str, bytes]:
        # rebuilds the zip: the pipeline CWL plus each matched step's Component CWL,
        # written under its original run_reference filename - unmatched steps are
        # skipped, resolving that gap is out of scope for this feature
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("pipeline.cwl", workflow.cwl_content)
            for step in workflow.steps:
                if step.component is not None:
                    zf.writestr(step.run_reference, step.component.cwl_content)
        return f"{workflow.name}.zip", buffer.getvalue()

    def _extract_zip_files(self, zip_bytes: bytes) -> dict[str, str]:
        try:
            with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                bad_file = zf.testzip()
                if bad_file is not None:
                    raise InvalidWorkflowArchiveError(f"Corrupt file in archive: {bad_file}")
                result: dict[str, str] = {}
                for info in zf.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".cwl"):
                        continue
                    # flatten to basename - CWL run: references are filenames, not paths;
                    # tolerate a zip that wraps everything in a single top-level folder
                    basename = info.filename.rsplit("/", 1)[-1]
                    # skip macOS AppleDouble sidecar files (e.g. "._pipeline.cwl") and the
                    # __MACOSX/ dir Finder adds automatically when zipping - these mirror
                    # real filenames but hold binary resource-fork data, not CWL content
                    if basename.startswith("._") or info.filename.startswith("__MACOSX/"):
                        continue
                    try:
                        result[basename] = zf.read(info).decode("utf-8")
                    except UnicodeDecodeError as err:
                        raise InvalidWorkflowArchiveError(f"'{basename}' is not valid UTF-8 text") from err
                if not result:
                    raise InvalidWorkflowArchiveError("Archive contains no .cwl files")
                return result
        except zipfile.BadZipFile as err:
            raise InvalidWorkflowArchiveError("Not a valid zip archive") from err

    async def _save_and_reload(self, workflow: Workflow) -> Workflow:
        saved = await self.workflows_repository.save(workflow)
        reloaded = await self.workflows_repository.find_by_id(saved.id)
        assert reloaded is not None
        return reloaded
