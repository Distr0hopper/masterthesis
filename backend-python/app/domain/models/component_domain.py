import json
from pathlib import Path

_DOMAINS_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "domains.json"

VALID_DOMAINS: list[str] = json.loads(_DOMAINS_CONFIG_PATH.read_text())
