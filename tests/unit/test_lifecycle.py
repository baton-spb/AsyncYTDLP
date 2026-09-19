"""Юнит-тесты для проверки жизненного цикла AsyncYTDLP."""

import pytest

from async_yt_dlp.client import AsyncYTDLP, ClientState
from async_yt_dlp.exceptions import LifecycleError


@pytest.mark.asyncio
async def test_client_state_lifecycle(client_with_fake: AsyncYTDLP):
    client = client_with_fake
    assert client.state == ClientState.NEW
    assert not client.is_closed

    async with client:
        assert client.state == ClientState.RUNNING

    assert client.state == ClientState.CLOSED
    assert client.is_closed


@pytest.mark.asyncio
async def test_operation_after_close_raises(client_with_fake: AsyncYTDLP):
    client = client_with_fake
    await client.close()

    with pytest.raises(LifecycleError, match="closed"):
        await client.extract_info("https://youtube.com/watch?v=123")

    with pytest.raises(LifecycleError, match="closed"):
        await client.download("https://youtube.com/watch?v=123")


@pytest.mark.asyncio
async def test_double_close_idempotent(client_with_fake: AsyncYTDLP):
    client = client_with_fake
    await client.close()
    # Повторный close не должен приводить к ошибкам
    await client.close()
    assert client.state == ClientState.CLOSED


@pytest.mark.asyncio
async def test_reenter_closed_client_raises(client_with_fake: AsyncYTDLP):
    client = client_with_fake
    await client.close()

    with pytest.raises(LifecycleError, match="Невозможно повторно открыть"):
        async with client:
            pass
