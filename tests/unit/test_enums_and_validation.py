"""Модульные тесты для перечислений (enums) и валидации параметров в AsyncYT-DLP."""

from __future__ import annotations

import pytest

from async_yt_dlp.enums import (
    AudioCodec,
    AudioFormat,
    Resolution,
    VideoCodec,
    VideoContainer,
)
from async_yt_dlp.options import YTDLPOptions
from async_yt_dlp.postprocess import CompressToSize, PostDownloadPipeline


def test_enums_string_values() -> None:
    """Проверяет строковые значения перечислений."""
    assert AudioFormat.MP3 == "mp3"
    assert AudioFormat.FLAC == "flac"
    assert AudioFormat.BEST == "best"

    assert VideoContainer.MP4 == "mp4"
    assert VideoContainer.MKV == "mkv"
    assert VideoContainer.WEBM == "webm"

    assert VideoCodec.H264 == "libx264"
    assert VideoCodec.H265 == "libx265"
    assert VideoCodec.COPY == "copy"

    assert AudioCodec.AAC == "aac"
    assert AudioCodec.MP3 == "libmp3lame"
    assert AudioCodec.COPY == "copy"

    assert Resolution.HD_720P == (1280, 720)
    assert Resolution.FHD_1080P == (1920, 1080)
    assert Resolution.UHD_4K == (3840, 2160)


def test_ytdlp_options_with_enums() -> None:
    """Проверяет генерацию словаря параметров YoutubeDL с использованием перечислений."""
    opts = YTDLPOptions(
        extract_audio=True,
        audio_format=AudioFormat.MP3,
        audio_quality=2,
        remux_video=VideoContainer.MKV,
        retries=3,
        socket_timeout=15.0,
        rate_limit=500_000,
    )
    params = opts.to_ytdlp_params()

    assert params["retries"] == 3
    assert params["socket_timeout"] == 15.0
    assert params["ratelimit"] == 500_000

    pps = params.get("postprocessors")
    assert isinstance(pps, list)
    audio_pp = next((p for p in pps if p.get("key") == "FFmpegExtractAudio"), None)
    assert audio_pp is not None
    assert audio_pp["preferredcodec"] == "mp3"
    assert audio_pp["preferredquality"] == "2"

    remux_pp = next((p for p in pps if p.get("key") == "FFmpegVideoRemuxer"), None)
    assert remux_pp is not None
    assert remux_pp["preferedformat"] == "mkv"


def test_ytdlp_options_range_validation() -> None:
    """Проверяет валидацию некорректных числовых диапазонов в YTDLPOptions."""
    with pytest.raises(ValueError, match="socket_timeout должен быть > 0"):
        YTDLPOptions(socket_timeout=0)

    with pytest.raises(ValueError, match="socket_timeout должен быть > 0"):
        YTDLPOptions(socket_timeout=-1.5)

    with pytest.raises(ValueError, match="retries должен быть >= 0"):
        YTDLPOptions(retries=-1)

    with pytest.raises(ValueError, match="fragment_retries должен быть >= 0"):
        YTDLPOptions(fragment_retries=-5)

    with pytest.raises(ValueError, match="extractor_retries должен быть >= 0"):
        YTDLPOptions(extractor_retries=-2)

    with pytest.raises(ValueError, match="file_access_retries должен быть >= 0"):
        YTDLPOptions(file_access_retries=-1)

    with pytest.raises(ValueError, match="rate_limit должен быть > 0"):
        YTDLPOptions(rate_limit=0)

    with pytest.raises(ValueError, match="throttled_rate_limit должен быть > 0"):
        YTDLPOptions(throttled_rate_limit=-100)

    with pytest.raises(ValueError, match="concurrent_fragments должен быть >= 1"):
        YTDLPOptions(concurrent_fragments=0)

    with pytest.raises(ValueError, match=r"audio_quality.*от 0 до 10"):
        YTDLPOptions(audio_quality=11)

    with pytest.raises(ValueError, match=r"audio_quality.*от 0 до 10"):
        YTDLPOptions(audio_quality=-1)


def test_compress_to_size_validation() -> None:
    """Проверяет валидацию параметров в CompressToSize."""
    with pytest.raises(ValueError, match="target_size_mb должен быть > 0"):
        CompressToSize(target_size_mb=0)

    with pytest.raises(ValueError, match="target_size_mb должен быть > 0"):
        CompressToSize(target_size_mb=-10.0)

    with pytest.raises(ValueError, match="audio_bitrate_kbps должен быть > 0"):
        CompressToSize(target_size_mb=50, audio_bitrate_kbps=0)

    # Корректные параметры
    compressor = CompressToSize(
        target_size_mb=25,
        video_codec=VideoCodec.H265,
        audio_codec=AudioCodec.OPUS,
    )
    assert compressor.target_size_mb == 25
    assert compressor.video_codec == VideoCodec.H265
    assert compressor.audio_codec == AudioCodec.OPUS


def test_post_download_pipeline_scale_presets() -> None:
    """Проверяет масштабирование в PostDownloadPipeline с пресетами Resolution."""
    pipeline = PostDownloadPipeline()
    pipeline.scale(Resolution.HD_720P)
    assert pipeline._scale_dims == (1280, 720)

    pipeline.scale(1920, 1080)
    assert pipeline._scale_dims == (1920, 1080)

    with pytest.raises(ValueError, match="Размеры кадра должны быть строго положительными"):
        pipeline.scale(0, 1080)

    with pytest.raises(ValueError, match="Размеры кадра должны быть строго положительными"):
        pipeline.scale(-100, 200)

    with pytest.raises(ValueError, match="Необходимо указать высоту"):
        pipeline.scale(1920)  # type: ignore[call-overload]


def test_post_download_pipeline_validation() -> None:
    """Проверяет валидацию диапазонов в методах PostDownloadPipeline."""
    pipeline = PostDownloadPipeline()

    # CRF валидация
    pipeline.video_codec(VideoCodec.H264, crf=0)
    assert pipeline._crf == 0
    pipeline.video_codec(VideoCodec.H265, crf=51)
    assert pipeline._crf == 51

    with pytest.raises(ValueError, match="crf должен быть в диапазоне от 0 до 51"):
        pipeline.video_codec(crf=-1)

    with pytest.raises(ValueError, match="crf должен быть в диапазоне от 0 до 51"):
        pipeline.video_codec(crf=52)

    # Trim валидация
    with pytest.raises(ValueError, match="start должен быть >= 0"):
        pipeline.trim(start=-1.0)

    with pytest.raises(ValueError, match="duration должен быть > 0"):
        pipeline.trim(duration=0)

    with pytest.raises(ValueError, match=r"end.*должна быть больше начальной start"):
        pipeline.trim(start=10.0, end=5.0)

    # Compress to size
    with pytest.raises(ValueError, match="target_size_mb должен быть > 0"):
        pipeline.compress_to_size(0)

    pipeline.compress_to_size(50.0)
    assert pipeline._compress_target_mb == 50.0

    # Remux
    pipeline.remux(VideoContainer.MKV)
    assert pipeline._remux_ext == "mkv"

    # Extract audio
    pipeline.extract_audio(AudioFormat.FLAC, bitrate="320k")
    assert pipeline._audio_codec == "flac"
    assert pipeline._audio_bitrate == "320k"
