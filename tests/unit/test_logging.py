"""Юнит-тесты для модуля _logging.py (YTDLPLoggerAdapter и санитизация)."""

import logging

from async_yt_dlp._logging import YTDLPLoggerAdapter, redact_options, redact_url


def test_redact_url():
    url_with_creds = "https://admin:supersecret@myproxy.internal:8080/stream"
    redacted = redact_url(url_with_creds)

    assert "supersecret" not in redacted
    assert "admin:********@myproxy.internal" in redacted

    # Обычный URL без учетных данных не изменяется
    normal_url = "https://youtube.com/watch?v=123"
    assert redact_url(normal_url) == normal_url


def test_redact_options_sensitive_keys():
    opts = {
        "password": "secret_password",
        "videopassword": "secret_video_password",
        "username": "bot_user",
        "proxy": "http://user:pass@proxy.example.com:3128",
        "cookiefile": "/secure/tokens/cookies.txt",
        "format": "best",
    }
    redacted = redact_options(opts)

    assert redacted["password"] == "********"
    assert redacted["videopassword"] == "********"
    assert redacted["username"] == "********"
    assert redacted["cookiefile"] == "********"
    assert "pass" not in redacted["proxy"]
    assert redacted["format"] == "best"


def test_redact_options_nested_headers():
    opts = {
        "http_headers": {
            "Authorization": "Bearer secret_jwt_token",
            "Cookie": "session=secret_session_id",
            "User-Agent": "Mozilla/5.0",
        }
    }
    redacted = redact_options(opts)

    headers = redacted["http_headers"]
    assert headers["Authorization"] == "********"
    assert headers["Cookie"] == "********"
    assert headers["User-Agent"] == "Mozilla/5.0"


def test_ytdlp_logger_adapter():
    records: list[tuple[str, str]] = []

    class MockHandler(logging.Handler):
        def emit(self, record: logging.LogRecord):
            records.append((record.levelname, record.getMessage()))

    test_logger = logging.getLogger("test_adapter_logger")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(MockHandler())

    adapter = YTDLPLoggerAdapter(test_logger)

    # [debug] prefix should route to debug
    adapter.debug("[debug] FFmpeg version 6.0")
    # normal string in debug should route to info
    adapter.debug("[download] Destination: video.mp4")
    adapter.warning("Deprecated extractor option")
    adapter.error("Failed to connect")

    assert ("DEBUG", "FFmpeg version 6.0") in records
    assert ("INFO", "[download] Destination: video.mp4") in records
    assert ("WARNING", "Deprecated extractor option") in records
    assert ("ERROR", "Failed to connect") in records


def test_ytdlp_logger_adapter_no_warnings():
    records: list[tuple[str, str]] = []

    class MockHandler(logging.Handler):
        def emit(self, record: logging.LogRecord):
            records.append((record.levelname, record.getMessage()))

    test_logger = logging.getLogger("test_adapter_no_warnings_logger")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(MockHandler())

    adapter = YTDLPLoggerAdapter(test_logger, no_warnings=True)
    adapter.warning("Some warning message")

    assert ("WARNING", "Some warning message") not in records
    assert any(level == "DEBUG" and "Some warning message" in msg for level, msg in records)
