import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.workflow import Workflow


class WorkflowFile(SQLModel, table=True):
    """An auxiliary file the pipeline CWL cannot do without - a $import/$include target,
    typically SchemaDefRequirement type definitions.

    Keyed by the path exactly as the document writes it (`types/spatial.yml`), because that
    is the path that has to resolve when the archive is written back out. Flattening it to
    a basename would leave the $import pointing at nothing.
    """

    __tablename__ = "workflow_files"

    workflow_id: uuid.UUID = Field(sa_column=Column(ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True))
    path: str = Field(primary_key=True)
    content: str = Field(sa_column=Column(Text, nullable=False))

    workflow: "Workflow" = Relationship(back_populates="files", sa_relationship_kwargs={"lazy": "selectin"})
