from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from services.user_api_service import UserService


@pytest.fixture
def user_service_dependencies(monkeypatch):
    logger = Mock()
    client = Mock()
    client.post = AsyncMock()

    monkeypatch.setattr("services.user_api_service.ApiClient", Mock(return_value=client))

    service = UserService(logger=logger)

    return SimpleNamespace(
        client=client,
        logger=logger,
        service=service,
    )
