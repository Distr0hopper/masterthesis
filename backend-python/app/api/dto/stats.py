from app.api.dto.base import CamelModel


class StatsDto(CamelModel):
    #: distinct published tool lineages
    tools_published: int
    #: distinct published workflow lineages
    workflows_published: int
    contributors: int
