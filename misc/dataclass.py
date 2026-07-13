from dataclasses import dataclass


@dataclass(frozen=True)
class UserApiKeyRecord:
    telegram_id: int
    api_key: bytes
    created_at: str
