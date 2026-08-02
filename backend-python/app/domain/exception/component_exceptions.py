import uuid


class ComponentNotFoundError(Exception):
    def __init__(self, component_id: uuid.UUID) -> None:
        super().__init__(f"Component {component_id} not found")