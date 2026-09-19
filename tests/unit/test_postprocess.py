"""Юнит-тесты для модуля postprocess (PostDownloadPipeline, CompressToSize)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from async_yt_dlp.exceptions import DependencyError, PostProcessingError
from async_yt_dlp.models import DownloadResult, MediaInfo
from async_yt_dlp.postprocess import (
    CompressToSize,
    PostDownloadPipeline,
    PostProcessResult,
    _require_async_ffmpeg,
)


def _create_mock_download_result(filepath: Path, duration: float = 60.0) -> DownloadResult:
    """Создает тестовый объект DownloadResult."""
    media_info = MediaInfo(
        id="test_id",
        title="Test Video Title",
        duration=duration,
        ext="mp4",
        raw_data={},
    )
    return DownloadResult(
        filepath=filepath,
        info=media_info,
        elapsed=1.5,
    )


def test_require_async_ffmpeg_error() -> None:
    """Проверяет выброс DependencyError, если async_ffmpeg отсутствует в системе."""
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(DependencyError, match="требуется установить пакет async-ffmpeg"),
    ):
        _require_async_ffmpeg()


@pytest.mark.asyncio
async def test_compress_to_size_calculation(tmp_path: Path) -> None:
    """Проверяет расчет битрейта и вызов two_pass_transcode в CompressToSize."""
    video_file = tmp_path / "video.mp4"
    video_file.write_bytes(b"dummy")

    download_res = _create_mock_download_result(video_file, duration=100.0)

    # 50 MB за 100 секунд:
    # safe_target_bytes = 50 * 1024 * 1024 * 0.97 = 50,855,936 байт
    # total_bits = 406,847,488 бит
    # total_bps = 4,068,474.88 бит/с (~4068 kbps)
    # audio_bps = 128,000 бит/с
    # video_bps = 3,940,474.88 бит/с (~3940 kbps)
    compressor = CompressToSize(target_size_mb=50.0, audio_bitrate_kbps=128)

    mock_client = MagicMock()
    mock_process_res = MagicMock(success=True, returncode=0, stderr="", duration_seconds=100.0)
    mock_client.two_pass_transcode = AsyncMock(return_value=mock_process_res)

    res = await compressor.run(download_res, client=mock_client)

    assert isinstance(res, PostProcessResult)
    assert res.success is True
    assert res.duration_seconds == 100.0
    mock_client.two_pass_transcode.assert_awaited_once()

    # Проверяем аргументы вызова
    call_kwargs = mock_client.two_pass_transcode.await_args.kwargs
    assert call_kwargs["video_codec"] == "libx264"
    assert call_kwargs["audio_bitrate"] == "128k"
    # Расчетный битрейт должен быть около 3940k
    assert "k" in call_kwargs["bitrate"]
    bitrate_val = int(call_kwargs["bitrate"].rstrip("k"))
    assert 3800 <= bitrate_val <= 4100


@pytest.mark.asyncio
async def test_compress_to_size_missing_file(tmp_path: Path) -> None:
    """Проверяет выброс ошибки при отсутствии исходного файла."""
    missing_file = tmp_path / "nonexistent.mp4"
    compressor = CompressToSize(target_size_mb=25.0)

    with pytest.raises(PostProcessingError, match="Исходный файл для сжатия не найден"):
        await compressor.run(missing_file)


@pytest.mark.asyncio
async def test_pipeline_extract_audio(tmp_path: Path) -> None:
    """Проверяет работу режима извлечения аудио в PostDownloadPipeline."""
    video_file = tmp_path / "song.mp4"
    video_file.write_bytes(b"dummy")

    download_res = _create_mock_download_result(video_file, duration=180.0)

    mock_client = MagicMock()
    mock_proc_res = MagicMock(success=True, returncode=0, stderr="", duration_seconds=180.0)
    mock_client.extract_audio = AsyncMock(return_value=mock_proc_res)

    pipeline = PostDownloadPipeline(client=mock_client).extract_audio(codec="mp3", bitrate="320k")
    res = await pipeline.run(download_res)

    assert isinstance(res, PostProcessResult)
    assert res.output.suffix == ".mp3"
    mock_client.extract_audio.assert_awaited_once_with(
        input=video_file,
        output=tmp_path / "song.mp3",
        codec="mp3",
        bitrate="320k",
        on_progress=None,
    )


@pytest.mark.asyncio
async def test_pipeline_remux(tmp_path: Path) -> None:
    """Проверяет вызов convert при установке remux без фильтров."""
    video_file = tmp_path / "source.mkv"
    video_file.write_bytes(b"dummy")

    mock_client = MagicMock()
    mock_proc_res = MagicMock(success=True, returncode=0, stderr="", duration_seconds=50.0)
    mock_client.convert = AsyncMock(return_value=mock_proc_res)

    pipeline = PostDownloadPipeline(client=mock_client).remux("mp4")
    res = await pipeline.run(video_file)

    assert isinstance(res, PostProcessResult)
    assert res.output.suffix == ".mp4"
    mock_client.convert.assert_awaited_once_with(
        input=video_file,
        output=tmp_path / "source_remux.mp4",
        copy=True,
        on_progress=None,
    )


@pytest.mark.asyncio
async def test_pipeline_complex_filters(tmp_path: Path) -> None:
    """Проверяет конфигурирование MediaPipeline при указании комплексных шагов (scale + loudnorm)."""
    video_file = tmp_path / "video.mp4"
    video_file.write_bytes(b"dummy")

    mock_client = MagicMock()
    mock_pipe = MagicMock()
    mock_proc_res = MagicMock(success=True, returncode=0, stderr="", duration_seconds=12.0)
    mock_pipe.run = AsyncMock(return_value=mock_proc_res)
    mock_client.pipeline.return_value = mock_pipe

    pipeline = (
        PostDownloadPipeline(client=mock_client)
        .scale(1280, 720)
        .normalize_audio(-14.0)
        .video_codec("libx264", crf=22, preset="fast")
        .audio_codec("aac", bitrate="192k")
    )
    res = await pipeline.run(video_file)

    assert isinstance(res, PostProcessResult)
    mock_client.pipeline.assert_called_once_with(video_file)
    mock_pipe.scale.assert_called_once_with(1280, 720)
    mock_pipe.normalize_audio.assert_called_once_with(target_lufs=-14.0)
    mock_pipe.video_codec.assert_called_once_with("libx264", crf=22, preset="fast")
    mock_pipe.audio_codec.assert_called_once_with("aac", bitrate="192k")
    mock_pipe.run.assert_awaited_once()
