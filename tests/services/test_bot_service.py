from unittest.mock import AsyncMock, Mock

import pytest

from exceptions import CreateRemoteUserError
from services.bot_service import BotService


@pytest.mark.asyncio
class TestBotService:
    def make_service(self, monkeypatch):
        user_service = Mock()
        user_service.create_user = AsyncMock()
        monkeypatch.setattr("services.bot_service.UserService", Mock(return_value=user_service))

        service = BotService(logger=Mock(), allowed_users={123})
        return service, user_service

    async def test_start_command_returns_when_message_is_missing(self, monkeypatch, telegram_update):
        service, user_service = self.make_service(monkeypatch)
        telegram_update.message = None

        response = await service.start_command(telegram_update)

        assert response is None
        user_service.create_user.assert_not_called()

    async def test_start_command_replies_unauthorized_when_effective_user_is_missing(
        self, monkeypatch, telegram_update, telegram_message
    ):
        service, user_service = self.make_service(monkeypatch)
        telegram_update.effective_user = None

        await service.start_command(telegram_update)

        telegram_message.reply_text.assert_awaited_once_with("Unauthorized.")
        user_service.create_user.assert_not_called()

    async def test_start_command_replies_not_allowed_when_user_is_not_allowed(
        self, monkeypatch, telegram_update, telegram_message, telegram_user
    ):
        service, user_service = self.make_service(monkeypatch)
        service.allowed_users = {999}

        await service.start_command(telegram_update)

        telegram_message.reply_text.assert_awaited_once_with(
            f"{telegram_user.first_name} you are not allowed to use this bot."
        )
        user_service.create_user.assert_not_called()

    async def test_start_command_creates_user_and_sends_confirmation(
        self, monkeypatch, telegram_update, telegram_message, telegram_user
    ):
        service, user_service = self.make_service(monkeypatch)

        await service.start_command(telegram_update)

        user_service.create_user.assert_awaited_once_with(telegram_user)
        telegram_message.reply_text.assert_any_await(
            f"Hi {telegram_user.first_name}! I'm creating your profile so I can help track your finances."
        )
        telegram_message.reply_text.assert_any_await("Conta criada")
        telegram_message.reply_text.assert_any_await(
            f"Hi {telegram_user.first_name}! I'm ready to help you track your finances.\n\n"
            "Here are the commands you can use:\n"
            "/add <amount> <description>  — add debit"
        )

    async def test_start_command_replies_when_user_creation_fails(
        self, monkeypatch, telegram_update, telegram_message, telegram_user
    ):
        service, user_service = self.make_service(monkeypatch)
        user_service.create_user.side_effect = CreateRemoteUserError()

        await service.start_command(telegram_update)

        user_service.create_user.assert_awaited_once_with(telegram_user)
        telegram_message.reply_text.assert_any_await(
            f"Hi {telegram_user.first_name}! I'm creating your profile so I can help track your finances."
        )
        telegram_message.reply_text.assert_any_await(
            "I couldn't create your profile right now. Please try again in a moment."
        )

    async def test_show_commands_uses_user_first_name(self, monkeypatch, telegram_message, telegram_user):
        service, _ = self.make_service(monkeypatch)

        await service._show_commands(telegram_message, telegram_user)

        telegram_message.reply_text.assert_awaited_once_with(
            f"Hi {telegram_user.first_name}! I'm ready to help you track your finances.\n\n"
            "Here are the commands you can use:\n"
            "/add <amount> <description>  — add debit"
        )
