# AGENTS.md

## Project overview

`finance_bot` is an async Telegram bot for personal finance tracking. It uses
`python-telegram-bot` for Telegram integration and `httpx` to communicate with a
remote finance API.

The current implementation supports:

```text
start - Authorize the user, collect and confirm their email, create the remote profile, and display available commands
expense - Prepare an expense and request confirmation before saving it
income - Prepare an income and request confirmation before saving it
```

Expense and income confirmations expire after two minutes.

## User signup

The `/start` command uses a `ConversationHandler` to collect the user's email as a
regular text message. The bot asks the user to confirm or cancel the email before
calling the remote user API. The conversation expires after two minutes, and users
can also exit it with `/cancel`.

The bot only requires non-empty email input. Email format validation, normalization,
and duplicate handling belong to the remote API. `UserService.create_user` includes
the confirmed email in the user creation payload and translates API failures into a
`CreateRemoteUserError` for the bot layer to handle.

## Current architecture

The project uses a small layered architecture:

```text
main.py -> BotService -> domain API service -> ApiClient
```

Dependencies should continue to flow downward. Telegram-specific behavior belongs
in the bot layer, domain API operations belong in services, and generic HTTP behavior
belongs in the API client.

## Repository structure

```text
finance_bot/
├── clients/
│   ├── __init__.py
│   └── api_client.py          # Generic async HTTP transport
├── services/
│   ├── __init__.py
│   ├── bot_service.py         # Telegram orchestration and command handling
│   └── user_api_service.py    # User-related remote API operations
├── tests/
│   ├── clients/
│   │   ├── __init__.py
│   │   └── test_api_client.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── telegram.py
│   │   └── user_service.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── test_bot_service.py
│   │   └── test_user_api_service.py
│   ├── __init__.py
│   └── conftest.py            # Exports shared test fixtures
├── category_keywords.json     # Category-to-keyword mapping
├── exceptions.py              # Domain exceptions
├── main.py                    # Application setup and Telegram handler registration
├── pyproject.toml             # Project dependencies and tool configuration
└── README.md
```

## Layer responsibilities

| Layer | Responsibilities | Must not contain |
| --- | --- | --- |
| `main.py` | Load `.env`, read runtime configuration, construct dependencies, register Telegram handlers, and start polling. | Command parsing, domain business logic, or direct API operations. |
| `BotService` | Handle Telegram updates and replies, authorize users, parse and validate command arguments, and delegate external operations to domain services. | Direct `httpx` calls or generic HTTP transport logic. |
| Domain API services | Translate domain actions into API requests, call `ApiClient`, and convert transport failures into domain exceptions. | Telegram command parsing or user reply logic. |
| `ApiClient` | Perform generic HTTP operations, construct headers, normalize URLs, and preserve trailing slashes. | Telegram behavior or finance-domain business logic. |

## Technology

- Python 3.14
- `uv`
- `python-telegram-bot`
- `httpx.AsyncClient`
- `python-dotenv`
- `pytest` and `pytest-asyncio`
- Ruff
- `ty`

Run the project checks after code changes:

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```
