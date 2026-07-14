import os

from dataclasses import dataclass

from cryptography.fernet import Fernet


@dataclass(frozen=True)
class UserApiKeyRecord:
    telegram_id: int
    api_key: str
    created_at: str

    @property
    def decrypted_api_key(self) -> str:
        fernet = Fernet(os.getenv("ENCRYPTION_KEY", ""))
        return fernet.decrypt(bytes.fromhex(self.api_key)).decode()
