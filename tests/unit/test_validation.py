"""Юнит-тесты для модуля _validation.py."""

from pathlib import Path

import pytest

from async_yt_dlp._validation import validate_path, validate_url
from async_yt_dlp.exceptions import ValidationError


def test_validate_url_valid_schemes():
    assert (
        validate_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        == "https://www.youtube.com/watch?v=BaW_jenozKc"
    )
    assert validate_url("http://example.com/video.mp4") == "http://example.com/video.mp4"
    assert validate_url("ftps://ftp.example.com/stream.mkv") == "ftps://ftp.example.com/stream.mkv"


def test_validate_url_search_prefixes():
    assert validate_url("ytsearch:python asyncio") == "ytsearch:python asyncio"
    assert validate_url("scsearch5:lofi beats") == "scsearch5:lofi beats"


def test_validate_url_file_scheme_protection():
    # По умолчанию file:// запрещен
    with pytest.raises(ValidationError, match="file://"):
        validate_url("file:///etc/passwd")

    # С явным разрешением allow_file_urls=True
    assert (
        validate_url("file:///path/to/local.mp4", allow_file_urls=True)
        == "file:///path/to/local.mp4"
    )


def test_validate_url_invalid_cases():
    with pytest.raises(ValidationError):
        validate_url("")

    with pytest.raises(ValidationError):
        validate_url("   ")

    with pytest.raises(ValidationError):
        validate_url("https://example.com/\x00evil")

    with pytest.raises(ValidationError):
        validate_url("javascript:alert(1)")

    with pytest.raises(ValidationError):
        validate_url(123)  # type: ignore


def test_validate_path(tmp_path: Path):
    valid_dir = tmp_path / "sub"
    res = validate_path(valid_dir, create_dir=True)
    assert res.exists()
    assert res.is_dir()

    with pytest.raises(ValidationError):
        validate_path("")

    with pytest.raises(ValidationError):
        validate_path("/path/with/\x00null")

    with pytest.raises(ValidationError):
        validate_path(tmp_path / "non_existent_file.txt", must_exist=True)
