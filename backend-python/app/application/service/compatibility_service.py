import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.application.service.components_service import ComponentsService
from app.application.unit_of_work import UnitOfWork
from app.domain.compatibility.port import FormatPair, Port, data_inputs, data_outputs
from app.domain.compatibility.port_check import PortCheck, check_ports, format_pair_for, format_pairs_between
from app.domain.compatibility.ranking import Match, OutputFrame, match_component, rank_key
from app.domain.models.component import Component
from app.domain.models.user import User
from app.domain.pagination.pagination import PaginatedList
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.format_service.format_service_client import FormatServiceClient

#: (actual_format, expected_format, ontology_url) -> answer. Process-wide on purpose: a
#: format's place in an ontology doesn't change, so an answer is valid for every request.
#: Only definite answers are stored - a None (service down) must be retried next time.
_cache: dict[tuple[str, str, str], bool] = {}


@dataclass(frozen=True)
class Connection:
    """A builder edge: `source_port` (an output) of one component feeding `target_port` (an input) of another."""

    source_component_id: uuid.UUID
    source_port: str
    target_component_id: uuid.UUID
    target_port: str


@dataclass
class RankedComponent:
    component: Component
    match: Match


class CompatibilityService:
    """The workflow builder's type checking: which connections are valid, and how the
    palette ranks against the canvas. The rules themselves live in
    app.domain.compatibility; this service loads the ports and answers the format
    questions (via the SOS File Format Service) those rules ask."""

    def __init__(self, uow: UnitOfWork, format_service_client: FormatServiceClient):
        self.uow = uow
        self.format_service_client = format_service_client

    @staticmethod
    def get_service(
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
        format_service_client: Annotated[FormatServiceClient, Depends(FormatServiceClient.get_client)],
    ) -> "CompatibilityService":
        return CompatibilityService(uow, format_service_client)

    async def check_connections(self, connections: list[Connection], current_user: User | None) -> list[PortCheck]:
        components = await self._visible_components_by_id(
            [c.source_component_id for c in connections] + [c.target_component_id for c in connections],
            current_user,
        )
        resolved = [self._ports_for(connection, components) for connection in connections]
        answers = await self._answer(self._questions_for(resolved))
        return [ports if isinstance(ports, PortCheck) else check_ports(*ports, answers.get) for ports in resolved]

    async def rank_components(
        self,
        candidates: list[Component],
        rank_against: list[uuid.UUID],
        favorited_names: set[str],
        current_user: User | None,
        pagination: PaginatedList,
    ) -> tuple[list[RankedComponent], int]:
        """One page of `candidates`, ranked against the canvas.

        `rank_against` is the component of every canvas node, most recently added first;
        each becomes an output frame. Every candidate is scored before paging - ranking
        only the page at hand would let a good match on a later page never surface. That
        loads the whole filtered set per request: fine at this repository's size, and the
        format questions stay few (bounded by the distinct formats, and cached).
        """
        frames = self._frames_for(rank_against, await self._visible_components_by_id(rank_against, current_user))
        candidate_ports = {c.id: self._ports(c) for c in candidates}
        answers = await self._answer(self._ranking_questions_for(candidate_ports.values(), frames))
        ranked = sorted(
            (RankedComponent(c, match_component(candidate_ports[c.id], frames, answers.get)) for c in candidates),
            key=lambda r: rank_key(r.match, r.component.name in favorited_names, r.component.name),
        )
        return ranked[pagination.offset : pagination.offset + pagination.limit], len(ranked)

    async def _visible_components_by_id(
        self, ids: list[uuid.UUID], current_user: User | None
    ) -> dict[uuid.UUID, Component]:
        components = await self.uow.components.find_by_ids(list(dict.fromkeys(ids)))
        return {c.id: c for c in components if ComponentsService.is_visible(c, current_user)}

    @staticmethod
    def _ports(component: Component) -> list[Port]:
        return [Port.of(component, p) for p in component.parameters]

    def _ports_for(
        self, connection: Connection, components: dict[uuid.UUID, Component]
    ) -> tuple[Port, Port] | PortCheck:
        """The source and target port, or the incompatible verdict when either doesn't exist."""
        source_component = components.get(connection.source_component_id)
        target_component = components.get(connection.target_component_id)
        if source_component is None or target_component is None:
            return PortCheck.incompatible("Unknown component - it may have been removed.")
        source = next((p for p in self._ports(source_component) if p.name == connection.source_port), None)
        target = next((p for p in self._ports(target_component) if p.name == connection.target_port), None)
        if source is None or target is None:
            return PortCheck.incompatible("Unknown port - the component may have changed.")
        return source, target

    def _frames_for(self, rank_against: list[uuid.UUID], components: dict[uuid.UUID, Component]) -> list[OutputFrame]:
        """One output frame per canvas component, in `rank_against` order (newest first).

        Components that are gone or not visible are skipped, and so are ones without data
        outputs - they have nothing a candidate could connect to.
        """
        frames: list[OutputFrame] = []
        for component_id in rank_against:
            component = components.get(component_id)
            if component is None:
                continue
            outputs = data_outputs(self._ports(component))
            if outputs:
                frames.append(OutputFrame(component_id=component.id, component_name=component.name, outputs=outputs))
        return frames

    @staticmethod
    def _ranking_questions_for(candidates: Iterable[list[Port]], frames: list[OutputFrame]) -> set[FormatPair]:
        """The format questions ranking needs: every canvas output against every candidate's
        data inputs. The set collapses the many candidates asking the same question (e.g.
        GeoTIFF -> raster) into one."""
        questions: set[FormatPair] = set()
        for ports in candidates:
            inputs = data_inputs(ports)
            for frame in frames:
                questions |= format_pairs_between(frame.outputs, inputs)
        return questions

    @staticmethod
    def _questions_for(resolved: list[tuple[Port, Port] | PortCheck]) -> set[FormatPair]:
        """The format questions these connections need the format service for.

        A connection contributes none when it is already decided (an unknown port), or when
        the rules can decide it alone - a missing format, identical formats, ... (see
        format_pair_for). The set makes connections asking the same question share it.
        """
        questions: set[FormatPair] = set()
        for ports in resolved:
            if isinstance(ports, PortCheck):
                continue
            source, target = ports
            pair = format_pair_for(source, target)
            if pair is not None:
                questions.add(pair)
        return questions

    async def _answer(self, pairs: set[FormatPair]) -> dict[FormatPair, bool]:
        """The format service's definite answers for `pairs` - unanswerable ones are absent,
        which the rules read as unverified. """

        answers: dict[FormatPair, bool] = {}
        # sequential: the format service caches a parsed ontology only once its first
        # request completes, so concurrent misses would each download it again
        for pair in sorted(pairs, key=lambda p: (p.ontology_url, p.actual_format, p.expected_format)):
            if (answer := await self._check(pair)) is not None:
                answers[pair] = answer
        return answers

    async def _check(self, pair: FormatPair) -> bool | None:
        key = (pair.actual_format, pair.expected_format, pair.ontology_url)
        if key in _cache:
            return _cache[key]
        compatible = await self.format_service_client.check_compatibility(
            expected_format=pair.expected_format, actual_format=pair.actual_format, ontology_url=pair.ontology_url
        )
        if compatible is not None:
            _cache[key] = compatible
        return compatible
