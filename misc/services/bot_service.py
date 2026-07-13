from logging import Logger

from telegram import Message, Update, User

from misc.dataclass import UserApiKeyRecord
from misc.repository import UserRepository


class BotService:
    def __init__(self, logger: Logger, allowed_users: set[int]):
        self.logger = logger
        self.allowed_users = allowed_users
        self._repository = UserRepository()

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
        user = self._get_user_by_telegram_id(telegram_user.id)

        if not user:
            await update.message.reply_text(
                f"Hi {telegram_user.first_name}! I'm creating your profile so I can help track your finances."
            )
        return await self._show_commands(update.message, telegram_user)

    def _get_user_by_telegram_id(self, telegram_id: int) -> None | UserApiKeyRecord:
        return self._repository.get_user_by_telegram_id(telegram_id)

    def _is_allowed_user(self, user_id: int) -> bool:
        return user_id in self.allowed_users

    async def _show_commands(self, message: Message, user: User):
        return await message.reply_text(
            f"Hi {user.first_name}! I'm ready to help you track your finances.\n\n"
            "Here are the commands you can use:\n"
            "/add <amount> <description>  — add debit"
        )
