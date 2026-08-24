import json
import logging
import os

from pathlib import Path

from dotenv import load_dotenv
from telegram import Message, Update
from telegram.ext import Application, CommandHandler

from services.bot_service import BotService


class FinanceBot:
    def __init__(
        self,
        token: str,
        allowed_users: set[int],
        logger: logging.Logger,
        category_keywords_path: str = "category_keywords.json",
    ) -> None:
        self.token = token
        self.allowed_users = allowed_users
        self.logger = logger
        self.category_keywords = self._load_category_keywords(category_keywords_path)
        self._service = BotService(logger=self.logger, allowed_users=allowed_users)

    def _load_category_keywords(self, category_keywords_path: str) -> dict[str, list[str]]:
        with Path(category_keywords_path).open() as file:
            return json.load(file)

    async def start_cmd(self, update: Update, _) -> None | Message:
        return await self._service.start_command(update)

    async def add_cmd(self, update: Update, _) -> None | Message:
        return await self._service.add_command(update, self.category_keywords)

    def run(self) -> None:
        self.logger.info("Starting Finance Bot...")
        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start_cmd))
        app.add_handler(CommandHandler("add", self.add_cmd))
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
