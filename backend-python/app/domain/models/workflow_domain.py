import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.workflow import Workflow


class WorkflowDomain(SQLModel, table=True):
    __tablename__ = "workflow_domains"

    workflow_id: uuid.UUID = Field(sa_column=Column(ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True))
    # validated against VALID_DOMAINS at the DTO boundary, not a DB-backed FK - domains
    # are static JSON config (app/domain/models/component_domain.py), not a real table
    domain: str = Field(primary_key=True)

    workflow: "Workflow" = Relationship(back_populates="domains", sa_relationship_kwargs={"lazy": "selectin"})
