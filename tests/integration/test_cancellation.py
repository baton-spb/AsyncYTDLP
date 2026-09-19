"""Интеграционные тесты для проверки cancellation и таймаутов в AsyncYTDLP."""

import asyncio

import pytest

from async_yt_dlp.client import AsyncYTDLP


@pytest.mark.asyncio
async def test_client_cancellation_during_download():
    task_started = asyncio.Event()

    class LongRunningBackend:
        async def extract_info(self, *args, **kwargs):
            return {}

        async def download(self, *args, **kwargs):
            task_started.set()
            await asyncio.sleep(5.0)
            return {}, 5.0

        async def close(self):
            pass

    client = AsyncYTDLP(backend=LongRunningBackend())
    async with client:
        dl_task = asyncio.create_task(client.download("https://www.youtube.com/watch?v=long"))

        await task_started.wait()
        # Отменяем задачу
        dl_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await dl_task


@pytest.mark.asyncio
async def test_client_timeout_via_asyncio_timeout():
    class HangBackend:
        async def extract_info(self, *args, **kwargs):
            await asyncio.sleep(10.0)
            return {}

        async def download(self, *args, **kwargs):
            await asyncio.sleep(10.0)
            return {}, 10.0

        async def close(self):
            pass

    client = AsyncYTDLP(backend=HangBackend())
    async with client:
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0.05):
                await client.extract_info("https://www.youtube.com/watch?v=hang")


@pytest.mark.asyncio
async def test_cancellation_during_progress_stream():
    class StreamingBackend:
        async def extract_info(self, *args, **kwargs):
            return {}

        async def download(self, url, params, *, progress_bridge=None, **kwargs):
            if progress_bridge:
                for i in range(100):
                    progress_bridge.sync_hook(
                        {
                            "status": "downloading",
                            "downloaded_bytes": i * 10,
                            "total_bytes": 1000,
                        }
                    )
                    await asyncio.sleep(0.02)
            return {}, 2.0

        async def close(self):
            pass

    client = AsyncYTDLP(backend=StreamingBackend())
    async with client:
        stream = client.download_with_progress("https://www.youtube.com/watch?v=stream")

        events_seen = 0
        async for _ in stream:
            events_seen += 1
            if events_seen == 2:
                # Прерываем итерацию
                break

        assert events_seen == 2
