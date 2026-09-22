"""
Every SQLModel table class must be imported here so relationship() string
references (e.g. Relationship(back_populates=...)) can always resolve,
regardless of which model happens to be imported first at runtime.

SQLAlchemy creates a Mapping-Registry with those imports, which is needed
because TYPE_CHECKING is false at runtime, so the imports are necessary to
register the tables with SQLModel.metadata before the relatinships are dissolved.
"""

from app.domain.models.component import Component  # noqa: F401
from app.domain.models.component_domain import ComponentDomain  # noqa: F401
from app.domain.models.component_file import ComponentFile  # noqa: F401
from app.domain.models.workflow_file import WorkflowFile  # noqa: F401
from app.domain.models.parameter import Parameter  # noqa: F401
from app.domain.models.user import User  # noqa: F401