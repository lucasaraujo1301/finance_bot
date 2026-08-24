from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from telegram import InlineKeyboardMarkup

from exceptions import CreateRemoteUserError
from services.bot_service import ENTRY_CONFIRMATION_TIMEOUT_SECONDS, BotService

COMMAND_HELP = (
    "Here are the commands you can use:\n"
    "/expense <amount> <payment_method> [payment_date] [category] <description>\n"
    "/income <amount> <payment_method> [payment_date] [category] <description>\n\n"
    "/expense records a debit, and /income records a credit.\n\n"
    "Arguments:\n"
    "<amount> required: transaction amount; use . or , as the decimal separator.\n"
    "<payment_method> required: how the transaction was paid or received.\n"
    "[payment_date] optional: date in DD/MM/YYYY or YYYY-MM-DD format; defaults to today.\n"
    "[category] optional: category name; inferred from the description when omitted.\n"
    "<description> required: one or more words describing the transaction."
)


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
            f"Hi {telegram_user.first_name}! I'm ready to help you track your finances.\n\n{COMMAND_HELP}"
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
            f"Hi {telegram_user.first_name}! I'm ready to help you track your finances.\n\n{COMMAND_HELP}"
        )

    async def test_add_command_requires_at_least_three_arguments(self, monkeypatch, telegram_update, telegram_message):
        service, _ = self.make_service(monkeypatch)
        context = SimpleNamespace(args=["10", "pix"])

        await service.add_command(telegram_update, context, "debit")

        telegram_message.reply_text.assert_awaited_once_with(
            "Usage: /command <amount> <payment_method> [payment_date] [category] <description>"
        )

    async def test_add_command_parses_date_category_and_multi_word_description(
        self, monkeypatch, telegram_update, telegram_message
    ):
        service, _ = self.make_service(monkeypatch)
        service._process_entry = AsyncMock()
        context = SimpleNamespace(
            args=["25,90", "pix", "24/08/2026", "snack", "pizza", "with", "friends"], user_data={}
        )

        await service.add_command(telegram_update, context, "debit")

        service._process_entry.assert_not_awaited()
        pending_entry = context.user_data["pending_entry"]
        assert pending_entry == {
            "amount": Decimal("25.90"),
            "entry_type": "debit",
            "payment_method": "pix",
            "payment_date": date(2026, 8, 24),
            "category": "snack",
            "description": "pizza with friends",
        }
        assert "pending_entry_created_at" in context.user_data
        assert telegram_message.reply_text.await_args.args == (
            "Please confirm: R$ 25.90 — pizza with friends\n"
            "Entry type: debit\n"
            "Payment method: pix\n"
            "Payment date: 24/08/2026\n"
            "Category: snack",
        )
        assert isinstance(telegram_message.reply_text.await_args.kwargs["reply_markup"], InlineKeyboardMarkup)

    async def test_add_command_accepts_iso_date_and_infers_category(self, monkeypatch, telegram_update):
        service, _ = self.make_service(monkeypatch)
        service._process_entry = AsyncMock()
        context = SimpleNamespace(args=["50", "cash", "2026-08-24", "uber", "home"], user_data={})

        await service.add_command(telegram_update, context, "credit")

        assert context.user_data["pending_entry"]["payment_date"] == date(2026, 8, 24)
        assert context.user_data["pending_entry"]["category"] == "transport"

    async def test_add_command_uses_today_when_date_is_omitted(self, monkeypatch, telegram_update):
        service, _ = self.make_service(monkeypatch)
        service._process_entry = AsyncMock()
        context = SimpleNamespace(args=["10", "pix", "ifood"], user_data={})

        await service.add_command(telegram_update, context, "debit")

        assert context.user_data["pending_entry"]["payment_date"] == date.today()

    async def test_confirm_entry_processes_pending_entry(self, monkeypatch, telegram_update):
        service, _ = self.make_service(monkeypatch)
        service._process_entry = AsyncMock()
        query = Mock()
        query.data = "entry:confirm"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        telegram_update.callback_query = query
        entry = {
            "amount": Decimal("25.90"),
            "entry_type": "debit",
            "payment_method": "pix",
            "payment_date": date(2026, 8, 24),
            "category": "snack",
            "description": "pizza",
        }
        context = SimpleNamespace(user_data={"pending_entry": entry, "pending_entry_created_at": 100.0})
        monkeypatch.setattr("services.bot_service.time.monotonic", Mock(return_value=101.0))

        await service.confirm_entry(telegram_update, context)

        service._process_entry.assert_awaited_once_with(telegram_update, **entry)
        assert "pending_entry" not in context.user_data
        query.edit_message_text.assert_awaited_once_with(
            "Saved: R$ 25.90 — pizza\nEntry type: debit\nPayment method: pix\nPayment date: 24/08/2026\nCategory: snack"
        )

    async def test_confirm_entry_cancels_pending_entry(self, monkeypatch, telegram_update):
        service, _ = self.make_service(monkeypatch)
        service._process_entry = AsyncMock()
        query = Mock()
        query.data = "entry:cancel"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        telegram_update.callback_query = query
        context = SimpleNamespace(
            user_data={"pending_entry": {"amount": Decimal("10")}, "pending_entry_created_at": 100.0}
        )
        monkeypatch.setattr("services.bot_service.time.monotonic", Mock(return_value=101.0))

        await service.confirm_entry(telegram_update, context)

        service._process_entry.assert_not_awaited()
        query.edit_message_text.assert_awaited_once_with("Entry cancelled.")

    async def test_confirm_entry_rejects_expired_entry(self, monkeypatch, telegram_update):
        service, _ = self.make_service(monkeypatch)
        query = Mock()
        query.data = "entry:confirm"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        telegram_update.callback_query = query
        context = SimpleNamespace(user_data={})

        await service.confirm_entry(telegram_update, context)

        query.edit_message_text.assert_awaited_once_with("This entry has expired.")

    async def test_confirm_entry_rejects_entry_after_two_minutes(self, monkeypatch, telegram_update):
        service, _ = self.make_service(monkeypatch)
        service._process_entry = AsyncMock()
        query = Mock()
        query.data = "entry:confirm"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        telegram_update.callback_query = query
        context = SimpleNamespace(
            user_data={
                "pending_entry": {"amount": Decimal("10")},
                "pending_entry_created_at": 100.0,
            }
        )
        monkeypatch.setattr(
            "services.bot_service.time.monotonic",
            Mock(return_value=100.0 + ENTRY_CONFIRMATION_TIMEOUT_SECONDS + 1),
        )

        await service.confirm_entry(telegram_update, context)

        service._process_entry.assert_not_awaited()
        assert context.user_data == {}
        query.edit_message_text.assert_awaited_once_with("This entry has expired.")
