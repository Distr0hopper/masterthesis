from pydantic import BaseModel, ConfigDict, Field

from app.api.util.http_method import HttpMethod


class Link(BaseModel):
    href: str
    method: HttpMethod = HttpMethod.GET


class LinkModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    links: dict[str, Link] = Field(default_factory=dict, alias="_links")
