import logging
import os

from dotenv import load_dotenv
from telegram import Message, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from services.bot_service import BotService


class FinanceBot:
    def __init__(
        self,
        token: str,
        allowed_users: set[int],
        logger: logging.Logger,
    ) -> None:
        self.token = token
        self.allowed_users = allowed_users
        self.logger = logger
        self._service = BotService(logger=self.logger, allowed_users=allowed_users)

    async def start_cmd(self, update: Update, _) -> None | Message:
        return await self._service.start_command(update)

    async def expense_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None | Message:
        return await self._service.add_command(update, context, "debit")

    async def income_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None | Message:
        return await self._service.add_command(update, context, "credit")

    async def confirm_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._service.confirm_entry(update, context)

    def run(self) -> None:
        self.logger.info("Starting Finance Bot...")
        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start_cmd))
        app.add_handler(CommandHandler("expense", self.expense_cmd))
        app.add_handler(CommandHandler("income", self.income_cmd))
        app.add_handler(CallbackQueryHandler(self.confirm_entry, pattern=r"^entry:(confirm|cancel)$"))
        self.logger.info("Bot started, polling for updates...")
        app.run_polling()


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("finance_bot")

    load_dotenv()
    token = os.getenv("BOT_TOKEN", "TOKEN")
    allowed_users = {803626879}  # your user ID
    FinanceBot(token=token, allowed_users=allowed_users, logger=logger).run()


if __name__ == "__main__":
    main()
