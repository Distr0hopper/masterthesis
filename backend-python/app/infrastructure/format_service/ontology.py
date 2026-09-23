from urllib.parse import urlparse

from app.config import get_settings

_EDAM_HOST = "edamontology.org"


def resolve_ontology_url(schema_url: str | None) -> str | None:
    """The ontology a CWL `$schemas` URL is resolved and compared against.

    Every EDAM URL (EDAM_1.18.owl, EDAM.owl, ...) collapses onto the one configured EDAM
    ontology: format identifiers are stable across EDAM releases, the configured fork is
    the only one carrying the EO formats (format_4100+), and compatibility can only be
    checked between two components that name the *same* ontology. Anything else passes
    through unchanged.
    """
    if schema_url is None:
        return None
    edam_url = get_settings().format_service_edam_url
    host = (urlparse(schema_url).hostname or "").lower()
    if schema_url == edam_url or host == _EDAM_HOST or host.endswith(f".{_EDAM_HOST}"):
        return edam_url
    return schema_url
