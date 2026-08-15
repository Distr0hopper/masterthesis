import uuid
from difflib import SequenceMatcher

# below this similarity ratio, a step is left unmatched rather than suggested - 0.6 is
# difflib's own commonly-cited "close match" threshold
MATCH_THRESHOLD = 0.6


def normalize_name(value: str) -> str:
    """Strips a .cwl extension, lowercases, and collapses separators so
    'remove-outliers.cwl' and 'Remove_Outliers' compare equal."""
    stem = value[:-4] if value.lower().endswith(".cwl") else value
    normalized = stem.lower().strip()
    for sep in ("_", " "):
        normalized = normalized.replace(sep, "-")
    return normalized


def best_match(
    run_reference: str, candidates: list[tuple[uuid.UUID, str]]
) -> tuple[uuid.UUID, str, float] | None:
    """candidates: (component_id, component_name) pairs, typically the latest version per
    lineage of every existing Component. Returns (component_id, component_name, score) for
    the highest-scoring candidate at or above MATCH_THRESHOLD, or None if none qualify."""
    target = normalize_name(run_reference)
    best: tuple[uuid.UUID, str, float] | None = None
    for component_id, component_name in candidates:
        score = SequenceMatcher(None, target, normalize_name(component_name)).ratio()
        if score >= MATCH_THRESHOLD and (best is None or score > best[2]):
            best = (component_id, component_name, score)
    return best
