"""Юнит-тесты для модуля options.py (YTDLPOptions)."""

from pathlib import Path

from async_yt_dlp.options import YTDLPOptions


def test_default_options():
    opts = YTDLPOptions()
    params = opts.to_ytdlp_params()

    assert params["quiet"] is True
    assert params["no_warnings"] is True
    assert params["noprogress"] is True
    assert "format" not in params
    assert params["outtmpl"] == {"default": "%(title)s [%(id)s].%(ext)s"}


def test_typed_options_mapping():
    opts = YTDLPOptions(
        format="bestvideo+bestaudio/best",
        output_template="%(id)s.%(ext)s",
        output_path=Path("/downloads"),
        temp_path=Path("/tmp"),
        retries=5,
        fragment_retries=10,
        proxy="socks5://127.0.0.1:1080",
        cookies_file=Path("/path/to/cookies.txt"),
        username="test_user",
        password="test_password",
        rate_limit=1024000,
        restrict_filenames=True,
    )
    params = opts.to_ytdlp_params()

    assert params["format"] == "bestvideo+bestaudio/best"
    assert params["outtmpl"] == {"default": "%(id)s.%(ext)s"}
    assert params["paths"]["home"] == str(Path("/downloads"))
    assert params["paths"]["temp"] == str(Path("/tmp"))
    assert params["retries"] == 5
    assert params["fragment_retries"] == 10
    assert params["proxy"] == "socks5://127.0.0.1:1080"
    assert params["cookiefile"] == str(Path("/path/to/cookies.txt"))
    assert params["username"] == "test_user"
    assert params["password"] == "test_password"
    assert params["ratelimit"] == 1024000
    assert params["restrictfilenames"] is True


def test_postprocessors_generation():
    opts = YTDLPOptions(
        extract_audio=True,
        audio_format="mp3",
        audio_quality="192K",
        embed_thumbnail=True,
        embed_metadata=True,
        embed_subtitles=True,
        remux_video="mp4",
    )
    params = opts.to_ytdlp_params()
    pps = params.get("postprocessors", [])

    keys = [p["key"] for p in pps]
    assert "FFmpegExtractAudio" in keys
    assert "EmbedThumbnail" in keys
    assert "FFmpegMetadata" in keys
    assert "FFmpegEmbedSubtitle" in keys
    assert "FFmpegVideoRemuxer" in keys

    audio_pp = next(p for p in pps if p["key"] == "FFmpegExtractAudio")
    assert audio_pp["preferredcodec"] == "mp3"
    assert audio_pp["preferredquality"] == "192K"


def test_raw_options_priority():
    opts = YTDLPOptions(
        format="best",
        raw_options={"format": "worst", "future_option": 42},
    )
    params = opts.to_ytdlp_params()

    # raw_options переопределяет typed-параметр
    assert params["format"] == "worst"
    assert params["future_option"] == 42


def test_merge_options():
    base = YTDLPOptions(
        format="best",
        retries=3,
        http_headers={"User-Agent": "Bot/1.0"},
        raw_options={"key1": "val1"},
    )
    override = YTDLPOptions(
        format="bestaudio",
        http_headers={"Authorization": "Bearer token"},
        raw_options={"key2": "val2"},
    )

    merged = base.merge(override)
    params = merged.to_ytdlp_params()

    assert params["format"] == "bestaudio"
    assert params["retries"] == 3
    assert merged.http_headers == {
        "User-Agent": "Bot/1.0",
        "Authorization": "Bearer token",
    }
    assert merged.raw_options == {"key1": "val1", "key2": "val2"}


def test_to_safe_dict_redaction():
    opts = YTDLPOptions(
        username="admin",
        password="super_secret_password",
        proxy="http://user:secret@proxy.org:8080",
        cookies_file=Path("/secrets/cookies.txt"),
    )
    safe = opts.to_safe_dict()

    assert safe["password"] == "********"
    assert safe["username"] == "********"
    assert safe["cookiefile"] == "********"
    assert safe["proxy"] == "http://user:********@proxy.org:8080"


def test_js_runtimes_options():
    # 1. Tuple / List format
    opts = YTDLPOptions(js_runtimes=("deno", "node"))
    params = opts.to_ytdlp_params()
    assert params["js_runtimes"] == {"deno": {}, "node": {}}

    # 2. Dict format
    opts_dict = YTDLPOptions(js_runtimes={"bun": {"path": "/usr/bin/bun"}})
    params_dict = opts_dict.to_ytdlp_params()
    assert params_dict["js_runtimes"] == {"bun": {"path": "/usr/bin/bun"}}

    # 3. Merge
    base = YTDLPOptions(js_runtimes=("deno",))
    override = YTDLPOptions(js_runtimes=("node",))
    merged = base.merge(override)
    assert merged.js_runtimes == ("node",)


def test_auto_detect_js_runtimes():
    from unittest.mock import MagicMock, patch

    mock_dep = MagicMock(js_runtimes=("node",))
    with patch("async_yt_dlp._dependencies.check_dependencies", return_value=mock_dep):
        opts = YTDLPOptions(auto_detect_js=True)
        params = opts.to_ytdlp_params()
        assert params.get("js_runtimes") == {"node": {}}

    with patch("async_yt_dlp._dependencies.check_dependencies", return_value=mock_dep):
        opts_disabled = YTDLPOptions(auto_detect_js=False)
        params_disabled = opts_disabled.to_ytdlp_params()
        assert "js_runtimes" not in params_disabled
