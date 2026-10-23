"""Reading a MoveApps repo through the GitHub REST API - faked here, one canned response
per URL - without cloning it."""

import base64
import json

import pytest
import requests

from moveapps_cwl_packager.github import GitHubClient, extract_readme_description

API = "https://api.github.com"
REPO = f"{API}/repos/movestore/RemoveOutliers"
README = b"# Remove Outliers\n\n## Description\nDrops fixes faster than a bird can fly.\n\n## Settings\n..."


def _file(content: bytes) -> dict:
    return {"content": base64.b64encode(content).decode()}


def _responses(**overrides: object) -> dict[str, object]:
    responses: dict[str, object] = {
        REPO: {"default_branch": "master"},
        f"{REPO}/contents/appspec.json": _file(json.dumps({"settings": [{"id": "maxspeed"}]}).encode()),
        f"{REPO}/contents/app-configuration.json": _file(b'{"maxspeed": 20}'),
        f"{REPO}/contents/README.md": _file(README),
        f"{API}/users/movestore": {"name": "MoveApps Team"},
        f"{REPO}/branches/master": {"commit": {"sha": "abc123"}},
    }
    responses.update(overrides)
    return responses


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch):
    """Serve `responses` instead of GitHub: a dict is a 200 JSON body, an int an error
    status, a missing URL a 404."""
    responses: dict[str, object] = {}
    seen_headers: list[dict] = []

    def get(self: requests.Session, url: str, timeout: float) -> requests.Response:
        seen_headers.append(dict(self.headers))
        body = responses.get(url, 404)
        response = requests.Response()
        response.url = url
        response.request = requests.Request("GET", url).prepare()
        if isinstance(body, int):
            response.status_code = body
            response._content = b"{}"
        else:
            response.status_code = 200
            response._content = json.dumps(body).encode()
        return response

    monkeypatch.setattr(requests.Session, "get", get)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    return responses, seen_headers


def test_a_repo_is_read_with_its_commit_description_and_author(github) -> None:
    responses, _ = github
    responses.update(_responses())

    contents = GitHubClient().fetch_repo("movestore", "RemoveOutliers")

    assert contents.appspec == {"settings": [{"id": "maxspeed"}]}
    assert contents.app_config.content == b'{"maxspeed": 20}'
    assert (contents.default_branch, contents.commit_sha) == ("master", "abc123")
    assert contents.description == "Drops fixes faster than a bird can fly."
    assert contents.author == "MoveApps Team"


def test_a_missing_readme_or_owner_profile_only_loses_the_extras(github) -> None:
    responses, _ = github
    responses.update(_responses(**{f"{REPO}/contents/README.md": 404, f"{API}/users/movestore": 500}))

    contents = GitHubClient().fetch_repo("movestore", "RemoveOutliers")

    assert (contents.description, contents.author) == ("", "movestore")


def test_a_repo_without_appspec_settings_is_no_moveapps_app(github) -> None:
    responses, _ = github
    responses.update(_responses(**{f"{REPO}/contents/appspec.json": _file(b'{"name": "x"}')}))

    with pytest.raises(ValueError, match="no 'settings' key"):
        GitHubClient().fetch_repo("movestore", "RemoveOutliers")


def test_a_missing_required_file_or_repo_raises_the_http_error(github) -> None:
    responses, _ = github
    responses.update(_responses(**{f"{REPO}/contents/app-configuration.json": 404}))
    with pytest.raises(requests.HTTPError):
        GitHubClient().fetch_repo("movestore", "RemoveOutliers")

    responses.clear()
    with pytest.raises(requests.HTTPError):
        GitHubClient().fetch_repo("movestore", "RemoveOutliers")


def test_a_token_is_sent_only_when_there_is_one(github, monkeypatch: pytest.MonkeyPatch) -> None:
    responses, seen_headers = github
    responses.update(_responses())

    GitHubClient().fetch_repo("movestore", "RemoveOutliers")
    assert "Authorization" not in seen_headers[-1]

    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    GitHubClient().fetch_repo("movestore", "RemoveOutliers")
    assert seen_headers[-1]["Authorization"] == "Bearer secret"


def test_the_readme_description_is_the_section_up_to_the_next_heading() -> None:
    assert extract_readme_description(README) == "Drops fixes faster than a bird can fly."
    assert extract_readme_description(b"## description\nlower case heading") == "lower case heading"
    assert extract_readme_description(b"# Just a title") == ""
