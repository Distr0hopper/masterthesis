"""Core packaging logic - shared by the CLI and the HTTP service."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests

from .generators import (
    generate_cwl,
    generate_dockerfile_content,
    generate_inputs_yaml,
)
from .github import GitHubClient

DEFAULT_WRAPPER_IMAGE = "moveapps-r-wrapper:latest"


class PackagingError(Exception):
    """Base class for every expected packaging failure."""


class InvalidRepoUrlError(PackagingError):
    """The URL is not a GitHub repository URL."""


class NotAMoveAppsRepoError(PackagingError):
    """The repository doesn't exist or isn't a valid MoveApps R app."""


class GitHubUnavailableError(PackagingError):
    """GitHub couldn't be reached or refused the request (e.g. rate limit)."""


@dataclass
class PackageResult:
    repo_name: str
    cwl: str
    inputs_yaml: str
    commit_sha: str
    description: str
    author: str
    # appspec settings - the detected CWL input parameters (for the CLI summary)
    settings: list[dict]


def parse_github_url(url: str) -> tuple[str, str]:
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip()
    )
    if not m:
        raise InvalidRepoUrlError(
            f"Not a valid GitHub repository URL: {url!r} "
            "(expected format: https://github.com/<owner>/<repo>)"
        )
    return m.group(1), m.group(2)


def repo_name_to_image(repo_name: str) -> str:
    return repo_name.lower().replace("_", "-")


def package_repo(
    repo_url: str,
    wrapper_image: str = DEFAULT_WRAPPER_IMAGE,
    github_token: str | None = None,
) -> PackageResult:
    owner, repo_name = parse_github_url(repo_url)

    client = GitHubClient(token=github_token)
    try:
        contents = client.fetch_repo(owner, repo_name)
        app_config_dict = json.loads(contents.app_config.content)
        r_packages = [d["name"] for d in contents.appspec.get("dependencies", {}).get("R", [])]
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise NotAMoveAppsRepoError(
                f"{owner}/{repo_name} not found or missing a required MoveApps file ({exc.request.url})"
            ) from exc
        raise GitHubUnavailableError(f"GitHub request failed: {exc}") from exc
    except requests.RequestException as exc:
        raise GitHubUnavailableError(f"GitHub could not be reached: {exc}") from exc
    except (ValueError, KeyError) as exc:
        # json.JSONDecodeError is a ValueError, as is the missing-'settings' check in fetch_repo
        raise NotAMoveAppsRepoError(f"{owner}/{repo_name} is not a valid MoveApps R app: {exc}") from exc

    appspec_settings = contents.appspec.get("settings", [])
    raw_base_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{contents.default_branch}"

    dockerfile_content = generate_dockerfile_content(wrapper_image, raw_base_url, r_packages or None)
    cwl_text = generate_cwl(repo_name_to_image(repo_name), appspec_settings, dockerfile_content)
    inputs_yaml = generate_inputs_yaml(appspec_settings, app_config_dict)

    return PackageResult(
        repo_name=repo_name,
        cwl=cwl_text,
        inputs_yaml=inputs_yaml,
        commit_sha=contents.commit_sha,
        description=contents.description,
        author=contents.author,
        settings=appspec_settings,
    )
