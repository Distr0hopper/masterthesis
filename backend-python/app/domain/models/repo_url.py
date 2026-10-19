"""A repository URL as the catalogue keys it. A packaged tool's lineage is found by the repo
it came from, so the same repo spelled differently - a trailing slash, a `.git` suffix, a
copied `?tab=readme` - must never start a second lineage."""

import re
from urllib.parse import urlparse, urlunparse

#: what may trail a repo path without making it another repo - mirrored in SQL by
#: ComponentsRepository.find_tool_by_repo_url, for rows stored before URLs were canonical
REPO_URL_SUFFIX_PATTERN = r"(\.git)?/*$"


def canonical_repo_url(url: str) -> str:
    """`url` without query, fragment, `.git` suffix and trailing slashes, scheme and host
    lowercased. The path keeps its case for display - compare via repo_url_key."""
    parsed = urlparse(url.strip())
    path = re.sub(REPO_URL_SUFFIX_PATTERN, "", parsed.path)
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def repo_url_key(url: str) -> str:
    """What two URLs of the same repo share - GitHub ignores the case of owner and repo."""
    return canonical_repo_url(url).lower()
