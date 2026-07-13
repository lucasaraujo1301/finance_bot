from unittest.mock import Mock

import pytest

from misc.dataclass import UserApiKeyRecord
from misc.services.bot_service import BotService


@pytest.mark.asyncio
class TestBotService:
    def make_service(self, monkeypatch, user_record: UserApiKeyRecord | None = None):
        repository = Mock()
        repository.get_user_by_telegram_id.return_value = user_record
        monkeypatch.setattr("misc.services.bot_service.UserRepository", Mock(return_value=repository))

        service = BotService(logger=Mock(), allowed_users={123})
        return service, repository

    async def test_start_command_returns_when_message_is_missing(self, monkeypatch, telegram_update):
        service, repository = self.make_service(monkeypatch)
        telegram_update.message = None

        response = await service.start_command(telegram_update)

        assert response is None
        repository.get_user_by_telegram_id.assert_not_called()

    async def test_start_command_replies_unauthorized_when_effective_user_is_missing(
        self, monkeypatch, telegram_update, telegram_message
    ):
        service, repository = self.make_service(monkeypatch)
        telegram_update.effective_user = None

        await service.start_command(telegram_update)

        telegram_message.reply_text.assert_awaited_once_with("Unauthorized.")
        repository.get_user_by_telegram_id.assert_not_called()

    async def test_start_command_replies_not_allowed_when_user_is_not_allowed(
        self, monkeypatch, telegram_update, telegram_message, telegram_user
    ):
        service, repository = self.make_service(monkeypatch)
        service.allowed_users = {999}

        await service.start_command(telegram_update)

        telegram_message.reply_text.assert_awaited_once_with(
            f"{telegram_user.first_name} you are not allowed to use this bot."
        )
        repository.get_user_by_telegram_id.assert_not_called()

    async def test_start_command_sends_profile_creation_message_when_user_does_not_exist(
        self, monkeypatch, telegram_update, telegram_message, telegram_user
    ):
        service, repository = self.make_service(monkeypatch)

        await service.start_command(telegram_update)

        repository.get_user_by_telegram_id.assert_called_once_with(telegram_user.id)
        telegram_message.reply_text.assert_any_await(
            f"Hi {telegram_user.first_name}! I'm creating your profile so I can help track your finances."
        )
        telegram_message.reply_text.assert_any_await(
            f"Hi {telegram_user.first_name}! I'm ready to help you track your finances.\n\n"
            "Here are the commands you can use:\n"
            "/add <amount> <description>  — add debit"
        )

    async def test_start_command_only_shows_commands_when_user_already_exists(
        self, monkeypatch, telegram_update, telegram_message, telegram_user
    ):
        user_record = UserApiKeyRecord(telegram_id=telegram_user.id, api_key=b"api-key", created_at="2026-07-13")
        service, repository = self.make_service(monkeypatch, user_record=user_record)

        await service.start_command(telegram_update)

        repository.get_user_by_telegram_id.assert_called_once_with(telegram_user.id)
        telegram_message.reply_text.assert_awaited_once_with(
            f"Hi {telegram_user.first_name}! I'm ready to help you track your finances.\n\n"
            "Here are the commands you can use:\n"
            "/add <amount> <description>  — add debit"
        )

    async def test_show_commands_uses_user_first_name(self, monkeypatch, telegram_message, telegram_user):
        service, _ = self.make_service(monkeypatch)

        await service._show_commands(telegram_message, telegram_user)

        telegram_message.reply_text.assert_awaited_once_with(
            f"Hi {telegram_user.first_name}! I'm ready to help you track your finances.\n\n"
            "Here are the commands you can use:\n"
            "/add <amount> <description>  — add debit"
        )
