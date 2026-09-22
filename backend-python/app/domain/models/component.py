import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.component_domain import ComponentDomain
    from app.domain.models.component_file import ComponentFile
    from app.domain.models.parameter import Parameter
    from app.domain.models.user import User


class ComponentSource(str, Enum):
    AUTOMATED_PACKAGING = "automated_packaging"
    MANUAL_UPLOAD = "manual_upload"


class ComponentStatus(str, Enum):
    """Mirrors WorkflowStatus - a component is staged privately until its creator publishes it."""

    DRAFT = "draft"
    PUBLISHED = "published"


MAX_DESCRIPTION_LENGTH = 2000


class Component(SQLModel, table=True):
    __tablename__ = "components"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_components_name_version"),
        Index(
            "uq_components_name_repo_commit_sha",
            "name",
            "repo_commit_sha",
            unique=True,
            postgresql_where=text("repo_commit_sha IS NOT NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    author_name: str | None = None
    created_by_id: uuid.UUID | None = Field(default=None, sa_column=Column(ForeignKey("users.id"), nullable=True))
    description: str | None = Field(default=None, sa_column=Column(String(MAX_DESCRIPTION_LENGTH), nullable=True))
    repo_url: str | None = None
    repo_commit_sha: str | None = None
    doi: str | None = None
    version: int = 1
    cwl_content: str = Field(sa_column=Column(Text, nullable=False))
    # both derived from cwl_content at write time (see cwl_parser.extract_cwl_type /
    # extract_dockerfile_content) - nullable because manual uploads or repos without a
    # DockerRequirement legitimately have no Dockerfile
    cwl_type: str | None = None
    dockerfile_content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # also derived from cwl_content (see cwl_parser.extract_docker_pull) - mutually exclusive
    # with dockerfile_content per the CWL spec (DockerRequirement has either dockerFile or
    # dockerPull);
    docker_pull_reference: str | None = None
    # explicit String column: SQLModel would otherwise infer a native Postgres
    # enum type from the Python Enum
    source: ComponentSource = Field(default=ComponentSource.MANUAL_UPLOAD, sa_column=Column(String, nullable=False))
    # Per *version row*, not per lineage: only PUBLISHED rows are publicly visible/listed (see
    # ComponentsService.list_components / get_visible_component), so a still-draft v2 never
    # hides an already-published v1 from the browse list.
    status: ComponentStatus = Field(default=ComponentStatus.DRAFT, sa_column=Column(String, nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    # lazy="selectin": default lazy loading isn't safe with AsyncSession (attribute
    # access outside an awaited context raises MissingGreenlet) - selectin issues a
    # proper follow-up SELECT as part of the same async flow instead.
    created_by: Optional["User"] = Relationship(back_populates="components", sa_relationship_kwargs={"lazy": "selectin"})
    parameters: list["Parameter"] = Relationship(back_populates="component", sa_relationship_kwargs={"lazy": "selectin"})
    domains: list["ComponentDomain"] = Relationship(
        back_populates="component",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True},
    )
    files: list["ComponentFile"] = Relationship(
        back_populates="component",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True},
    )