"""Юнит-тесты для отслеживания активных задач DownloadJob в DownloadManager."""

from __future__ import annotations

import asyncio

import pytest

from async_yt_dlp.manager import DownloadJob, DownloadManager
from async_yt_dlp.options import YTDLPOptions


@pytest.mark.asyncio
async def test_download_job_tracking() -> None:
    """Проверяет регистрацию и дерегистрацию объекта DownloadJob во время операции."""
    manager = DownloadManager(max_concurrency=2, queue_size=5)
    job = DownloadJob(
        url="https://example.com/video",
        job_id="test-job-123",
        options=YTDLPOptions(extract_audio=True),
        metadata={"user_id": 42},
    )

    started_event = asyncio.Event()
    finish_event = asyncio.Event()

    async def _long_operation() -> str:
        started_event.set()
        await finish_event.wait()
        return "completed"

    task = asyncio.create_task(manager.run_operation(_long_operation, job=job))

    await started_event.wait()

    # Проверяем, что задача зарегистрирована в active_jobs
    active = manager.active_jobs
    assert len(active) == 1
    assert active[0].job_id == "test-job-123"
    assert active[0].url == "https://example.com/video"
    assert active[0].metadata == {"user_id": 42}
    assert manager.get_job("test-job-123") is job

    # Разрешаем завершение операции
    finish_event.set()
    res = await task
    assert res == "completed"

    # Проверяем, что после завершения задача удалена из active_jobs
    assert len(manager.active_jobs) == 0
    assert manager.get_job("test-job-123") is None
