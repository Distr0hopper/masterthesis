"""One repo, one key - however its URL was pasted."""

import pytest

from app.domain.models.repo_url import canonical_repo_url, repo_url_key

CANONICAL = "https://github.com/Distr0hopper/RemoveOutliers"


@pytest.mark.parametrize(
    "pasted",
    [
        CANONICAL,
        f"{CANONICAL}/",
        f"{CANONICAL}//",
        f"{CANONICAL}.git",
        f"{CANONICAL}.git/",
        f"  {CANONICAL}  ",
        f"{CANONICAL}?tab=readme-ov-file",
        f"{CANONICAL}#readme",
        "HTTPS://GitHub.com/Distr0hopper/RemoveOutliers/",
    ],
)
def test_spellings_of_the_same_repo_are_made_canonical(pasted: str) -> None:
    assert canonical_repo_url(pasted) == CANONICAL


def test_owner_and_repo_case_only_matter_for_display() -> None:
    assert canonical_repo_url("https://github.com/distr0hopper/removeoutliers") != CANONICAL
    assert repo_url_key("https://github.com/distr0hopper/removeoutliers") == repo_url_key(CANONICAL)


def test_another_repo_stays_another_repo() -> None:
    assert repo_url_key(f"{CANONICAL}-fork") != repo_url_key(CANONICAL)
