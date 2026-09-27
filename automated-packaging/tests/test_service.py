import pytest
import requests
from fastapi.testclient import TestClient

from moveapps_cwl_packager import service
from moveapps_cwl_packager.github import GitHubClient, RepoContents, RepoFile

REPO_URL = "https://github.com/movestore/RemoveOutliers"


@pytest.fixture
def client():
    return TestClient(service.app)


def _contents() -> RepoContents:
    return RepoContents(
        appspec={"settings": [{"id": "maxspeed", "type": "DOUBLE", "defaultValue": 20.0}]},
        app_config=RepoFile(path="app-configuration.json", content=b'{"maxspeed": 20.0}'),
        default_branch="master",
        description="Removes outliers",
        author="MoveApps",
        commit_sha="abc123",
    )


def _raise(exc: Exception):
    def fetch(self, owner, repo):
        raise exc

    return fetch


def _http_error(status_code: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    response.url = f"https://api.github.com/repos/movestore/RemoveOutliers"
    return requests.HTTPError(f"{status_code} Error", response=response, request=requests.Request("GET", response.url))


def test_package_returns_cwl_and_metadata(client, monkeypatch):
    monkeypatch.setattr(GitHubClient, "fetch_repo", lambda self, owner, repo: _contents())

    response = client.post("/api/v1/package", json={"repoUrl": REPO_URL + ".git"})

    assert response.status_code == 200
    body = response.json()
    assert body["repoName"] == "RemoveOutliers"
    assert body["commitSha"] == "abc123"
    assert body["author"] == "MoveApps"
    assert "cwlVersion: v1.2" in body["cwl"]
    assert "maxspeed" in body["inputsYaml"]


def test_invalid_url_is_422(client):
    response = client.post("/api/v1/package", json={"repoUrl": "https://gitlab.com/foo/bar"})

    assert response.status_code == 422
    assert "Not a valid GitHub repository URL" in response.json()["detail"]


def test_missing_repo_is_422(client, monkeypatch):
    monkeypatch.setattr(GitHubClient, "fetch_repo", _raise(_http_error(404)))

    response = client.post("/api/v1/package", json={"repoUrl": REPO_URL})

    assert response.status_code == 422
    assert "not found" in response.json()["detail"]


def test_missing_appspec_settings_is_422(client, monkeypatch):
    monkeypatch.setattr(GitHubClient, "fetch_repo", _raise(ValueError("appspec.json has no 'settings' key")))

    response = client.post("/api/v1/package", json={"repoUrl": REPO_URL})

    assert response.status_code == 422
    assert "settings" in response.json()["detail"]


def test_rate_limit_is_502(client, monkeypatch):
    monkeypatch.setattr(GitHubClient, "fetch_repo", _raise(_http_error(403)))

    response = client.post("/api/v1/package", json={"repoUrl": REPO_URL})

    assert response.status_code == 502


def test_connection_error_is_502(client, monkeypatch):
    monkeypatch.setattr(GitHubClient, "fetch_repo", _raise(requests.ConnectionError("no route to host")))

    response = client.post("/api/v1/package", json={"repoUrl": REPO_URL})

    assert response.status_code == 502
    assert "could not be reached" in response.json()["detail"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
