import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.component import Component


class ParameterDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class Parameter(SQLModel, table=True):
    __tablename__ = "parameters"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    cwl_type: str
    default_value: str | None = None
    description: str | None = None
    format: str | None = None
    # resolved human-readable name for `format` (an ontology identifier, e.g. EDAM) -
    # populated later by a separate resolution call against an external endpoint, not by
    # anything in this codebase yet
    format_label: str | None = None
    # explicit String column: SQLModel would otherwise infer a native Postgres
    # enum type from the Python Enum, which we deliberately avoided (see the
    # hand-written migration - VARCHAR only, no CREATE TYPE)
    direction: ParameterDirection = Field(default=ParameterDirection.INPUT, sa_column=Column(String, nullable=False))
    component_id: uuid.UUID | None = Field(
        default=None, sa_column=Column(ForeignKey("components.id", ondelete="CASCADE"), nullable=True)
    )

    # lazy="selectin": see the matching note on Component - required for AsyncSession safety
    component: Optional["Component"] = Relationship(back_populates="parameters", sa_relationship_kwargs={"lazy": "selectin"})