import os

from logging import Logger

import httpx

from cryptography.fernet import Fernet
from telegram import User

from misc.clients.api_client import ApiClient
from misc.dataclass import UserApiKeyRecord
from misc.exceptions import CreateRemoteUserError
from misc.repository import UserRepository


class UserService:
    def __init__(self, logger: Logger):
        self.logger = logger
        self._repository = UserRepository()
        self._client = ApiClient(self.logger, os.getenv("API_BASE_URL", ""))
        key = os.getenv("ENCRYPTION_KEY", "")
        self.cryptography = Fernet(key)

    def get_user_by_telegram_id(self, telegram_id: int) -> None | UserApiKeyRecord:
        return self._repository.get_user_by_telegram_id(telegram_id)

    async def create_user(self, telegram_user: User) -> None:
        data = {
            "full_name": f"{telegram_user.first_name} {telegram_user.last_name}",
            "telegram_id": str(telegram_user.id),
        }
        try:
            response = await self._client.post(data, "/users")
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

        try:
            api_key = response.json()["api_key"]
        except (KeyError, ValueError) as error:
            self.logger.error("API created user without api_key. body=%s", response.text)
            raise CreateRemoteUserError() from error

        api_key = self.cryptography.encrypt(api_key.encode()).hex()
        self._repository.add_user(telegram_user.id, api_key=api_key)
