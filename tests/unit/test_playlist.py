"""Юнит-тесты для методов download_playlist и download_playlist_all."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from async_yt_dlp.backend import DownloadBackend
from async_yt_dlp.client import AsyncYTDLP, ErrorPolicy
from async_yt_dlp.exceptions import DownloadError
from async_yt_dlp.models import DownloadResult
from async_yt_dlp.progress import ProgressBridge


class _MockPlaylistBackend(DownloadBackend):
    """Строго типизированный мок-бэкенд для тестирования плейлистов."""

    def __init__(
        self,
        info: Mapping[str, object],
        *,
        fail_first_download: bool = False,
    ) -> None:
        self._info = dict(info)
        self._fail_first = fail_first_download
        self.download_calls: list[str] = []
        self._call_count = 0

    async def extract_info(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        download: bool = False,
        extra_info: Mapping[str, object] | None = None,
        job_id: str | None = None,
    ) -> dict[str, object]:
        return dict(self._info)

    async def download(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        progress_bridge: ProgressBridge | None = None,
        extra_info: Mapping[str, object] | None = None,
        job_id: str | None = None,
    ) -> tuple[dict[str, object], float]:
        self.download_calls.append(url)
        self._call_count += 1
        if self._fail_first and self._call_count == 1:
            raise DownloadError("Эмуляция ошибки сети", url=url)
        return (
            {
                "id": "item_id",
                "title": "Item title",
                "ext": "mp4",
                "filepath": "mock.mp4",
            },
            0.1,
        )

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_download_playlist_full(
    sample_playlist_info: Mapping[str, object],
) -> None:
    """Проверяет скачивание всех элементов плейлиста через асинхронный генератор."""
    fake = _MockPlaylistBackend(sample_playlist_info)
    client = AsyncYTDLP(backend=fake)

    results: list[DownloadResult] = []
    async for item in client.download_playlist(
        "https://www.youtube.com/playlist?list=PL_test_playlist_123"
    ):
        assert isinstance(item, DownloadResult)
        results.append(item)

    # В sample_playlist_info 2 элемента
    assert len(results) == 2
    assert len(fake.download_calls) == 2


@pytest.mark.asyncio
async def test_download_playlist_slicing(
    sample_playlist_info: Mapping[str, object],
) -> None:
    """Проверяет фильтрацию элементов по start, end и max_items."""
    fake = _MockPlaylistBackend(sample_playlist_info)
    client = AsyncYTDLP(backend=fake)

    # Запрос только 1 элемента со 2-й позиции (start=2, max_items=1)
    results = await client.download_playlist_all(
        "https://www.youtube.com/playlist?list=PL_test_playlist_123",
        start=2,
        max_items=1,
    )
    assert len(results) == 1
    assert isinstance(results[0], DownloadResult)


@pytest.mark.asyncio
async def test_download_playlist_single_video_fallback(
    sample_video_info: Mapping[str, object],
) -> None:
    """Проверяет корректную обработку вызова download_playlist на URL одиночного видео."""
    fake = _MockPlaylistBackend(sample_video_info)
    client = AsyncYTDLP(backend=fake)

    results = await client.download_playlist_all("https://www.youtube.com/watch?v=BaW_jenozKc")
    assert len(results) == 1
    assert isinstance(results[0], DownloadResult)


@pytest.mark.asyncio
async def test_download_playlist_error_policy_collect(
    sample_playlist_info: Mapping[str, object],
) -> None:
    """Проверяет политику сбора ошибок ErrorPolicy.COLLECT при сбое одного из элементов."""
    fake = _MockPlaylistBackend(sample_playlist_info, fail_first_download=True)
    client = AsyncYTDLP(backend=fake)

    results = await client.download_playlist_all(
        "https://www.youtube.com/playlist?list=PL_test_playlist_123",
        on_error=ErrorPolicy.COLLECT,
    )
    assert len(results) == 2
    assert isinstance(results[0], DownloadError)
    assert isinstance(results[1], DownloadResult)


@pytest.mark.asyncio
async def test_download_playlist_error_policy_skip(
    sample_playlist_info: Mapping[str, object],
) -> None:
    """Проверяет политику пропуска сбойных элементов ErrorPolicy.SKIP."""
    fake = _MockPlaylistBackend(sample_playlist_info, fail_first_download=True)
    client = AsyncYTDLP(backend=fake)

    results = await client.download_playlist_all(
        "https://www.youtube.com/playlist?list=PL_test_playlist_123",
        on_error=ErrorPolicy.SKIP,
    )
    assert len(results) == 1
    assert isinstance(results[0], DownloadResult)
