from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

__all__ = ["load_cwl", "YAMLError"]


def load_cwl(content: str) -> Any:
    """Parse CWL/YAML text into plain Python data (dict/list/scalars).

    Uses ruamel.yaml rather than PyYAML: CWL v1.2 permits constructs PyYAML's parser
    rejects outright, notably the optional-marker ``?`` inside an unquoted flow sequence
    (``secondaryFiles: [^.shx, ^.dbf, ^.cpg?, ^.qpj?]``). ruamel is also what the CWL
    reference tooling (cwltool / schema-salad) parses with.

    Raises ``YAMLError`` on malformed input, matching the exception the callers catch.
    """
    # a fresh instance per call - a YAML() object is not meant to be shared across
    # concurrent loads, and uploads are nowhere near a hot path
    yaml = YAML(typ="safe")
    return yaml.load(content)
