"""Юнит-тесты для построителя выражений выбора формата FormatSelector."""

from __future__ import annotations

import pytest

from async_yt_dlp.format import FormatSelector
from async_yt_dlp.options import YTDLPOptions


def test_custom_format_selector() -> None:
    """Проверяет создание селектора из сырой строки."""
    sel = FormatSelector.custom("bv*[height<=720]+ba/b")
    assert str(sel) == "bv*[height<=720]+ba/b"
    assert sel.build() == "bv*[height<=720]+ba/b"
    assert "FormatSelector('bv*[height<=720]+ba/b')" in repr(sel)


def test_custom_selector_cannot_add_filters() -> None:
    """Проверяет, что добавление фильтров к кастомному выражению вызывает ошибку."""
    sel = FormatSelector.custom("bv*")
    with pytest.raises(ValueError, match="Невозможно добавлять фильтры"):
        sel.max_height(1080)


def test_fluent_builder_filters() -> None:
    """Проверяет построение фильтров по высоте, fps, расширению и кодекам."""
    sel = (
        FormatSelector.video()
        .max_height(1080)
        .min_height(720)
        .max_fps(60)
        .ext("mp4")
        .vcodec("avc", prefix=True)
        .max_filesize("100M")
    )
    res = sel.build()
    assert res.startswith("bestvideo*")
    assert "[height<=1080]" in res
    assert "[height>=720]" in res
    assert "[fps<=60]" in res
    assert "[ext=mp4]" in res
    assert "[vcodec^=avc]" in res
    assert "[filesize<=100M]" in res


def test_exact_height_and_audio_codec() -> None:
    """Проверяет фильтры точной высоты и аудиокодека."""
    sel = FormatSelector.audio().acodec("opus", prefix=False).filter("abr>=128")
    res = sel.build()
    assert res == "bestaudio*[acodec=opus][abr>=128]"

    exact_sel = FormatSelector.any_stream().exact_height(720).max_filesize(5000000)
    assert exact_sel.build() == "best[height=720][filesize<=5000000B]"


def test_merge_and_fallback_operators() -> None:
    """Проверяет операторы `+` и `/`."""
    video = FormatSelector.video().max_height(1080)
    audio = FormatSelector.audio()
    fallback = FormatSelector.any_stream()

    combined = (video + audio) / fallback
    assert str(combined) == "bestvideo*[height<=1080]+bestaudio*/best"


def test_presets() -> None:
    """Проверяет корректность генерации строк для встроенных пресетов."""
    p_1080 = FormatSelector.preset_1080p()
    assert "bestvideo*[height<=1080]+bestaudio*" in str(p_1080)
    assert "/best[height<=1080]/best" in str(p_1080)

    p_720 = FormatSelector.preset_720p()
    assert "bestvideo*[height<=720]+bestaudio*" in str(p_720)

    p_audio = FormatSelector.preset_audio_only("mp3")
    assert "bestaudio*[ext=mp3]" in str(p_audio)

    p_compat = FormatSelector.preset_compatibility()
    assert "vcodec^=avc" in str(p_compat)
    assert "acodec^=mp4a" in str(p_compat)

    p_tg = FormatSelector.preset_telegram(max_size_mb=30)
    assert "filesize<=30M" in str(p_tg)

    p_max = FormatSelector.preset_max_quality()
    assert str(p_max) == "bestvideo*+bestaudio*/best"

    # Проверка новых пресетов всех стандартных разрешений
    p_144 = FormatSelector.preset_144p()
    assert "height<=144" in str(p_144)

    p_240 = FormatSelector.preset_240p()
    assert "height<=240" in str(p_240)

    p_360 = FormatSelector.preset_360p()
    assert "height<=360" in str(p_360)

    p_480 = FormatSelector.preset_480p()
    assert "height<=480" in str(p_480)

    p_2k = FormatSelector.preset_2k()
    assert "height<=1440" in str(p_2k)

    p_4k = FormatSelector.preset_4k("mp4", fps=60)
    assert "height<=2160" in str(p_4k)
    assert "fps<=60" in str(p_4k)
    assert "ext=mp4" in str(p_4k)

    p_8k = FormatSelector.preset_8k()
    assert "height<=4320" in str(p_8k)

    p_best_a = FormatSelector.preset_best_audio()
    assert "bestaudio*/best" in str(p_best_a)

    p_worst = FormatSelector.preset_worst("mp4")
    assert "worst[ext=mp4]/worst" in str(p_worst)


def test_resolution_factory_exact() -> None:
    """Проверяет работу фабрики resolution с exact=True."""
    res_sel = FormatSelector.resolution(720, exact=True)
    assert "height=720" in str(res_sel)
    assert "height<=720" not in str(res_sel)


def test_options_format_selector_integration() -> None:
    """Проверяет прозрачную передачу FormatSelector в YTDLPOptions."""
    selector = FormatSelector.preset_720p()
    opts = YTDLPOptions(format=selector)

    params = opts.to_ytdlp_params()
    assert params["format"] == str(selector)

