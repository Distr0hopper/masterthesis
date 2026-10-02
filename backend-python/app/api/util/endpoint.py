import uuid


class Endpoints:
    COMPONENTS_ROOT = "/components"
    TOOLS_ROOT = "/tools"
    WORKFLOWS_ROOT = "/workflows"

    @staticmethod
    def component_by_id(component_id: uuid.UUID) -> str:
        return f"{Endpoints.COMPONENTS_ROOT}/{component_id}"

    @staticmethod
    def component_commands_by_id(component_id: uuid.UUID) -> str:
        return f"{Endpoints.component_by_id(component_id)}/commands"

    @staticmethod
    def component_deletion_impact_by_id(component_id: uuid.UUID) -> str:
        return f"{Endpoints.component_by_id(component_id)}/deletion-impact"

    @staticmethod
    def component_download_by_id(component_id: uuid.UUID) -> str:
        return f"{Endpoints.component_by_id(component_id)}/download"

    @staticmethod
    def tool_commands_by_id(tool_id: uuid.UUID) -> str:
        return f"{Endpoints.TOOLS_ROOT}/{tool_id}/commands"

    @staticmethod
    def tool_versions_by_id(tool_id: uuid.UUID) -> str:
        return f"{Endpoints.TOOLS_ROOT}/{tool_id}/versions"

    @staticmethod
    def workflow_step_by_id(step_id: uuid.UUID) -> str:
        return f"{Endpoints.WORKFLOWS_ROOT}/steps/{step_id}"

    @staticmethod
    def workflow_step_commands_by_id(step_id: uuid.UUID) -> str:
        return f"{Endpoints.workflow_step_by_id(step_id)}/commands"
