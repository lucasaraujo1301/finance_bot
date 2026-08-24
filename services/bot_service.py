import json
import time

from datetime import date, datetime
from decimal import Decimal
from logging import Logger
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update, User
from telegram.ext import ContextTypes, ConversationHandler

from exceptions import CreateRemoteUserError
from services.user_api_service import UserService

ENTRY_CONFIRMATION_TIMEOUT_SECONDS = 120
EMAIL, EMAIL_CONFIRMATION = range(2)


class BotService:
    def __init__(self, logger: Logger, allowed_users: set[int]):
        self.logger = logger
        self.allowed_users = allowed_users
        self._user_service = UserService(self.logger)
        self.category_keywords = self._load_category_keywords("category_keywords.json")

    # PRIVATE METHODS

    def _load_category_keywords(self, category_keywords_path: str) -> dict[str, list[str]]:
        with Path(category_keywords_path).open() as file:
            return json.load(file)

    def _is_allowed_user(self, user_id: int) -> bool:
        return user_id in self.allowed_users

    def _categorize(self, description: str) -> str:
        description = description.lower()
        for category, keywords in self.category_keywords.items():
            if any(keyword in description for keyword in keywords):
                return category
        return "other"

    def _parse_date(self, value: str) -> date | None:
        for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, date_format).date()
            except ValueError:
                continue
        return None

    async def _process_entry(
        self,
        update: Update,
        amount: Decimal,
        entry_type: str,
        payment_method: str,
        payment_date: date,
        category: str,
        description: str,
    ) -> None:
        # TODO: send to your API here
        pass

    async def _show_commands(self, message: Message, user: User):
        return await message.reply_text(
            f"Hi {user.first_name}! I'm ready to help you track your finances.\n\n"
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

    # END PRIVATE METHODS

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not update.message:
            return ConversationHandler.END

        if not update.effective_user:
            self.logger.warning("Unauthorized access attempt: no effective user.")
            await update.message.reply_text("Unauthorized.")
            return ConversationHandler.END

        telegram_user = update.effective_user
        self.logger.info(f"Received /start command from user {telegram_user.id}")

        if not self._is_allowed_user(telegram_user.id):
            self.logger.warning(f"Unauthorized access attempt from user {telegram_user.id}.")
            await update.message.reply_text(f"{telegram_user.first_name} you are not allowed to use this bot.")
            return ConversationHandler.END

        self.logger.info(f"Initializing bot for user {telegram_user.id}.")

        if context.user_data is not None:
            context.user_data.pop("pending_email", None)
        await update.message.reply_text(f"Hi {telegram_user.first_name}! Please enter your email address.")
        return EMAIL

    async def receive_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not update.message or not update.message.text or context.user_data is None:
            return EMAIL

        email = update.message.text.strip()
        if not email:
            await update.message.reply_text("Please enter a non-empty email address.")
            return EMAIL

        context.user_data["pending_email"] = email
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Confirm", callback_data="start:confirm_email"),
                    InlineKeyboardButton("Cancel", callback_data="start:cancel_email"),
                ]
            ]
        )
        await update.message.reply_text(f"Please confirm your email: {email}", reply_markup=keyboard)
        return EMAIL_CONFIRMATION

    async def confirm_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if not query:
            return EMAIL_CONFIRMATION

        await query.answer()
        if query.data == "start:cancel_email":
            if context.user_data is not None:
                context.user_data.pop("pending_email", None)
            await query.edit_message_text("Profile creation cancelled.")
            return ConversationHandler.END

        telegram_user = update.effective_user
        email = context.user_data.pop("pending_email", None) if context.user_data is not None else None
        if not telegram_user or not self._is_allowed_user(telegram_user.id) or not email:
            await query.edit_message_text("This email confirmation has expired. Run /start again.")
            return ConversationHandler.END

        try:
            await self._user_service.create_user(telegram_user, email)
        except CreateRemoteUserError:
            await query.edit_message_text(
                "The API rejected this email or could not create your profile. Run /start and try again."
            )
            return ConversationHandler.END

        await query.edit_message_text("Profile created successfully.")
        if query.message:
            await self._show_commands(query.message, telegram_user)
        return ConversationHandler.END

    async def cancel_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if context.user_data is not None:
            context.user_data.pop("pending_email", None)
        if update.message:
            await update.message.reply_text("Profile creation cancelled.")
        return ConversationHandler.END

    async def start_timeout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if context.user_data is not None:
            context.user_data.pop("pending_email", None)
        if update.effective_message:
            await update.effective_message.reply_text("Email confirmation expired. Run /start again.")
        return ConversationHandler.END

    async def add_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        entry_type: str,
    ) -> None | Message:
        if not update.message:
            return
        if not update.effective_user or not self._is_allowed_user(update.effective_user.id):
            return await update.message.reply_text("Unauthorized.")

        arguments = context.args or []
        if len(arguments) < 3:
            return await update.message.reply_text(
                "Usage: /command <amount> <payment_method> [payment_date] [category] <description>"
            )

        try:
            amount = Decimal(arguments[0].replace(",", "."))
        except ValueError:
            return await update.message.reply_text("Invalid amount.")

        payment_method = arguments[1]
        payment_date = date.today()
        category = None
        argument_index = 2

        while argument_index < len(arguments) - 1:
            argument = arguments[argument_index]
            parsed_date = self._parse_date(argument)

            if parsed_date and payment_date == date.today():
                payment_date = parsed_date
                argument_index += 1
                continue
            if category is None and argument.lower() in self.category_keywords:
                category = argument.lower()
                argument_index += 1
                continue
            break

        description = " ".join(arguments[argument_index:])
        category = category or self._categorize(description)
        if context.user_data is None:
            return await update.message.reply_text("Unable to prepare this entry. Please try again.")

        context.user_data["pending_entry"] = {
            "amount": amount,
            "entry_type": entry_type,
            "payment_method": payment_method,
            "payment_date": payment_date,
            "category": category,
            "description": description,
        }
        context.user_data["pending_entry_created_at"] = time.monotonic()
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Confirm", callback_data="entry:confirm"),
                    InlineKeyboardButton("Cancel", callback_data="entry:cancel"),
                ]
            ]
        )
        return await update.message.reply_text(
            f"Please confirm: R$ {amount:.2f} — {description}\n"
            f"Entry type: {entry_type}\n"
            f"Payment method: {payment_method}\n"
            f"Payment date: {payment_date:%d/%m/%Y}\n"
            f"Category: {category}",
            reply_markup=keyboard,
        )

    async def confirm_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return

        await query.answer()
        if not update.effective_user or not self._is_allowed_user(update.effective_user.id):
            await query.edit_message_text("Unauthorized.")
            return

        if context.user_data is None:
            await query.edit_message_text("This entry has expired.")
            return

        entry = context.user_data.pop("pending_entry", None)
        created_at = context.user_data.pop("pending_entry_created_at", None)
        if not entry or created_at is None or time.monotonic() - created_at > ENTRY_CONFIRMATION_TIMEOUT_SECONDS:
            await query.edit_message_text("This entry has expired.")
            return

        if query.data == "entry:cancel":
            await query.edit_message_text("Entry cancelled.")
            return

        await self._process_entry(update, **entry)
        await query.edit_message_text(
            f"Saved: R$ {entry['amount']:.2f} — {entry['description']}\n"
            f"Entry type: {entry['entry_type']}\n"
            f"Payment method: {entry['payment_method']}\n"
            f"Payment date: {entry['payment_date']:%d/%m/%Y}\n"
            f"Category: {entry['category']}"
        )
