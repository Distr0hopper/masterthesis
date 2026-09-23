import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("app.infrastructure.format_service.format_service_client")


class FormatServiceClient:
    """HTTP client for the SOS File Format Service (sos-file-format-service).

    Lookups are best-effort: a format label is display metadata, so an unreachable
    service or an ontology it can't load must never block creating a component - every
    failure is logged and surfaces as a missing label instead.
    """

    def __init__(self, base_url: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def get_client() -> "FormatServiceClient":
        settings = get_settings()
        return FormatServiceClient(settings.format_service_url, settings.format_service_timeout)

    async def get_format_label(self, format_identifier: str, schema_url: str) -> str | None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await self._fetch_label(client, format_identifier, schema_url)

    async def resolve_labels(self, identifiers: set[str], schema_url: str) -> dict[str, str | None]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return {
                identifier: await self._fetch_label(client, identifier, schema_url)
                for identifier in sorted(identifiers)
            }

    async def _fetch_label(self, client: httpx.AsyncClient, format_identifier: str, schema_url: str) -> str | None:
        try:
            response = await client.post(
                f"{self.base_url}/format-info",
                json={"format_identifier": format_identifier, "ontology_schema_url": schema_url},
            )
            response.raise_for_status()
            label = response.json().get("label")
        except (httpx.HTTPError, ValueError) as err:
            logger.warning("Could not resolve format label for %s (schema %s): %s", format_identifier, schema_url, err)
            return None
        return label if isinstance(label, str) else None
