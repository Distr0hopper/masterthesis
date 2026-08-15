import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.component import Component
    from app.domain.models.workflow import Workflow


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    first_name: str | None = None
    last_name: str | None = None
    affiliation: str | None = None
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    # lazy="selectin": see the matching note on Component - required for AsyncSession safety
    components: list["Component"] = Relationship(back_populates="created_by", sa_relationship_kwargs={"lazy": "selectin"})
    workflows: list["Workflow"] = Relationship(back_populates="created_by", sa_relationship_kwargs={"lazy": "selectin"})
