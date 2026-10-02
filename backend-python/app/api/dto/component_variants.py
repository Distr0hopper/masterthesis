"""The polymorphic shapes an endpoint returns when it serves both kinds - each a union of
the kind-specific variants, told apart by their `kind` field."""

from typing import Annotated

from pydantic import Field

from app.api.dto.tool import ToolDetailDto, ToolListItemDto
from app.api.dto.workflow import WorkflowDetailDto, WorkflowListItemDto

ComponentListItemDto = Annotated[ToolListItemDto | WorkflowListItemDto, Field(discriminator="kind")]
ComponentDetailDto = Annotated[ToolDetailDto | WorkflowDetailDto, Field(discriminator="kind")]
