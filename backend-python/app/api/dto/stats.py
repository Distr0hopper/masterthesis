from app.api.dto.base import CamelModel


class StatsDto(CamelModel):
    components_published: int
    workflows_composed: int
    contributors: int
