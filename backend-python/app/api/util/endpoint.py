import uuid


class Endpoints:
    COMPONENTS_ROOT = "/components"
    WORKFLOWS_ROOT = "/workflows"

    @staticmethod
    def component_by_id(component_id: uuid.UUID) -> str:
        return f"{Endpoints.COMPONENTS_ROOT}/{component_id}"

    @staticmethod
    def component_favorite_by_id(component_id: uuid.UUID) -> str:
        return f"{Endpoints.component_by_id(component_id)}/favorite"

    @staticmethod
    def workflow_by_id(workflow_id: uuid.UUID) -> str:
        return f"{Endpoints.WORKFLOWS_ROOT}/{workflow_id}"

    @staticmethod
    def workflow_publish_by_id(workflow_id: uuid.UUID) -> str:
        return f"{Endpoints.workflow_by_id(workflow_id)}/publish"

    @staticmethod
    def workflow_step_by_id(step_id: uuid.UUID) -> str:
        return f"{Endpoints.WORKFLOWS_ROOT}/steps/{step_id}"

    @staticmethod
    def workflow_step_confirm_by_id(step_id: uuid.UUID) -> str:
        return f"{Endpoints.workflow_step_by_id(step_id)}/confirm"
