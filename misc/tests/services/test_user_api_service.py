from unittest.mock import Mock

import httpx
import pytest

from misc.dataclass import UserApiKeyRecord
from misc.exceptions import CreateRemoteUserError


@pytest.mark.asyncio
class TestUserService:
    async def test_get_user_by_telegram_id_returns_repository_user(self, user_service_dependencies):
        user = UserApiKeyRecord(telegram_id=123, api_key="encrypted-key", created_at="2026-07-13")
        user_service_dependencies.repository.get_user_by_telegram_id.return_value = user

        result = user_service_dependencies.service.get_user_by_telegram_id(123)

        user_service_dependencies.repository.get_user_by_telegram_id.assert_called_once_with(123)
        assert result == user

    async def test_create_user_posts_to_api_and_saves_encrypted_api_key(
        self, user_service_dependencies, telegram_user
    ):
        response = Mock()
        response.status_code = 201
        response.json.return_value = {"api_key": "raw-api-key"}
        user_service_dependencies.client.post.return_value = response

        await user_service_dependencies.service.create_user(telegram_user)

        user_service_dependencies.client.post.assert_awaited_once_with(
            {
                "full_name": "Lucas Araujo",
                "telegram_id": "123",
            },
            "/users",
        )
        user_service_dependencies.cryptography.encrypt.assert_called_once_with(b"raw-api-key")
        user_service_dependencies.repository.add_user.assert_called_once_with(
            telegram_user.id,
            api_key=b"encrypted-api-key".hex(),
        )

    async def test_create_user_raises_when_api_does_not_return_created(
        self, user_service_dependencies, telegram_user
    ):
        response = Mock()
        response.status_code = 500
        response.content = b"server error"
        user_service_dependencies.client.post.return_value = response

        with pytest.raises(CreateRemoteUserError):
            await user_service_dependencies.service.create_user(telegram_user)

        user_service_dependencies.repository.add_user.assert_not_called()
        user_service_dependencies.logger.error.assert_called_once_with(
            "Failed to create user in API. status=%s\n body=%s",
            500,
            b"server error",
        )

    async def test_create_user_raises_when_api_request_fails(self, user_service_dependencies, telegram_user):
        error = httpx.ConnectError("All connection attempts failed")
        user_service_dependencies.client.post.side_effect = error

        with pytest.raises(CreateRemoteUserError):
            await user_service_dependencies.service.create_user(telegram_user)

        user_service_dependencies.repository.add_user.assert_not_called()
        user_service_dependencies.logger.error.assert_called_once_with(
            "Failed to connect to user API. error=%s",
            error,
        )

    async def test_create_user_raises_when_api_key_is_missing(self, user_service_dependencies, telegram_user):
        response = Mock()
        response.status_code = 201
        response.text = '{"id": 1}'
        response.json.return_value = {"id": 1}
        user_service_dependencies.client.post.return_value = response

        with pytest.raises(CreateRemoteUserError):
            await user_service_dependencies.service.create_user(telegram_user)

        user_service_dependencies.repository.add_user.assert_not_called()
        user_service_dependencies.logger.error.assert_called_once_with(
            "API created user without api_key. body=%s",
            response.text,
        )

    async def test_create_user_raises_when_api_response_is_not_valid_json(
        self, user_service_dependencies, telegram_user
    ):
        response = Mock()
        response.status_code = 201
        response.text = "not-json"
        response.json.side_effect = ValueError("Invalid JSON")
        user_service_dependencies.client.post.return_value = response

        with pytest.raises(CreateRemoteUserError):
            await user_service_dependencies.service.create_user(telegram_user)

        user_service_dependencies.repository.add_user.assert_not_called()
        user_service_dependencies.logger.error.assert_called_once_with(
            "API created user without api_key. body=%s",
            response.text,
        )
