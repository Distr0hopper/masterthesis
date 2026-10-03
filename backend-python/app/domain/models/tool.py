import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.component import Component


class Tool(SQLModel, table=True):
    """The leaf of the composite: what only a CommandLineTool/ExpressionTool has.

    Everything shared with workflows (name, version, CWL, ports, ...) is on the owning
    Component; this row only exists alongside one of kind TOOL.
    """

    __tablename__ = "tools"

    component_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("components.id", ondelete="CASCADE"), primary_key=True)
    )
    # the CWL `class` (CommandLineTool or ExpressionTool) - derived from the component's
    # cwl_content at write time (see cwl_parser.extract_cwl_type)
    cwl_type: str | None = None
    # derived from cwl_content (see cwl_parser.extract_dockerfile_content) - nullable because
    # manual uploads or repos without a DockerRequirement legitimately have no Dockerfile
    dockerfile_content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # also derived from cwl_content (see cwl_parser.extract_docker_pull) - mutually exclusive
    # with dockerfile_content per the CWL spec (DockerRequirement has either dockerFile or
    # dockerPull)
    docker_pull_reference: str | None = None

    component: "Component" = Relationship(back_populates="tool", sa_relationship_kwargs={"lazy": "selectin"})
