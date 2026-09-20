import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlmodel import Field, SQLModel


class FavoriteEntityType(str, Enum):
    """Which kind of entity a favorite row points at - see Favorite.entity_ref."""

    COMPONENT = "COMPONENT"
    WORKFLOW = "WORKFLOW"


class Favorite(SQLModel, table=True):
    __tablename__ = "favorites"

    user_id: uuid.UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True))
    # explicit String column, same convention as Component.source/Workflow.status - never
    # a native PG enum
    entity_type: FavoriteEntityType = Field(sa_column=Column(String, primary_key=True))
    # polymorphic reference, so what it holds depends on entity_type:
    #   COMPONENT -> the component *lineage* name, so every version favorites together
    #   WORKFLOW  -> the workflow's uuid as text, since workflows aren't versioned
    # neither can be a real FK (`components.name` has no unique constraint of its own, and
    # a single column can't point at two tables anyway), so existence is validated in
    # FavoritesService before every write and orphans are swept on delete
    entity_ref: str = Field(primary_key=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
