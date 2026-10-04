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
    from app.domain.models.tool import Tool
    from app.domain.models.user import User
    from app.domain.models.workflow import Workflow
    from app.domain.models.workflow_step import WorkflowStep


class ComponentKind(str, Enum):
    """Which child of the composite a Component is - CWL's Process subclasses, narrowed to
    the two this repository models. A Tool is a leaf (CommandLineTool / ExpressionTool),
    a Workflow is a composite whose steps run other Components."""

    TOOL = "tool"
    WORKFLOW = "workflow"


class ComponentSource(str, Enum):
    AUTOMATED_PACKAGING = "automated_packaging"
    MANUAL_UPLOAD = "manual_upload"
    #: workflows only - generated from a builder canvas (see Workflow.draft_id)
    WORKFLOW_BUILDER = "workflow_builder"


class ComponentStatus(str, Enum):
    """A component is staged privately until its creator publishes it. A published version
    can later be deprecated: still readable, and everything already running it keeps
    working, but it is no longer listed or offered for new use (see composite.lifecycle)."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


MAX_DESCRIPTION_LENGTH = 2000
MAX_DEPRECATION_NOTE_LENGTH = 500


class Component(SQLModel, table=True):
    """The abstract node of the composite - CWL's `Process`.

    Everything a Tool and a Workflow have in common lives here: identity, the name+version
    lineage, the CWL document, its ports (parameters), domains, auxiliary files and the
    publication status. What only one kind has lives in its 1:1 detail row, `tool` or
    `workflow`, exactly one of which is set (matching `kind`).

    SQLModel cannot map a table class that subclasses another table class, so the
    hierarchy is expressed as composition plus the `kind` discriminator rather than as
    Python inheritance.
    """

    __tablename__ = "components"
    # fetch the server-generated timestamps via RETURNING on flush - otherwise they stay
    # expired and reading one would lazy-load, which an AsyncSession cannot do
    __mapper_args__ = {"eager_defaults": True}
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
    # explicit String column, same convention as source/status - never a native PG enum
    kind: ComponentKind = Field(sa_column=Column(String, nullable=False))
    # the lineage key: every version of a component shares it, and it is unique across
    # both kinds, so a lineage never mixes tools and workflows
    name: str
    author_name: str | None = None
    created_by_id: uuid.UUID | None = Field(default=None, sa_column=Column(ForeignKey("users.id"), nullable=True))
    description: str | None = Field(default=None, sa_column=Column(String(MAX_DESCRIPTION_LENGTH), nullable=True))
    repo_url: str | None = None
    repo_commit_sha: str | None = None
    doi: str | None = None
    version: int = 1
    # the raw CWL document - a CommandLineTool/ExpressionTool for a tool, the pipeline
    # (class: Workflow) for a workflow
    cwl_content: str = Field(sa_column=Column(Text, nullable=False))
    # derived from cwl_content: the ontology its parameters' `format`s belong to - the
    # `$schemas` URL, normalized so every EDAM release maps to one configured ontology
    # (see format_service.ontology.resolve_ontology_url). Two ports are only comparable via
    # the format service when both components share it; None when the CWL declares no $schemas.
    ontology_url: str | None = None
    # explicit String column: SQLModel would otherwise infer a native Postgres
    # enum type from the Python Enum
    source: ComponentSource = Field(default=ComponentSource.MANUAL_UPLOAD, sa_column=Column(String, nullable=False))
    # Per *version row*, not per lineage: only PUBLISHED rows are listed and only PUBLISHED or
    # DEPRECATED ones are publicly visible (see composite.lifecycle), so a still-draft or
    # deprecated v2 never hides an already-published v1 from the browse list.
    status: ComponentStatus = Field(default=ComponentStatus.DRAFT, sa_column=Column(String, nullable=False))
    #: why the version is deprecated, npm-style - set only while it is DEPRECATED
    deprecation_note: str | None = Field(
        default=None, sa_column=Column(String(MAX_DEPRECATION_NOTE_LENGTH), nullable=True)
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    # lazy="selectin": default lazy loading isn't safe with AsyncSession (attribute
    # access outside an awaited context raises MissingGreenlet) - selectin issues a
    # proper follow-up SELECT as part of the same async flow instead.
    created_by: Optional["User"] = Relationship(back_populates="components", sa_relationship_kwargs={"lazy": "selectin"})
    # cascade + passive_deletes, like domains/files below: without them, deleting a component
    # made SQLAlchemy NULL out every parameter's component_id before the DELETE, so the
    # database's ON DELETE CASCADE had nothing left to cascade and the rows were orphaned
    parameters: list["Parameter"] = Relationship(
        back_populates="component",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True},
    )
    domains: list["ComponentDomain"] = Relationship(
        back_populates="component",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True},
    )
    files: list["ComponentFile"] = Relationship(
        back_populates="component",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True},
    )
    # the kind-specific parts - one-to-one, so uselist=False
    tool: Optional["Tool"] = Relationship(
        back_populates="component",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "uselist": False,
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    workflow: Optional["Workflow"] = Relationship(
        back_populates="component",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "uselist": False,
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    @property
    def is_tool(self) -> bool:
        return self.kind == ComponentKind.TOOL

    @property
    def is_workflow(self) -> bool:
        return self.kind == ComponentKind.WORKFLOW

    @property
    def steps(self) -> list["WorkflowStep"]:
        """A workflow's steps in order - always [] for a tool, the leaf of the composite."""
        return self.workflow.steps if self.workflow is not None else []

    @property
    def children(self) -> list["Component"]:
        """The components this one is composed of - one per bound step, in step order."""
        return [step.component for step in self.steps if step.component is not None]
