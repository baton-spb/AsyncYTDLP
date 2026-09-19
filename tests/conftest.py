"""Общие фикстуры и тестовые данные для pytest."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import pytest

from async_yt_dlp.client import AsyncYTDLP
from async_yt_dlp.options import YTDLPOptions
from async_yt_dlp.progress import ProgressBridge


@pytest.fixture
def sample_video_info() -> dict[str, Any]:
    """Словарь реалистичных метаданных отдельного видео от yt-dlp."""
    return {
        "id": "BaW_jenozKc",
        "title": "youtube-dl test video",
        "description": "Test video description",
        "duration": 10.5,
        "uploader": "Philipp Hagemeister",
        "uploader_id": "phihag",
        "channel": "Philipp Hagemeister",
        "channel_id": "UC_channel_123",
        "channel_url": "https://www.youtube.com/channel/UC_channel_123",
        "webpage_url": "https://www.youtube.com/watch?v=BaW_jenozKc",
        "thumbnail": "https://i.ytimg.com/vi/BaW_jenozKc/default.jpg",
        "ext": "mp4",
        "filesize": 154820,
        "upload_date": "20121002",
        "view_count": 42000,
        "like_count": 1337,
        "live_status": "not_live",
        "age_limit": 0,
        "categories": ["Science & Technology"],
        "tags": ["youtube-dl", "test"],
        "_type": "video",
        "formats": [
            {
                "format_id": "18",
                "ext": "mp4",
                "width": 640,
                "height": 360,
                "fps": 25.0,
                "vcodec": "avc1.42001E",
                "acodec": "mp4a.40.2",
                "filesize": 154820,
                "tbr": 450.0,
                "vbr": 350.0,
                "abr": 100.0,
                "asr": 44100,
                "format_note": "360p",
                "protocol": "https",
                "resolution": "640x360",
            },
            {
                "format_id": "137",
                "ext": "mp4",
                "width": 1920,
                "height": 1080,
                "fps": 25.0,
                "vcodec": "avc1.640028",
                "acodec": "none",
                "filesize": 1050000,
                "tbr": 2500.0,
                "vbr": 2500.0,
                "abr": None,
                "asr": None,
                "format_note": "1080p",
                "protocol": "https",
            },
            {
                "format_id": "140",
                "ext": "m4a",
                "width": None,
                "height": None,
                "fps": None,
                "vcodec": "none",
                "acodec": "mp4a.40.2",
                "filesize": 85000,
                "tbr": 128.0,
                "vbr": None,
                "abr": 128.0,
                "asr": 44100,
                "format_note": "medium",
                "protocol": "https",
            },
        ],
        "subtitles": {
            "en": [{"ext": "vtt", "url": "https://example.com/en.vtt", "name": "English"}],
            "ru": [{"ext": "vtt", "url": "https://example.com/ru.vtt", "name": "Russian"}],
        },
        "thumbnails": [
            {
                "url": "https://i.ytimg.com/vi/BaW_jenozKc/default.jpg",
                "width": 120,
                "height": 90,
                "id": "0",
            },
            {
                "url": "https://i.ytimg.com/vi/BaW_jenozKc/hqdefault.jpg",
                "width": 480,
                "height": 360,
                "id": "1",
            },
        ],
        "filepath": "/downloads/youtube-dl test video [BaW_jenozKc].mp4",
    }


@pytest.fixture
def sample_playlist_info(sample_video_info: dict[str, Any]) -> dict[str, Any]:
    """Словарь метаданных плейлиста от yt-dlp."""
    video2 = dict(sample_video_info)
    video2["id"] = "second_video_id"
    video2["title"] = "Second test video"

    return {
        "id": "PL_test_playlist_123",
        "title": "Test Playlist",
        "description": "Playlist description",
        "_type": "playlist",
        "webpage_url": "https://www.youtube.com/playlist?list=PL_test_playlist_123",
        "playlist_count": 2,
        "entries": [sample_video_info, video2],
    }


class FakeBackend:
    """Мок-бэкенд для быстрых юнит-тестов клиента и менеджера без обращения к yt-dlp."""

    def __init__(self, return_info: Mapping[str, object] | None = None, delay: float = 0.0) -> None:
        self.return_info = dict(return_info) if return_info is not None else None
        self.delay = delay
        self.extract_calls: list[dict[str, object]] = []
        self.download_calls: list[dict[str, object]] = []
        self.is_closed = False

    async def extract_info(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        download: bool = False,
        extra_info: Mapping[str, object] | None = None,
        job_id: str | None = None,
    ) -> dict[str, object]:
        self.extract_calls.append(
            {
                "url": url,
                "params": params,
                "download": download,
                "extra_info": extra_info,
                "job_id": job_id,
            }
        )
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return self.return_info or {"id": "mock_id", "title": "Mock Title", "ext": "mp4"}

    async def download(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        progress_bridge: ProgressBridge | None = None,
        extra_info: Mapping[str, object] | None = None,
        job_id: str | None = None,
    ) -> tuple[dict[str, object], float]:
        self.download_calls.append(
            {
                "url": url,
                "params": params,
                "extra_info": extra_info,
                "job_id": job_id,
            }
        )
        if progress_bridge:
            progress_bridge.sync_hook(
                {
                    "status": "downloading",
                    "downloaded_bytes": 500,
                    "total_bytes": 1000,
                    "speed": 100.0,
                    "eta": 5.0,
                }
            )
            progress_bridge.sync_hook(
                {
                    "status": "finished",
                    "downloaded_bytes": 1000,
                    "total_bytes": 1000,
                }
            )
            progress_bridge.sync_postprocessor_hook(
                {
                    "status": "finished",
                    "postprocessor": "Fixup",
                }
            )
            progress_bridge.finish()

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        info = self.return_info or {
            "id": "mock_id",
            "title": "Mock Title",
            "ext": "mp4",
            "filepath": "mock_file.mp4",
        }
        return info, 0.25

    async def close(self) -> None:
        self.is_closed = True


@pytest.fixture
def fake_backend(sample_video_info: dict[str, Any]) -> FakeBackend:
    return FakeBackend(return_info=sample_video_info)


@pytest.fixture
def client_with_fake(fake_backend: FakeBackend) -> AsyncYTDLP:
    return AsyncYTDLP(
        max_concurrency=2,
        queue_size=10,
        default_options=YTDLPOptions(format="bestvideo+bestaudio/best"),
        backend=fake_backend,
    )
