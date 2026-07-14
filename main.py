import json
import logging
import os
import re

from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from telegram import Message, Update
from telegram.ext import Application, CommandHandler

from misc.services.bot_service import BotService


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

    def _is_allowed_user(self, update: Update) -> bool:
        return bool(update.effective_user and update.effective_user.id in self.allowed_users)

    def categorize(self, description: str) -> str:
        desc_lower = description.lower()
        for category, keywords in self.category_keywords.items():
            for kw in keywords:
                if kw in desc_lower:
                    return category
        return "other"

    async def start_cmd(self, update: Update, _) -> None | Message:
        return await self._service.start_command(update)

    async def add_cmd(self, update: Update, _) -> None | Message:
        if not update.message or not update.message.text:
            return
        if not update.effective_user:
            return await update.message.reply_text("Unauthorized.")

        if not self._is_allowed_user(update):
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
        category = self.categorize(description)

        await self.process_entry(update, amount, description, category)
        return await update.message.reply_text(f"Saved: R$ {amount:.2f} — {description}\nCategory: {category}")

    async def process_entry(self, update: Update, amount: Decimal, description: str, category: str) -> None:
        # TODO: send to your API here
        # async with httpx.AsyncClient() as client:
        #     await client.post("https://your-api.com/debits", json={
        #         "amount": float(amount), "description": description, "category": category
        #     })
        pass

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
    logger.info(os.getenv("ENCRYPTION_KEY"))
    token = os.getenv("BOT_TOKEN", "TOKEN")
    allowed_users = {803626879}  # your user ID
    FinanceBot(token=token, allowed_users=allowed_users, logger=logger).run()


if __name__ == "__main__":
    main()
