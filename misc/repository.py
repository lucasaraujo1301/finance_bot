import os
import sqlite3

from pathlib import Path

from cryptography.fernet import Fernet

from misc.dataclass import UserApiKeyRecord

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "db.sqlite"


class UserRepository:
    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = database_path
        key = os.getenv("ENCYRPTION_KEY", "")
        self.crypto = Fernet(key)
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    api_key BLOB NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add_user(self, telegram_id: int, api_key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (telegram_id, api_key)
                VALUES (?, ?)
                """,
                (telegram_id, api_key),
            )

    def get_user_by_telegram_id(self, telegram_id: int) -> UserApiKeyRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT telegram_id, api_key, created_at
                FROM users
                WHERE telegram_id = ?
                """,
                (telegram_id,),
            ).fetchone()

        return UserApiKeyRecord(**dict(row)) if row is not None else None
