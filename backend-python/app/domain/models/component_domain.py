import json
from pathlib import Path

_DOMAINS_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "domains.json"

_RAW_DOMAINS: list[dict[str, str]] = json.loads(_DOMAINS_CONFIG_PATH.read_text())

VALID_DOMAINS: list[str] = [d["id"] for d in _RAW_DOMAINS]
DOMAIN_COLORS: dict[str, str] = {d["id"]: d["color"] for d in _RAW_DOMAINS}
