import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class LoginCode(SQLModel, table=True):
    """A one-time login code sent to an email. At most one per email: requesting a new one
    deletes the earlier ones, and a code is deleted once it logged someone in."""

    __tablename__ = "login_codes"
    # fetch the server-generated timestamps via RETURNING on flush - otherwise they stay
    # expired and reading one would lazy-load, which an AsyncSession cannot do
    __mapper_args__ = {"eager_defaults": True}

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True)
    code_hash: str
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    attempts: int = Field(default=0)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
