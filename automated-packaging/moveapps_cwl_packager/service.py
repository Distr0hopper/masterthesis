"""HTTP service exposing the packager - run with `uvicorn moveapps_cwl_packager.service:app`."""

from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings, SettingsConfigDict

from .packager import (
    DEFAULT_WRAPPER_IMAGE,
    GitHubUnavailableError,
    InvalidRepoUrlError,
    NotAMoveAppsRepoError,
    package_repo,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    github_token: str | None = None
    wrapper_image: str = DEFAULT_WRAPPER_IMAGE


@lru_cache
def get_settings() -> Settings:
    return Settings()


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PackageRequest(CamelModel):
    repo_url: str


class PackageResponse(CamelModel):
    repo_name: str
    cwl: str
    inputs_yaml: str
    commit_sha: str
    description: str
    author: str


app = FastAPI(title="MoveApps CWL Packaging Service", version="0.1.0")


@app.exception_handler(InvalidRepoUrlError)
@app.exception_handler(NotAMoveAppsRepoError)
async def _unprocessable_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(GitHubUnavailableError)
async def _github_unavailable_handler(request: Request, exc: GitHubUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# plain `def`: package_repo does blocking requests calls, FastAPI runs it in its threadpool
@app.post("/api/v1/package", response_model=PackageResponse, response_model_by_alias=True)
def package(body: PackageRequest) -> PackageResponse:
    settings = get_settings()
    result = package_repo(body.repo_url, settings.wrapper_image, settings.github_token)
    return PackageResponse(
        repo_name=result.repo_name,
        cwl=result.cwl,
        inputs_yaml=result.inputs_yaml,
        commit_sha=result.commit_sha,
        description=result.description,
        author=result.author,
    )
