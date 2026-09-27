import logging
from dataclasses import dataclass

import httpx

from app.application.exception.component_exceptions import PackagingFailedError, PackagingServiceUnavailableError
from app.config import get_settings

logger = logging.getLogger("app.infrastructure.packaging.packaging_service_client")


@dataclass
class PackagingResult:
    repo_name: str
    cwl: str
    inputs_yaml: str
    commit_sha: str
    description: str | None
    author: str | None


class PackagingServiceClient:
    """HTTP client for the packaging service (automated-packaging, see root docker-compose.yml).

    Unlike the best-effort FormatServiceClient, packaging is the whole point of the request,
    so every failure raises: a rejection by the service (bad URL, not a MoveApps repo, GitHub
    down) becomes PackagingFailedError carrying the service's reason, an unreachable service
    becomes PackagingServiceUnavailableError.
    """

    def __init__(self, base_url: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # injectable for tests (httpx.MockTransport)
        self.transport = transport

    @staticmethod
    def get_client() -> "PackagingServiceClient":
        settings = get_settings()
        return PackagingServiceClient(settings.packaging_service_url, settings.packaging_service_timeout)

    async def package(self, repo_url: str) -> PackagingResult:
        # only used for error messages - the authoritative name comes from the service
        fallback_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
                response = await client.post(f"{self.base_url}/package", json={"repoUrl": repo_url})
        except (httpx.ConnectError, httpx.TimeoutException) as err:
            logger.error(f"Packaging service unreachable at {self.base_url}: {err!r}")
            raise PackagingServiceUnavailableError() from err

        if response.is_error:
            raise PackagingFailedError(fallback_name, self._error_reason(response))

        body = response.json()
        return PackagingResult(
            repo_name=body["repoName"],
            cwl=body["cwl"],
            inputs_yaml=body["inputsYaml"],
            commit_sha=body["commitSha"],
            description=body.get("description"),
            author=body.get("author"),
        )

    @staticmethod
    def _error_reason(response: httpx.Response) -> str:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        # FastAPI's own request-validation 422s carry a list of errors, not a string
        if isinstance(detail, str) and detail:
            return detail
        return f"packaging service responded {response.status_code} {response.reason_phrase}"
