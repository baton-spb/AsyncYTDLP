"""Юнит-тесты для интеграции поиска внешних бинарников через async-ffmpeg."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from async_yt_dlp._dependencies import DependencyInfo, check_dependencies


def test_dependency_info_has_async_ffmpeg() -> None:
    """Проверяет поле has_async_ffmpeg в DependencyInfo."""
    info = DependencyInfo(
        ytdlp_version="2024.08.01",
        ffmpeg_available=True,
        ffprobe_available=True,
        has_async_ffmpeg=True,
    )
    assert info.has_async_ffmpeg is True
    assert info.has_ffmpeg_suite is True


def test_check_dependencies_delegates_to_async_ffmpeg() -> None:
    """Проверяет, что check_dependencies обращается к async_ffmpeg при его наличии."""
    mock_ffmpeg_path = Path("/mock/bin/ffmpeg")
    mock_ffprobe_path = Path("/mock/bin/ffprobe")

    with (
        patch("importlib.util.find_spec") as mock_find_spec,
        patch("async_ffmpeg.find_ffmpeg", return_value=mock_ffmpeg_path, create=True),
        patch("async_ffmpeg.find_ffprobe", return_value=mock_ffprobe_path, create=True),
        patch(
            "async_ffmpeg.get_binary_version_sync",
            return_value="ffmpeg version 7.1-custom",
            create=True,
        ),
        patch.object(Path, "is_file", return_value=True),
    ):
        mock_find_spec.side_effect = lambda mod: MagicMock() if mod == "async_ffmpeg" else None

        info = check_dependencies(force_refresh=True)
        assert info.has_async_ffmpeg is True
        assert info.ffmpeg_available is True
        assert info.ffmpeg_path == mock_ffmpeg_path
        assert info.ffmpeg_version == "ffmpeg version 7.1-custom"
