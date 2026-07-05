import json
import logging
import os
import re

from decimal import Decimal

from dotenv import load_dotenv
from telegram import Message, Update
from telegram.ext import Application, CommandHandler

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("finance_bot")
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "TOKEN")
ALLOWED_USERS = {803626879}  # your user ID

with open("category_keywords.json") as f:
    CATEGORY_KEYWORDS = json.load(f)


def categorize(description: str) -> str:
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return category
    return "other"


async def init_cmd(update: Update, _) -> None | Message:
    logger.info(f"Received /init command from user {update.effective_user.id if update.effective_user else 'unknown'}")
    if not update.message:
        return

    if not update.effective_user:
        logger.warning("Unauthorized access attempt: no effective user.")
        return await update.message.reply_text("Unauthorized.")

    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        logger.warning(f"Unauthorized access attempt from user {user_id}.")
        return await update.message.reply_text("Private bot.")
    logger.info(f"Initializing bot for user {user_id}.")
    return await update.message.reply_text("Bot ready.\n\nCommands:\n/add <amount> <description>  — add debit")


async def add_cmd(update: Update, _) -> None | Message:
    if not update.message or not update.message.text:
        return
    if not update.effective_user:
        return await update.message.reply_text("Unauthorized.")

    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
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
    category = categorize(description)

    await process_entry(update, amount, description, category)
    return await update.message.reply_text(f"Saved: R$ {amount:.2f} — {description}\nCategory: {category}")


async def process_entry(update: Update, amount: Decimal, description: str, category: str):
    # TODO: send to your API here
    # async with httpx.AsyncClient() as client:
    #     await client.post("https://your-api.com/debits", json={
    #         "amount": float(amount), "description": description, "category": category
    #     })
    pass


def main():
    logger.info("Starting Finance Bot...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", init_cmd))
    app.add_handler(CommandHandler("add", add_cmd))
    logger.info("Bot started, polling for updates...")
    app.run_polling()


if __name__ == "__main__":
    main()
