"""Юнит-тесты для модуля exceptions.py."""

from async_yt_dlp.exceptions import (
    AsyncYTDLPError,
    CancellationError,
    DownloadError,
    ExtractionError,
    OperationTimeoutError,
    PostProcessingError,
    map_ytdlp_error,
)


class MockExtractorError(Exception):
    """Имитация ExtractorError из yt_dlp."""


class MockDownloadError(Exception):
    """Имитация DownloadError из yt_dlp."""


class MockPostProcessingError(Exception):
    """Имитация PostProcessingError из yt_dlp."""


class MockDownloadCancelled(Exception):  # noqa: N818
    """Имитация DownloadCancelled из yt_dlp."""


def test_exception_context_fields():
    err = AsyncYTDLPError("Download failed", url="https://example.com/v", job_id="job-123")

    assert err.url == "https://example.com/v"
    assert err.job_id == "job-123"
    assert "[url=https://example.com/v]" in str(err)
    assert "[job_id=job-123]" in str(err)


def test_map_ytdlp_error_extractor():
    raw_err = MockExtractorError("Video unavailable: 404")
    mapped = map_ytdlp_error(raw_err, url="https://youtube.com/watch?v=123", job_id="job-1")

    assert isinstance(mapped, ExtractionError)
    assert mapped.url == "https://youtube.com/watch?v=123"
    assert mapped.job_id == "job-1"
    assert mapped.__cause__ is raw_err
    assert "Video unavailable: 404" in str(mapped)


def test_map_ytdlp_error_download():
    raw_err = MockDownloadError("Connection reset by peer")
    mapped = map_ytdlp_error(raw_err, url="https://test.com")

    assert isinstance(mapped, DownloadError)
    assert mapped.__cause__ is raw_err


def test_map_ytdlp_error_postprocessing():
    raw_err = MockPostProcessingError("ffmpeg returned error code 1")
    mapped = map_ytdlp_error(raw_err)

    assert isinstance(mapped, PostProcessingError)
    assert mapped.__cause__ is raw_err


def test_map_ytdlp_error_cancellation():
    raw_err = MockDownloadCancelled("User abort")
    mapped = map_ytdlp_error(raw_err)

    assert isinstance(mapped, CancellationError)
    assert mapped.__cause__ is raw_err


def test_map_ytdlp_error_timeout():
    raw_err = TimeoutError("Timed out waiting for socket")
    mapped = map_ytdlp_error(raw_err)

    assert isinstance(mapped, OperationTimeoutError)
    assert mapped.__cause__ is raw_err


def test_map_already_mapped_error():
    existing = ExtractionError("Already mapped", url="https://orig.url", job_id="id-1")
    mapped = map_ytdlp_error(existing, url="https://new.url")

    # Исходный контекст сохраняется
    assert mapped is existing
    assert mapped.url == "https://orig.url"
