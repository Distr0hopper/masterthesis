from dataclasses import dataclass
from enum import StrEnum

from app.domain.compatibility.port import FormatLookup, FormatPair, Port, no_lookup
from app.domain.models.parameter import ParameterDirection


class ConnectionStatus(StrEnum):
    #: the types fit, and the formats are identical or the format service said they fit
    COMPATIBLE = "compatible"
    #: the types don't fit, or the format service said the formats don't
    INCOMPATIBLE = "incompatible"
    #: the types fit but the formats couldn't be checked - allowed, but flagged. A port
    #: without a format is unknown, not "accepts anything": File -> File only *might* fit
    UNVERIFIED = "unverified"


class UnverifiedReason(StrEnum):
    MISSING_FORMATS = "missing-formats"
    MISSING_INPUT_FORMAT = "missing-input-format"
    MISSING_OUTPUT_FORMAT = "missing-output-format"
    UNKNOWN_ONTOLOGY = "unknown-ontology"
    DIFFERENT_ONTOLOGY = "different-ontology"
    NOT_CHECKED = "not-checked"


UNVERIFIED_MESSAGES: dict[UnverifiedReason, str] = {
    UnverifiedReason.MISSING_FORMATS: "Neither port declares a format, so they may or may not fit.",
    UnverifiedReason.MISSING_INPUT_FORMAT: (
        "The input declares no format, so it cannot be checked against the output's format."
    ),
    UnverifiedReason.MISSING_OUTPUT_FORMAT: (
        "The output declares no format, so it cannot be checked against the input's format."
    ),
    UnverifiedReason.UNKNOWN_ONTOLOGY: "A format is not from a known ontology ($schemas), so it cannot be checked.",
    UnverifiedReason.DIFFERENT_ONTOLOGY: (
        "The components use different ontologies ($schemas), so their formats cannot be compared."
    ),
    UnverifiedReason.NOT_CHECKED: "The format service could not check these formats.",
}


@dataclass(frozen=True)
class PortCheck:
    status: ConnectionStatus
    #: set only when status is UNVERIFIED
    reason: UnverifiedReason | None = None
    #: human-readable explanation - None for a plain compatible connection
    message: str | None = None

    @staticmethod
    def compatible() -> "PortCheck":
        return PortCheck(ConnectionStatus.COMPATIBLE)

    @staticmethod
    def incompatible(message: str) -> "PortCheck":
        return PortCheck(ConnectionStatus.INCOMPATIBLE, message=message)

    @staticmethod
    def unverified(reason: UnverifiedReason) -> "PortCheck":
        return PortCheck(ConnectionStatus.UNVERIFIED, reason=reason, message=UNVERIFIED_MESSAGES[reason])


def _normalize_cwl_type(cwl_type: str) -> str:
    """Drop the CWL optional marker and normalise case/whitespace for comparison."""
    return cwl_type.replace("?", "").strip().lower()


def cwl_types_compatible(output_type: str, input_type: str) -> bool:
    out, inp = _normalize_cwl_type(output_type), _normalize_cwl_type(input_type)
    if out == inp:
        return True
    # file[] -> file: a scatter step would fan the array out over repeated invocations.
    # TODO: counted as compatible for now; proper scatter handling is its own task.
    return out == "file[]" and inp == "file"


def structurally_compatible(source: Port, target: Port) -> bool:
    """A File output feeding a File input whose cwlTypes fit."""
    return (
        source.is_data
        and target.is_data
        and source.direction == ParameterDirection.OUTPUT
        and target.direction == ParameterDirection.INPUT
        and cwl_types_compatible(source.cwl_type, target.cwl_type)
    )


def format_pair_for(source: Port, target: Port) -> FormatPair | None:
    """The question this connection has to put to the format service, or None when it can
    be decided without one - see check_ports for the order the rules apply in."""
    if not structurally_compatible(source, target):
        return None
    if not source.format or not target.format:
        return None
    if not source.ontology_url or source.ontology_url != target.ontology_url:
        return None
    if source.format == target.format:
        return None
    return FormatPair(actual_format=source.format, expected_format=target.format, ontology_url=source.ontology_url)


def check_ports(source: Port, target: Port, lookup: FormatLookup = no_lookup) -> PortCheck:
    """Whether one concrete output port may feed one concrete input port, in order:

    1. the cwlTypes must fit (File -> File, File[] -> File, ...) - otherwise incompatible
    2. a port without a format can't be checked - unverified. Not "compatible": an untyped
       File input (e.g. one expecting .rds, which no ontology covers) does not accept anything
    3. a format outside any known ontology (no $schemas), or formats from two different
       ontologies, can't be compared - unverified
    4. identical formats - compatible
    5. otherwise the format service decides (via `lookup`) - unverified until it has
    """
    if not structurally_compatible(source, target):
        return PortCheck.incompatible(f"Incompatible types - {source.cwl_type} cannot feed {target.cwl_type}")
    if not source.format and not target.format:
        return PortCheck.unverified(UnverifiedReason.MISSING_FORMATS)
    if not target.format:
        return PortCheck.unverified(UnverifiedReason.MISSING_INPUT_FORMAT)
    if not source.format:
        return PortCheck.unverified(UnverifiedReason.MISSING_OUTPUT_FORMAT)
    if not source.ontology_url or not target.ontology_url:
        return PortCheck.unverified(UnverifiedReason.UNKNOWN_ONTOLOGY)
    if source.ontology_url != target.ontology_url:
        return PortCheck.unverified(UnverifiedReason.DIFFERENT_ONTOLOGY)
    if source.format == target.format:
        return PortCheck.compatible()

    answer = lookup(format_pair_for(source, target))  # type: ignore[arg-type] - non-None past the checks above
    if answer is None:
        return PortCheck.unverified(UnverifiedReason.NOT_CHECKED)
    if answer:
        return PortCheck.compatible()
    return PortCheck.incompatible(f"Incompatible formats - {source.display_type} cannot feed {target.display_type}")


def format_pairs_between(outputs: list[Port], inputs: list[Port]) -> set[FormatPair]:
    """Every distinct format question between any of `outputs` and any of `inputs`."""
    return {pair for out in outputs for inp in inputs if (pair := format_pair_for(out, inp)) is not None}
