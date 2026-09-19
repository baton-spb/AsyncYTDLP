"""Юнит-тесты для модуля manager.py (DownloadManager)."""

import asyncio

import pytest

from async_yt_dlp.exceptions import LifecycleError, QueueFullError
from async_yt_dlp.manager import DownloadManager


@pytest.mark.asyncio
async def test_manager_bounded_concurrency():
    # Ограничение 2 одновременных задачи
    manager = DownloadManager(max_concurrency=2, queue_size=10)

    max_simultaneous = 0
    current_simultaneous = 0

    async def _mock_task():
        nonlocal max_simultaneous, current_simultaneous
        current_simultaneous += 1
        max_simultaneous = max(max_simultaneous, current_simultaneous)
        await asyncio.sleep(0.05)
        current_simultaneous -= 1
        return "done"

    tasks = [manager.run_operation(_mock_task) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    assert results == ["done"] * 5
    assert max_simultaneous <= 2


@pytest.mark.asyncio
async def test_manager_queue_limit():
    # max_concurrency=1, queue_size=2
    manager = DownloadManager(max_concurrency=1, queue_size=2)

    release_first = asyncio.Event()

    async def _blocking():
        await release_first.wait()

    # 1-я задача захватывает семафор
    t1 = asyncio.create_task(manager.run_operation(_blocking))
    await asyncio.sleep(0.01)

    # 2-я и 3-я задачи занимают очередь ожидания (queue_size=2)
    t2 = asyncio.create_task(manager.run_operation(_blocking))
    t3 = asyncio.create_task(manager.run_operation(_blocking))
    await asyncio.sleep(0.01)

    # 4-я задача превышает лимит очереди
    with pytest.raises(QueueFullError):
        await manager.run_operation(_blocking)

    # Разблокируем
    release_first.set()
    await asyncio.gather(t1, t2, t3)


@pytest.mark.asyncio
async def test_manager_shutdown_cancels_waiting():
    manager = DownloadManager(max_concurrency=1, queue_size=5)

    release_task = asyncio.Event()

    async def _blocking():
        await release_task.wait()

    t1 = asyncio.create_task(manager.run_operation(_blocking))
    await asyncio.sleep(0.01)

    # Запускаем shutdown без ожидания
    shutdown_task = asyncio.create_task(manager.shutdown(wait=False))
    await shutdown_task

    assert manager.is_closed

    with pytest.raises(LifecycleError):
        await manager.run_operation(lambda: asyncio.sleep(0.1))

    release_task.set()
    with pytest.raises(asyncio.CancelledError):
        await t1
