import os

from logging import Logger

import httpx


class ApiClient:
    def __init__(self, logger: Logger, base_url: str):
        self.logger = logger
        self.base_url = base_url.rstrip("/")
        self.api_key = os.getenv("API_KEY")

    def _get_url(self, url: str, version: str = "v1") -> str:
        return f"{self.base_url}/{version}/{url.strip('/')}/"

    def _get_headers(self, language_code: str | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        if language_code:
            headers["Accept-Language"] = language_code

        return headers

    async def post(self, data: dict, url: str, language_code: str | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.post(
                url=self._get_url(url),
                json=data,
                headers=self._get_headers(language_code),
            )

    async def patch(self, data: dict, url: str, language_code: str | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.patch(
                url=self._get_url(url),
                json=data,
                headers=self._get_headers(language_code),
            )

    async def get(self, url: str, language_code: str | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.get(
                url=self._get_url(url),
                headers=self._get_headers(language_code),
            )

    async def delete(self, url: str, language_code: str | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.delete(
                url=self._get_url(url),
                headers=self._get_headers(language_code),
            )
