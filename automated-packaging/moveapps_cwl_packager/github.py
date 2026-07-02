"""GitHub REST API client — fetches individual files without cloning."""

import base64
import os
from dataclasses import dataclass

import requests

_API_BASE = "https://api.github.com/repos"


@dataclass
class RepoFile:
    path: str
    content: bytes


@dataclass
class RepoContents:
    appspec: dict
    app_config: RepoFile
    default_branch: str


class GitHubClient:
    def __init__(self, token: str | None = None):
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/vnd.github+json"
        self._session.headers["X-GitHub-Api-Version"] = "2022-11-28"
        tok = token or os.environ.get("GITHUB_TOKEN")
        if tok:
            self._session.headers["Authorization"] = f"Bearer {tok}"

    def _fetch_file(self, owner: str, repo: str, path: str) -> RepoFile:
        url = f"{_API_BASE}/{owner}/{repo}/contents/{path}"
        resp = self._session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            raise ValueError(f"Expected a file at '{path}', got a directory listing")
        raw = base64.b64decode(data["content"])
        return RepoFile(path=path, content=raw)

    def fetch_repo(self, owner: str, repo: str) -> RepoContents:
        import json

        repo_meta = self._session.get(f"{_API_BASE}/{owner}/{repo}", timeout=30)
        repo_meta.raise_for_status()
        default_branch = repo_meta.json().get("default_branch", "main")

        appspec_file = self._fetch_file(owner, repo, "appspec.json")
        appspec = json.loads(appspec_file.content)

        if "settings" not in appspec:
            raise ValueError(
                f"appspec.json in {owner}/{repo} has no 'settings' key. "
                "Is this a valid MoveApps R app repository?"
            )

        app_config = self._fetch_file(owner, repo, "app-configuration.json")

        return RepoContents(
            appspec=appspec,
            app_config=app_config,
            default_branch=default_branch,
        )
