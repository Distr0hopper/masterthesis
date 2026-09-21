import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.component import Component

_DOMAINS_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "domains.json"

_RAW_DOMAINS: list[dict[str, str]] = json.loads(_DOMAINS_CONFIG_PATH.read_text())

VALID_DOMAINS: list[str] = [d["id"] for d in _RAW_DOMAINS]
DOMAIN_COLORS: dict[str, str] = {d["id"]: d["color"] for d in _RAW_DOMAINS}


class ComponentDomain(SQLModel, table=True):
    """One of a component's domains - the exact shape of WorkflowDomain."""

    __tablename__ = "component_domains"

    component_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("components.id", ondelete="CASCADE"), primary_key=True)
    )
    # validated against VALID_DOMAINS at the DTO boundary, not a DB-backed FK - domains
    # are static JSON config (above), not a real table
    domain: str = Field(primary_key=True)

    component: "Component" = Relationship(back_populates="domains", sa_relationship_kwargs={"lazy": "selectin"})
