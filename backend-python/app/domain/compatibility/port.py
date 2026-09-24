from collections.abc import Callable
from dataclasses import dataclass

from app.domain.models.component import Component
from app.domain.models.parameter import Parameter, ParameterDirection


@dataclass(frozen=True)
class Port:
    """One component parameter, as far as matching cares."""

    name: str
    cwl_type: str
    direction: ParameterDirection
    #: ontology format URI (http://edamontology.org/format_4106), a bare token, or None
    format: str | None = None
    format_label: str | None = None
    #: the owning component's ontology - formats are only comparable within one
    ontology_url: str | None = None

    @staticmethod
    def of(component: Component, parameter: Parameter) -> "Port":
        return Port(
            name=parameter.name,
            cwl_type=parameter.cwl_type,
            direction=parameter.direction,
            format=parameter.format,
            format_label=parameter.format_label,
            ontology_url=component.ontology_url,
        )

    @property
    def is_data(self) -> bool:
        """File/File[] ports are data connections; scalars are configuration knobs."""
        return self.cwl_type.strip().lower().startswith("file")

    @property
    def display_type(self) -> str:
        """How the port's type reads in a message: its label, else its format, else its cwlType."""
        return self.format_label or self.format or self.cwl_type


@dataclass(frozen=True)
class FormatPair:
    """One question for the format service: may an output of `actual_format` feed an input
    of `expected_format`?"""

    actual_format: str
    expected_format: str
    ontology_url: str


#: the format service's answer for a pair - None while unknown (not asked, or it failed)
FormatLookup = Callable[[FormatPair], bool | None]


def no_lookup(_pair: FormatPair) -> bool | None:
    return None


def data_inputs(ports: list[Port]) -> list[Port]:
    return [p for p in ports if p.is_data and p.direction == ParameterDirection.INPUT]


def data_outputs(ports: list[Port]) -> list[Port]:
    return [p for p in ports if p.is_data and p.direction == ParameterDirection.OUTPUT]
