import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlmodel import Field, SQLModel


class Favorite(SQLModel, table=True):
    __tablename__ = "favorites"

    user_id: uuid.UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True))
    # the component *lineage* name, so every version favorites together - tools and
    # workflows alike, since names are unique across both kinds. Not a real FK
    # (`components.name` has no unique constraint of its own), so existence is validated in
    # ComponentsService before every write and orphans are swept when a lineage's last
    # version is deleted
    component_name: str = Field(primary_key=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
