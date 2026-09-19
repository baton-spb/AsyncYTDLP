"""Юнит-тесты для ThreadBackend и интеграции с yt-dlp в режиме симуляции."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from async_yt_dlp.backend import ThreadBackend
from async_yt_dlp.exceptions import ExtractionError
from async_yt_dlp.progress import ProgressBridge


@pytest.mark.asyncio
async def test_thread_backend_extract_mocked():
    backend = ThreadBackend()

    mock_info = {"id": "test_123", "title": "Test Mock Video", "ext": "mp4"}

    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_instance.__enter__.return_value = mock_instance
        mock_ydl_cls.return_value = mock_instance

        res = await backend.extract_info(
            "https://www.youtube.com/watch?v=test_123",
            params={"quiet": True},
            job_id="job-abc",
        )

        assert res["id"] == "test_123"
        assert res["title"] == "Test Mock Video"
        mock_instance.extract_info.assert_called_once()

    await backend.close()


@pytest.mark.asyncio
async def test_thread_backend_download_mocked():
    backend = ThreadBackend()
    mock_info = {
        "id": "dl_123",
        "title": "Downloaded Video",
        "filepath": "/tmp/dl_123.mp4",
    }

    loop = asyncio.get_running_loop()
    bridge = ProgressBridge(loop)

    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = mock_info
        mock_instance.__enter__.return_value = mock_instance
        mock_ydl_cls.return_value = mock_instance

        res, elapsed = await backend.download(
            "https://www.youtube.com/watch?v=dl_123",
            params={"quiet": True},
            progress_bridge=bridge,
            job_id="job-dl",
        )

        assert res["id"] == "dl_123"
        assert elapsed >= 0.0
        mock_instance.extract_info.assert_called_once()

    await backend.close()


@pytest.mark.asyncio
async def test_thread_backend_extract_error_mapping():
    backend = ThreadBackend()

    with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_instance = MagicMock()
        from yt_dlp.utils import ExtractorError

        mock_instance.extract_info.side_effect = ExtractorError("Unavailable video")
        mock_instance.__enter__.return_value = mock_instance
        mock_ydl_cls.return_value = mock_instance

        with pytest.raises(ExtractionError, match="Unavailable video"):
            await backend.extract_info(
                "https://www.youtube.com/watch?v=err",
                params={},
                job_id="job-err",
            )

    await backend.close()


@pytest.mark.asyncio
async def test_thread_backend_closed_raises():
    backend = ThreadBackend()
    await backend.close()

    with pytest.raises(RuntimeError, match="закрыт"):
        await backend.extract_info("https://test.com", params={})

    with pytest.raises(RuntimeError, match="закрыт"):
        await backend.download("https://test.com", params={})
