import uuid


class Endpoints:
    COMPONENTS_ROOT = "/components"

    @staticmethod
    def component_by_id(component_id: uuid.UUID) -> str:
        return f"{Endpoints.COMPONENTS_ROOT}/{component_id}"

    @staticmethod
    def component_favorite_by_id(component_id: uuid.UUID) -> str:
        return f"{Endpoints.component_by_id(component_id)}/favorite"
