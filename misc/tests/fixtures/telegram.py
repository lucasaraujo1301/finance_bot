from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def telegram_message():
    message = Mock()
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def telegram_user():
    user = Mock()
    user.id = 123
    user.first_name = "Lucas"
    user.last_name = "Araujo"
    return user


@pytest.fixture
def telegram_update(telegram_message, telegram_user):
    update = Mock()
    update.message = telegram_message
    update.effective_user = telegram_user
    return update
