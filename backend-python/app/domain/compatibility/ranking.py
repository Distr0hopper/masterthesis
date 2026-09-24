import uuid
from dataclasses import dataclass

from app.domain.compatibility.port import FormatLookup, Port, data_inputs, no_lookup
from app.domain.compatibility.port_check import ConnectionStatus, check_ports

#: score for a candidate that has no data inputs at all - sorts below "no match"
NO_DATA_INPUTS_SCORE = -1


@dataclass(frozen=True)
class OutputFrame:
    """One canvas node's data outputs. Frames are ordered most-recently-added first."""

    component_id: uuid.UUID
    component_name: str
    outputs: list[Port]


@dataclass(frozen=True)
class Match:
    score: int
    #: the frame that produced the score, or None when nothing matched
    frame: OutputFrame | None = None
    #: COMPATIBLE or UNVERIFIED for the frame's best pair - None when nothing matched
    status: ConnectionStatus | None = None


def match_component(candidate: list[Port], frames: list[OutputFrame], lookup: FormatLookup = no_lookup) -> Match:
    """Rank one candidate against the canvas. Higher is better; the most recent frame that
    matches wins. Within a frame a format-checked match outranks an unverified one, so the
    top frame scores `2 * len(frames)` (verified) or one less, and the oldest 2 or 1."""
    # nothing on the canvas yet -> everything ranks equally, the list stays alphabetical
    if not frames:
        return Match(score=0)

    inputs = data_inputs(candidate)
    if not inputs:
        return Match(score=NO_DATA_INPUTS_SCORE)

    for i, frame in enumerate(frames):
        statuses = {check_ports(out, inp, lookup).status for out in frame.outputs for inp in inputs}
        frame_score = 2 * (len(frames) - i)
        if ConnectionStatus.COMPATIBLE in statuses:
            return Match(score=frame_score, frame=frame, status=ConnectionStatus.COMPATIBLE)
        if ConnectionStatus.UNVERIFIED in statuses:
            return Match(score=frame_score - 1, frame=frame, status=ConnectionStatus.UNVERIFIED)

    return Match(score=0)


def rank_key(match: Match, is_favorite: bool, name: str) -> tuple[int, int, str]:
    """Palette order: compatibility score first, then favourites, then name.

    Favourites only break a tie *within* a score bucket - a favourite must never outrank a
    component that fits the canvas better, or the ranking stops meaning anything."""
    return (-match.score, 0 if is_favorite else 1, name.lower())
