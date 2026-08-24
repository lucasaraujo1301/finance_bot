from unittest.mock import Mock

import httpx
import pytest

from exceptions import CreateRemoteUserError


@pytest.mark.asyncio
class TestUserService:
    async def test_create_user_posts_to_api(self, user_service_dependencies, telegram_user):
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
            language_code=telegram_user.language_code,
        )

    async def test_create_user_raises_when_api_does_not_return_created(self, user_service_dependencies, telegram_user):
        response = Mock()
        response.status_code = 500
        response.content = b"server error"
        user_service_dependencies.client.post.return_value = response

        with pytest.raises(CreateRemoteUserError):
            await user_service_dependencies.service.create_user(telegram_user)

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

        user_service_dependencies.logger.error.assert_called_once_with(
            "Failed to connect to user API. error=%s",
            error,
        )
