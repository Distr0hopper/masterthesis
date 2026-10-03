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
#: optional per-domain hint, surfaced next to the domain pickers. Only the values whose
#: meaning isn't obvious from the name carry one, so this is sparse by design.
DOMAIN_DESCRIPTIONS: dict[str, str] = {
    d["id"]: d["description"] for d in _RAW_DOMAINS if d.get("description")
}

#: The "works anywhere" domain. Unlike every other value it is not a subject area but a
#: statement that the item applies to all of them, so a domain filter matches it on top of
#: whatever was actually selected (see the repositories' _apply_filters). Filtering by it
#: explicitly still narrows to just these items, since it is a member of the selection.
DOMAIN_AGNOSTIC = "domain_agnostic"


class ComponentDomain(SQLModel, table=True):
    """One of a component's domains - tools and workflows alike."""

    __tablename__ = "component_domains"

    component_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("components.id", ondelete="CASCADE"), primary_key=True)
    )
    # validated against VALID_DOMAINS at the DTO boundary, not a DB-backed FK - domains
    # are static JSON config (above), not a real table
    domain: str = Field(primary_key=True)

    component: "Component" = Relationship(back_populates="domains", sa_relationship_kwargs={"lazy": "selectin"})
