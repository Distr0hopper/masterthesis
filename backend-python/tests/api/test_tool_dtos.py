"""A repo URL is made canonical where it enters - every later lookup and the stored value
depend on it, so the same repo pasted differently never starts a second tool."""

import pytest

from app.api.dto.tool import PackagePreviewRequestDto, PackageToolRequestDto

CANONICAL = "https://github.com/Distr0hopper/RemoveOutliers"


@pytest.mark.parametrize("pasted", [f"{CANONICAL}/", f"{CANONICAL}.git", f" {CANONICAL}?tab=readme-ov-file "])
def test_the_package_dtos_make_the_repo_url_canonical(pasted: str) -> None:
    assert PackagePreviewRequestDto(repo_url=pasted).repo_url == CANONICAL
    assert PackageToolRequestDto(repo_url=pasted, domains=["other"]).repo_url == CANONICAL


def test_a_repo_url_that_isnt_a_url_is_refused() -> None:
    with pytest.raises(ValueError, match="valid URL"):
        PackagePreviewRequestDto(repo_url="github.com/no-scheme")
