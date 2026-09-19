"""Юнит-тесты для модуля progress.py (ProgressEvent и ProgressBridge)."""

import asyncio

import pytest

from async_yt_dlp.progress import (
    DownloadStatus,
    ProgressBridge,
    ProgressEvent,
    _format_bytes,
    _format_seconds,
)


def test_format_bytes():
    assert _format_bytes(None) == "N/A"
    assert _format_bytes(500) == "500 B"
    assert _format_bytes(1024 * 512) == "512.00 KiB"
    assert _format_bytes(1024 * 1024 * 10) == "10.00 MiB"


def test_format_seconds():
    assert _format_seconds(None) == "Unknown"
    assert _format_seconds(-5) == "Unknown"
    assert _format_seconds(45) == "00:45"
    assert _format_seconds(125) == "02:05"
    assert _format_seconds(3665) == "01:01:05"


def test_progress_event_properties():
    event = ProgressEvent(
        status=DownloadStatus.DOWNLOADING,
        downloaded_bytes=5 * 1024 * 1024,
        total_bytes=10 * 1024 * 1024,
        speed=1024 * 1024 * 2.5,
        eta=2.0,
        elapsed=2.0,
    )

    assert event.percent == pytest.approx(50.0)
    assert event.speed_str == "2.50 MiB/s"
    assert event.eta_str == "00:02"
    assert event.elapsed_str == "00:02"
    assert event.downloaded_str == "5.00 MiB"
    assert event.total_str == "10.00 MiB"


def test_progress_event_finished_percent():
    event = ProgressEvent(
        status=DownloadStatus.FINISHED,
        downloaded_bytes=1000,
        total_bytes=1000,
    )
    assert event.percent == 100.0


@pytest.mark.asyncio
async def test_progress_bridge_event_delivery():
    loop = asyncio.get_running_loop()
    bridge = ProgressBridge(loop, throttle_interval=0.0)

    # Симулируем вызовы из worker thread
    bridge.sync_hook({"status": "downloading", "downloaded_bytes": 100, "total_bytes": 1000})
    bridge.sync_hook({"status": "finished", "downloaded_bytes": 1000, "total_bytes": 1000})
    bridge.sync_postprocessor_hook({"status": "finished", "postprocessor": "Fixup"})
    bridge.finish()

    collected: list[ProgressEvent] = []
    async for event in bridge:
        collected.append(event)

    assert len(collected) == 4
    assert collected[0].status == DownloadStatus.DOWNLOADING
    assert collected[1].status == DownloadStatus.FINISHED
    assert collected[2].status == DownloadStatus.POST_PROCESSING
    assert collected[3].status == DownloadStatus.COMPLETE


@pytest.mark.asyncio
async def test_progress_bridge_throttling():
    loop = asyncio.get_running_loop()
    # Троттлинг 0.2 секунды
    bridge = ProgressBridge(loop, throttle_interval=0.2)

    # Быстрые вызовы подряд
    bridge.sync_hook({"status": "downloading", "downloaded_bytes": 100, "total_bytes": 1000})
    bridge.sync_hook({"status": "downloading", "downloaded_bytes": 200, "total_bytes": 1000})
    bridge.sync_hook({"status": "downloading", "downloaded_bytes": 300, "total_bytes": 1000})

    # Finished и Complete никогда не троттлятся
    bridge.sync_hook({"status": "finished", "downloaded_bytes": 1000, "total_bytes": 1000})
    bridge.finish()

    collected: list[ProgressEvent] = []
    async for event in bridge:
        collected.append(event)

    # Первый downloading прошёл, 2-й и 3-й отброшены троттлингом, finished и complete доставлены
    downloading_events = [e for e in collected if e.status == DownloadStatus.DOWNLOADING]
    assert len(downloading_events) == 1
    assert any(e.status == DownloadStatus.FINISHED for e in collected)
    assert any(e.status == DownloadStatus.COMPLETE for e in collected)


@pytest.mark.asyncio
async def test_progress_bridge_queue_overflow_protection():
    loop = asyncio.get_running_loop()
    # Очень маленькая очередь (2 элемента)
    bridge = ProgressBridge(loop, throttle_interval=0.0, queue_size=2)

    # Отправляем несколько событий без чтения
    bridge.sync_hook({"status": "downloading", "downloaded_bytes": 100})
    bridge.sync_hook({"status": "downloading", "downloaded_bytes": 200})
    bridge.sync_hook({"status": "downloading", "downloaded_bytes": 300})
    bridge.finish()

    # Потребитель вычитывает без зависания
    collected: list[ProgressEvent] = []
    async for event in bridge:
        collected.append(event)

    assert len(collected) > 0
    # Проверяем, что завершающее событие COMPLETE доставлено
    assert any(e.status == DownloadStatus.COMPLETE for e in collected)
