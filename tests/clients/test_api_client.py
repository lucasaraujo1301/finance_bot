from unittest.mock import AsyncMock, Mock

import pytest

from clients.api_client import ApiClient


@pytest.mark.asyncio
class TestApiClient:
    def make_service(self, monkeypatch, api_key: str | None = None) -> ApiClient:
        if api_key is None:
            monkeypatch.delenv("API_KEY", raising=False)
        else:
            monkeypatch.setenv("API_KEY", api_key)
        return ApiClient(logger=Mock(), base_url="https://api.example.com/")

    def mock_async_client(self, monkeypatch):
        client = Mock()
        client.post = AsyncMock(return_value=Mock(name="post_response"))
        client.patch = AsyncMock(return_value=Mock(name="patch_response"))
        client.get = AsyncMock(return_value=Mock(name="get_response"))
        client.delete = AsyncMock(return_value=Mock(name="delete_response"))

        async_client = Mock()
        async_client.return_value.__aenter__ = AsyncMock(return_value=client)
        async_client.return_value.__aexit__ = AsyncMock(return_value=None)

        monkeypatch.setattr("clients.api_client.httpx.AsyncClient", async_client)
        return async_client, client

    async def test_get_url_normalizes_slashes(self, monkeypatch):
        service = self.make_service(monkeypatch)

        assert service._get_url("/users/") == "https://api.example.com/v1/users/"

    async def test_get_headers_returns_json_headers_without_api_key(self, monkeypatch):
        service = self.make_service(monkeypatch)

        assert service._get_headers() == {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def test_get_headers_adds_api_key_from_environment(self, monkeypatch):
        service = self.make_service(monkeypatch, api_key="secret-key")

        assert service._get_headers() == {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": "secret-key",
        }

    async def test_get_headers_adds_accept_language(self, monkeypatch):
        service = self.make_service(monkeypatch)

        assert service._get_headers("pt-BR") == {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "pt-BR",
        }

    async def test_post_sends_json_payload(self, monkeypatch):
        service = self.make_service(monkeypatch, api_key="secret-key")
        async_client, client = self.mock_async_client(monkeypatch)
        payload = {"name": "Lucas"}

        response = await service.post(data=payload, url="users", language_code="pt-BR")

        async_client.assert_called_once_with(timeout=10)
        client.post.assert_awaited_once_with(
            url="https://api.example.com/v1/users/",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-KEY": "secret-key",
                "Accept-Language": "pt-BR",
            },
        )
        assert response == client.post.return_value

    async def test_patch_sends_json_payload(self, monkeypatch):
        service = self.make_service(monkeypatch)
        _, client = self.mock_async_client(monkeypatch)
        payload = {"name": "Lucas"}

        response = await service.patch(data=payload, url="users/123")

        client.patch.assert_awaited_once_with(
            url="https://api.example.com/v1/users/123/",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        assert response == client.patch.return_value

    async def test_get_sends_headers(self, monkeypatch):
        service = self.make_service(monkeypatch, api_key="secret-key")
        _, client = self.mock_async_client(monkeypatch)

        response = await service.get(url="users")

        client.get.assert_awaited_once_with(
            url="https://api.example.com/v1/users/",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-API-KEY": "secret-key",
            },
        )
        assert response == client.get.return_value

    async def test_delete_sends_headers(self, monkeypatch):
        service = self.make_service(monkeypatch)
        _, client = self.mock_async_client(monkeypatch)

        response = await service.delete(url="users/123")

        client.delete.assert_awaited_once_with(
            url="https://api.example.com/v1/users/123/",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        assert response == client.delete.return_value
