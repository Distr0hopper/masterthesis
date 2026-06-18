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
    rfunction: RepoFile
    app_config: RepoFile


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

        appspec_file = self._fetch_file(owner, repo, "appspec.json")
        appspec = json.loads(appspec_file.content)

        if "settings" not in appspec:
            raise ValueError(
                f"appspec.json in {owner}/{repo} has no 'settings' key. "
                "Is this a valid MoveApps R app repository?"
            )

        rfunction = self._fetch_file(owner, repo, "RFunction.R")
        app_config = self._fetch_file(owner, repo, "app-configuration.json")

        return RepoContents(
            appspec=appspec,
            rfunction=rfunction,
            app_config=app_config,
        )
