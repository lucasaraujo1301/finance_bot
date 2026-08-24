import re

from decimal import Decimal
from logging import Logger

from telegram import Message, Update, User

from exceptions import CreateRemoteUserError
from services.user_api_service import UserService


class BotService:
    def __init__(self, logger: Logger, allowed_users: set[int]):
        self.logger = logger
        self.allowed_users = allowed_users
        self._user_service = UserService(self.logger)

    async def start_command(self, update: Update):
        if not update.message:
            return

        if not update.effective_user:
            self.logger.warning("Unauthorized access attempt: no effective user.")
            return await update.message.reply_text("Unauthorized.")

        telegram_user = update.effective_user
        self.logger.info(f"Received /start command from user {telegram_user.id}")

        if not self._is_allowed_user(telegram_user.id):
            self.logger.warning(f"Unauthorized access attempt from user {telegram_user.id}.")
            return await update.message.reply_text(f"{telegram_user.first_name} you are not allowed to use this bot.")

        self.logger.info(f"Initializing bot for user {telegram_user.id}.")

        await update.message.reply_text(
            f"Hi {telegram_user.first_name}! I'm creating your profile so I can help track your finances."
        )

        try:
            await self._user_service.create_user(telegram_user)
        except CreateRemoteUserError:
            return await update.message.reply_text(
                "I couldn't create your profile right now. Please try again in a moment."
            )

        await update.message.reply_text("Conta criada")

        return await self._show_commands(update.message, telegram_user)

    async def add_command(self, update: Update, category_keywords: dict[str, list[str]]) -> None | Message:
        if not update.message or not update.message.text:
            return
        if not update.effective_user or not self._is_allowed_user(update.effective_user.id):
            return await update.message.reply_text("Unauthorized.")

        text = update.message.text[len("/add ") :].strip()
        match = re.match(r"([\d.,]+)\s+(.+)", text)
        if not match:
            return await update.message.reply_text("Usage: /add <amount> <description>")

        try:
            amount = Decimal(match.group(1).replace(",", "."))
        except Exception:
            return await update.message.reply_text("Invalid amount.")

        description = match.group(2)
        category = self._categorize(description, category_keywords)
        await self._process_entry(update, amount, description, category)
        return await update.message.reply_text(f"Saved: R$ {amount:.2f} — {description}\nCategory: {category}")

    def _is_allowed_user(self, user_id: int) -> bool:
        return user_id in self.allowed_users

    def _categorize(self, description: str, category_keywords: dict[str, list[str]]) -> str:
        description = description.lower()
        for category, keywords in category_keywords.items():
            if any(keyword in description for keyword in keywords):
                return category
        return "other"

    async def _process_entry(self, update: Update, amount: Decimal, description: str, category: str) -> None:
        # TODO: send to your API here
        pass

    async def _show_commands(self, message: Message, user: User):
        return await message.reply_text(
            f"Hi {user.first_name}! I'm ready to help you track your finances.\n\n"
            "Here are the commands you can use:\n"
            "/add <amount> <description>  — add debit"
        )
