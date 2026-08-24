import os

from logging import Logger

import httpx

from telegram import User

from clients.api_client import ApiClient
from exceptions import CreateRemoteUserError


class UserService:
    def __init__(self, logger: Logger):
        self.logger = logger
        self._client = ApiClient(self.logger, os.getenv("API_BASE_URL", ""))

    async def create_user(self, telegram_user: User, email: str) -> None:
        data = {
            "full_name": f"{telegram_user.first_name} {telegram_user.last_name}",
            "telegram_id": str(telegram_user.id),
            "email": email,
        }
        try:
            response = await self._client.post(data, "/users", language_code=telegram_user.language_code)
        except httpx.HTTPError as error:
            self.logger.error("Failed to connect to user API. error=%s", error)
            raise CreateRemoteUserError() from error

        if response.status_code != 201:
            self.logger.error(
                "Failed to create user in API. status=%s\n body=%s",
                response.status_code,
                response.content,
            )
            raise CreateRemoteUserError()

        self.logger.info("User created successfully!")
