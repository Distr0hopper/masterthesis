import re

#: the `$schemas` URL of the SOS EO formats ontology (github.com/dfg-sos/ontologies, served
#: on GitHub Pages) - what Component.ontology_url stores for it, and what the format
#: service fetches
EO_FORMATS_SCHEMA_URL = "https://dfg-sos.github.io/ontologies/eo-formats.owl"

#: other ways a CWL names the same ontology: its IRI (also with the namespace's `#`) ...
_EO_FORMATS_ALIASES = {
    "https://dfg-sos.github.io/ontologies/eo-formats",
    "https://dfg-sos.github.io/ontologies/eo-formats#",
    "https://dfg-sos.github.io/ontologies/eo-formats/",
}
#: ... or a pinned release, e.g. .../releases/eo-formats/1.0.0/eo-formats.owl
_EO_FORMATS_RELEASE = re.compile(r"https://dfg-sos\.github\.io/ontologies/releases/eo-formats/[^/]+/eo-formats\.owl")


def resolve_ontology_url(schema_urls: list[str]) -> str | None:
    """The ontology a CWL's `format`s belong to, picked from its `$schemas` - stored as
    Component.ontology_url and compared against.

    `$schemas` may list more than the format ontology - e.g. the SOS CWL extensions
    (cwl.owl), which define fields, not formats. So the EO formats ontology wins wherever
    it is listed; otherwise the first entry is taken. None without any `$schemas`.
    """
    resolved = [_normalize(url) for url in schema_urls]
    if EO_FORMATS_SCHEMA_URL in resolved:
        return EO_FORMATS_SCHEMA_URL
    return resolved[0] if resolved else None


def _normalize(schema_url: str) -> str:
    """Every way of naming the EO formats ontology - its schema URL, its ontology IRI, or a
    pinned release - collapses onto EO_FORMATS_SCHEMA_URL: compatibility can only be
    checked between two components that name the *same* ontology, and a release names
    the same format IRIs as the current version. Anything else passes through unchanged."""
    if schema_url in _EO_FORMATS_ALIASES or _EO_FORMATS_RELEASE.fullmatch(schema_url):
        return EO_FORMATS_SCHEMA_URL
    return schema_url
