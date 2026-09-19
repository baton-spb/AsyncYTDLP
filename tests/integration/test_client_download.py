"""Интеграционные тесты для методов скачивания (download, download_with_progress, download_many)."""

import asyncio
from typing import Any

import pytest

from async_yt_dlp.client import AsyncYTDLP, ErrorPolicy
from async_yt_dlp.exceptions import ExtractionError
from async_yt_dlp.models import DownloadResult
from async_yt_dlp.progress import DownloadStatus, ProgressEvent


@pytest.mark.asyncio
async def test_client_download_with_sync_progress_callback(client_with_fake: AsyncYTDLP):
    events: list[ProgressEvent] = []

    def _on_progress(event: ProgressEvent) -> None:
        events.append(event)

    async with client_with_fake as client:
        res = await client.download(
            "https://www.youtube.com/watch?v=BaW_jenozKc",
            on_progress=_on_progress,
        )

        assert isinstance(res, DownloadResult)
        assert len(events) > 0
        assert any(e.status == DownloadStatus.DOWNLOADING for e in events)
        assert any(e.status == DownloadStatus.FINISHED for e in events)


@pytest.mark.asyncio
async def test_client_download_with_async_progress_callback(client_with_fake: AsyncYTDLP):
    events: list[ProgressEvent] = []

    async def _async_on_progress(event: ProgressEvent) -> None:
        await asyncio.sleep(0.001)
        events.append(event)

    async with client_with_fake as client:
        res = await client.download(
            "https://www.youtube.com/watch?v=BaW_jenozKc",
            on_progress=_async_on_progress,
        )

        assert isinstance(res, DownloadResult)
        assert len(events) > 0


@pytest.mark.asyncio
async def test_client_download_with_progress_generator(client_with_fake: AsyncYTDLP):
    collected_events: list[ProgressEvent] = []

    async with client_with_fake as client:
        async for event in client.download_with_progress(
            "https://www.youtube.com/watch?v=BaW_jenozKc"
        ):
            collected_events.append(event)

    assert len(collected_events) > 0
    statuses = [e.status for e in collected_events]
    assert DownloadStatus.DOWNLOADING in statuses
    assert DownloadStatus.FINISHED in statuses
    assert DownloadStatus.COMPLETE in statuses


@pytest.mark.asyncio
async def test_client_download_many_collect(client_with_fake: AsyncYTDLP):
    urls = [
        "https://www.youtube.com/watch?v=1",
        "https://www.youtube.com/watch?v=2",
        "https://www.youtube.com/watch?v=3",
    ]

    async with client_with_fake as client:
        results = await client.download_many(urls, on_error=ErrorPolicy.COLLECT)

        assert len(results) == 3
        for r in results:
            assert isinstance(r, DownloadResult)


@pytest.mark.asyncio
async def test_client_download_many_skip_errors(client_with_fake: AsyncYTDLP):
    # Настраиваем бэкенд так, чтобы 2-й URL вызывал ошибку
    original_download = client_with_fake._backend.download  # type: ignore

    async def _failing_download(url: str, *args: Any, **kwargs: Any):
        if "fail" in url:
            raise ExtractionError("Simulated video error", url=url)
        return await original_download(url, *args, **kwargs)

    client_with_fake._backend.download = _failing_download  # type: ignore

    urls = [
        "https://www.youtube.com/watch?v=ok1",
        "https://www.youtube.com/watch?v=fail_url",
        "https://www.youtube.com/watch?v=ok2",
    ]

    async with client_with_fake as client:
        # SKIP: возвращаются только успешные результаты
        results_skip = await client.download_many(urls, on_error=ErrorPolicy.SKIP)
        assert len(results_skip) == 2
        assert all(isinstance(r, DownloadResult) for r in results_skip)

        # COLLECT: возвращаются и результаты, и ошибки
        results_collect = await client.download_many(urls, on_error=ErrorPolicy.COLLECT)
        assert len(results_collect) == 3
        assert isinstance(results_collect[0], DownloadResult)
        assert isinstance(results_collect[1], ExtractionError)
        assert isinstance(results_collect[2], DownloadResult)


@pytest.mark.asyncio
async def test_client_check_dependencies(client_with_fake: AsyncYTDLP):
    deps = await client_with_fake.check_dependencies(force_refresh=True)

    assert deps.ytdlp_version != "not_installed"
    assert isinstance(deps.ffmpeg_available, bool)
    assert isinstance(deps.ffprobe_available, bool)
