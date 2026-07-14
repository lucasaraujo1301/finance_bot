from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from misc.services.user_api_service import UserService


@pytest.fixture
def user_service_dependencies(monkeypatch):
    logger = Mock()
    repository = Mock()
    client = Mock()
    client.post = AsyncMock()
    cryptography = Mock()
    cryptography.encrypt.return_value = b"encrypted-api-key"

    monkeypatch.setattr("misc.services.user_api_service.UserRepository", Mock(return_value=repository))
    monkeypatch.setattr("misc.services.user_api_service.ApiClient", Mock(return_value=client))
    monkeypatch.setattr("misc.services.user_api_service.Fernet", Mock(return_value=cryptography))

    service = UserService(logger=logger)

    return SimpleNamespace(
        client=client,
        cryptography=cryptography,
        logger=logger,
        repository=repository,
        service=service,
    )
