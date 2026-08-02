"""
Every SQLModel table class must be imported here so relationship() string
references (e.g. Relationship(back_populates=...)) can always resolve,
regardless of which model happens to be imported first at runtime.
"""

from app.domain.models.component import Component  # noqa: F401
from app.domain.models.parameter import Parameter  # noqa: F401
from app.domain.models.user import User  # noqa: F401