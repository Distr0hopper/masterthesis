import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlmodel import Field, SQLModel


class Favorite(SQLModel, table=True):
    __tablename__ = "favorites"

    user_id: uuid.UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True))
    # scoped to the component lineage (name), not a single version row - `name` has no
    # unique constraint of its own (only (name, version) does), so this can't be a real
    # FK; existence is instead validated in FavoritesService before every write
    component_name: str = Field(primary_key=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )