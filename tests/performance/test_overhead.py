"""Бенчмарки и тесты оверхеда async-yt-dlp по сравнению с синхронными вызовами."""

import asyncio
import time

import pytest

from async_yt_dlp.client import AsyncYTDLP
from async_yt_dlp.progress import ProgressBridge


@pytest.mark.asyncio
async def test_progress_bridge_overhead():
    """Измеряет оверхед передачи 10 000 событий прогресса через ProgressBridge."""
    loop = asyncio.get_running_loop()
    bridge = ProgressBridge(loop, throttle_interval=0.0, queue_size=20000)

    start_time = time.perf_counter()

    # Эмулируем частые вызовы yt-dlp из worker thread
    for i in range(10_000):
        bridge.sync_hook(
            {
                "status": "downloading",
                "downloaded_bytes": i * 100,
                "total_bytes": 1_000_000,
                "speed": 500_000.0,
                "eta": 10.0,
            }
        )

    bridge.finish()

    # Вычитываем все события в асинхронном потребителе
    count = 0
    async for _ in bridge:
        count += 1

    duration = time.perf_counter() - start_time

    # Оверхед на 10k сообщений должен составлять доли секунды
    assert duration < 1.0, f"Слишком большой оверхед моста прогресса: {duration:.4f} с"
    assert count > 0


@pytest.mark.asyncio
async def test_concurrency_overhead(sample_video_info: dict):
    """Измеряет время диспетчеризации 100 одновременных задач через менеджер."""

    class ImmediateBackend:
        async def extract_info(self, *args, **kwargs):
            return sample_video_info

        async def download(self, *args, **kwargs):
            return sample_video_info, 0.001

        async def close(self):
            pass

    client = AsyncYTDLP(
        max_concurrency=10,
        queue_size=200,
        backend=ImmediateBackend(),
    )

    start = time.perf_counter()
    async with client:
        tasks = [client.extract_info(f"https://www.youtube.com/watch?v={i}") for i in range(100)]
        results = await asyncio.gather(*tasks)

    duration = time.perf_counter() - start

    assert len(results) == 100
    # Диспетчеризация 100 задач через семафор должна занимать считанные миллисекунды
    assert duration < 0.5, f"Слишком большой оверхед диспетчеризации задач: {duration:.4f} с"
