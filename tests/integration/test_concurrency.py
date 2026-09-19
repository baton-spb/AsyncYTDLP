"""Интеграционные тесты для проверки параллельности и семафоров в AsyncYTDLP."""

import asyncio

import pytest

from async_yt_dlp.client import AsyncYTDLP


@pytest.mark.asyncio
async def test_client_max_concurrency_respected(sample_video_info: dict):
    max_active = 0
    current_active = 0

    class ConcurrencyTrackingBackend:
        async def extract_info(self, *args, **kwargs):
            return {}

        async def download(self, *args, **kwargs):
            nonlocal max_active, current_active
            current_active += 1
            max_active = max(max_active, current_active)
            await asyncio.sleep(0.05)
            current_active -= 1
            return sample_video_info, 0.05

        async def close(self):
            pass

    # Лимит параллельности = 2
    client = AsyncYTDLP(
        max_concurrency=2,
        queue_size=20,
        backend=ConcurrencyTrackingBackend(),
    )

    urls = [f"https://www.youtube.com/watch?v={i}" for i in range(6)]
    async with client:
        tasks = [client.download(u) for u in urls]
        await asyncio.gather(*tasks)

    # Максимальное число одновременно выполнявшихся задач не превысило 2
    assert max_active == 2


@pytest.mark.asyncio
async def test_client_graceful_shutdown_waits_for_active(sample_video_info: dict):
    completed = False

    class SlowBackend:
        async def extract_info(self, *args, **kwargs):
            return {}

        async def download(self, *args, **kwargs):
            nonlocal completed
            await asyncio.sleep(0.1)
            completed = True
            return sample_video_info, 0.1

        async def close(self):
            pass

    client = AsyncYTDLP(max_concurrency=2, backend=SlowBackend())
    async with client:
        # Запускаем задачу в фоне
        dl_task = asyncio.create_task(client.download("https://www.youtube.com/watch?v=slow"))
        await asyncio.sleep(0.01)

    # При выходе из async with вызывается client.close(wait=True),
    # который должен дождаться завершения активной задачи
    assert completed is True
    res = await dl_task
    assert res.info.id == "BaW_jenozKc"
