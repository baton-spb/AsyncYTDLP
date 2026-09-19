"""Юнит-тесты для модуля models.py (MediaInfo, FormatInfo, DownloadResult и др.)."""

from pathlib import Path
from typing import Any

from async_yt_dlp.models import DownloadResult, MediaInfo


def test_media_info_from_ytdlp(sample_video_info: dict[str, Any]):
    info = MediaInfo.from_ytdlp(sample_video_info)

    assert info.id == "BaW_jenozKc"
    assert info.title == "youtube-dl test video"
    assert info.duration == 10.5
    assert info.duration_seconds == 10
    assert info.uploader == "Philipp Hagemeister"
    assert info.webpage_url == "https://www.youtube.com/watch?v=BaW_jenozKc"
    assert info.ext == "mp4"
    assert info.filesize == 154820
    assert not info.is_playlist
    assert info.entries is None
    assert len(info.formats) == 3
    assert len(info.thumbnails) == 2
    assert "en" in info.subtitles
    assert "ru" in info.subtitles


def test_format_info_attributes(sample_video_info: dict[str, Any]):
    info = MediaInfo.from_ytdlp(sample_video_info)

    fmt_18 = next(f for f in info.formats if f.format_id == "18")
    assert fmt_18.width == 640
    assert fmt_18.height == 720 or fmt_18.height == 360
    assert fmt_18.vcodec == "avc1.42001E"
    assert fmt_18.acodec == "mp4a.40.2"
    assert fmt_18.has_video is True
    assert fmt_18.has_audio is True

    fmt_137 = next(f for f in info.formats if f.format_id == "137")
    assert fmt_137.has_video is True
    assert fmt_137.has_audio is False  # acodec == 'none'

    fmt_140 = next(f for f in info.formats if f.format_id == "140")
    assert fmt_140.has_video is False  # vcodec == 'none'
    assert fmt_140.has_audio is True


def test_playlist_media_info(sample_playlist_info: dict[str, Any]):
    info = MediaInfo.from_ytdlp(sample_playlist_info)

    assert info.is_playlist is True
    assert info.title == "Test Playlist"
    assert info.playlist_count == 2
    assert info.entries is not None
    assert len(info.entries) == 2
    assert info.entries[0].id == "BaW_jenozKc"
    assert info.entries[1].id == "second_video_id"


def test_to_dict_serialization(sample_video_info: dict[str, Any]):
    info = MediaInfo.from_ytdlp(sample_video_info)
    serialized = info.to_dict()

    assert isinstance(serialized, dict)
    assert serialized.get("id") == "BaW_jenozKc"
    assert serialized.get("title") == "youtube-dl test video"


def test_download_result_properties(tmp_path: Path, sample_video_info: dict[str, Any]):
    test_file = tmp_path / "video.mp4"
    test_file.write_bytes(b"test video binary content")

    info = MediaInfo.from_ytdlp(sample_video_info)
    res = DownloadResult(
        filepath=test_file,
        info=info,
        elapsed=1.25,
        requested_formats=info.formats[:1],
    )

    assert res.filename == "video.mp4"
    assert res.exists is True
    assert res.file_size == len(b"test video binary content")
    assert res.elapsed == 1.25
