"""Request bodies of the SOS File Format Service endpoints this backend calls.

Plain BaseModel, not the API's CamelModel: the service expects snake_case field names.
"""

from pydantic import BaseModel


class FormatInfoRequest(BaseModel):
    """POST /format-info - a format's metadata; only its `label` is read back."""

    #: the expanded format IRI, e.g. https://dfg-sos.github.io/ontologies/eo-formats#GeoTIFF
    format_identifier: str
    #: the ontology the service loads and looks it up in - Component.ontology_url
    ontology_schema_url: str


class CompatibilityRequest(BaseModel):
    """POST /compatibility - whether `actual_format` is the same class as, or a subclass
    or equivalent of, `expected_format`; only `compatible` is read back."""

    #: what the input port expects
    expected_format: str
    #: what the output port feeding it produces
    actual_format: str
    #: the ontology both ports' components share - Component.ontology_url
    ontology_schema_url: str
