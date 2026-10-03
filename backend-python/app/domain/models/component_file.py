import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.component import Component


class ComponentFile(SQLModel, table=True):
    """An auxiliary file this component's CWL cannot do without - a $import/$include
    target, typically SchemaDefRequirement type definitions.

    Keyed by the path exactly as the document writes it (`types/spatial.yml`), because that
    is the path that has to resolve when the archive is written back out. Flattening it to
    a basename would leave the $import pointing at nothing.

    A component is a standalone catalogue entry, so a tool that imports type definitions
    has to carry them itself; the workflow it arrived with is not guaranteed to be around.
    """

    __tablename__ = "component_files"

    component_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("components.id", ondelete="CASCADE"), primary_key=True)
    )
    path: str = Field(primary_key=True)
    content: str = Field(sa_column=Column(Text, nullable=False))

    component: "Component" = Relationship(back_populates="files", sa_relationship_kwargs={"lazy": "selectin"})
