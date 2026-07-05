# Finance Bot

Telegram bot for personal expense tracking with automatic categorization.

## Commands

- `/start` — Initialize the bot and show available commands
- `/add <amount> <description>` — Record a debit transaction (e.g. `/add 25.90 ifood`)

Categories are inferred from keywords in the description (e.g. "ifood" → snack, "uber" → transport).

## Setup

1. Create a bot with [BotFather](https://t.me/botfather) and get the token.
2. Set `TOKEN` and `ALLOWED_USERS` in `main.py`.
3. Customize `category_keywords.json` to match your spending patterns.

```bash
uv sync
uv run python main.py
```
