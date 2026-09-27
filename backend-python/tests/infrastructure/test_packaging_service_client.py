import asyncio

import httpx
import pytest

from app.application.exception.component_exceptions import PackagingFailedError, PackagingServiceUnavailableError
from app.infrastructure.packaging.packaging_service_client import PackagingServiceClient

REPO_URL = "https://github.com/movestore/RemoveOutliers.git"


def _client(handler) -> PackagingServiceClient:
    return PackagingServiceClient("http://packaging/api/v1/", timeout=5, transport=httpx.MockTransport(handler))


def test_package_maps_response_to_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://packaging/api/v1/package"
        return httpx.Response(
            200,
            json={
                "repoName": "RemoveOutliers",
                "cwl": "cwlVersion: v1.2",
                "inputsYaml": "maxspeed: 20.0",
                "commitSha": "abc123",
                "description": "Removes outliers",
                "author": "MoveApps",
            },
        )

    result = asyncio.run(_client(handler).package(REPO_URL))

    assert result.repo_name == "RemoveOutliers"
    assert result.commit_sha == "abc123"
    assert result.cwl == "cwlVersion: v1.2"


def test_rejection_raises_packaging_failed_with_service_detail():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "movestore/RemoveOutliers is not a valid MoveApps R app"})

    with pytest.raises(PackagingFailedError, match="Packaging 'RemoveOutliers' failed: .*not a valid MoveApps R app"):
        asyncio.run(_client(handler).package(REPO_URL))


def test_non_json_error_falls_back_to_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    with pytest.raises(PackagingFailedError, match="500 Internal Server Error"):
        asyncio.run(_client(handler).package(REPO_URL))


def test_unreachable_service_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(PackagingServiceUnavailableError):
        asyncio.run(_client(handler).package(REPO_URL))
