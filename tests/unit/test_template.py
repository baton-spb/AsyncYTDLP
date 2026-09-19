"""Модульные тесты для объектного построителя OutputTemplate и управления контейнерами."""

from __future__ import annotations

from async_yt_dlp.enums import VideoContainer
from async_yt_dlp.format import FormatSelector
from async_yt_dlp.options import YTDLPOptions
from async_yt_dlp.template import OutputTemplate


def test_output_template_presets() -> None:
    """Проверяет строковые представления готовых пресетов OutputTemplate."""
    assert str(OutputTemplate.title_only()) == "%(title)s.%(ext)s"
    assert str(OutputTemplate.title_and_id()) == "%(title)s [%(id)s].%(ext)s"
    assert str(OutputTemplate.default()) == "%(title)s [%(id)s].%(ext)s"
    assert str(OutputTemplate.id_only()) == "%(id)s.%(ext)s"
    assert str(OutputTemplate.dated()) == "%(upload_date)s - %(title)s.%(ext)s"
    assert (
        str(OutputTemplate.playlist_folder())
        == "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s"
    )
    assert (
        str(OutputTemplate.playlist_folder(padding=3))
        == "%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s"
    )
    assert (
        str(OutputTemplate.channel_folder()) == "%(uploader)s/%(upload_date)s - %(title)s.%(ext)s"
    )


def test_output_template_fluent_builder() -> None:
    """Проверяет построение сложных путей через fluent-методы."""
    tpl = OutputTemplate().channel().dir().playlist_index(2).text(" - ").title().ext()
    assert str(tpl) == "%(channel)s/%(playlist_index)02d - %(title)s.%(ext)s"


def test_output_template_operators() -> None:
    """Проверяет операторы композиции / и +."""
    # Разделитель директорий /
    dir_tpl = OutputTemplate().channel() / OutputTemplate.title_only()
    assert str(dir_tpl) == "%(channel)s/%(title)s.%(ext)s"

    # Конкатенация +
    concat_tpl = (
        OutputTemplate().title() + " [" + OutputTemplate().id() + "]" + OutputTemplate().ext()
    )
    assert str(concat_tpl) == "%(title)s [%(id)s].%(ext)s"


def test_ytdlp_options_with_output_template_and_container() -> None:
    """Проверяет интеграцию OutputTemplate и VideoContainer в YTDLPOptions."""
    options = YTDLPOptions(
        output_template=OutputTemplate.title_only(),
        container=VideoContainer.MP4,
    )
    params = options.to_ytdlp_params()

    # Проверяем шаблон вывода
    assert params["outtmpl"] == {"default": "%(title)s.%(ext)s"}

    # Проверяем флаг remuxvideo
    assert params["remuxvideo"] == "mp4"

    # Проверяем наличие postprocessor remuxer
    pps = params.get("postprocessors")
    assert isinstance(pps, list)
    remux_pp = next((p for p in pps if p.get("key") == "FFmpegVideoRemuxer"), None)
    assert remux_pp is not None
    assert remux_pp["preferedformat"] == "mp4"


def test_format_selector_container_support() -> None:
    """Проверяет указание контейнера в селекторе форматов."""
    # Метод .container()
    sel = FormatSelector.video().container(VideoContainer.MP4)
    assert "ext=mp4" in str(sel)

    # Пресет с указанием контейнера MP4
    p1080 = FormatSelector.preset_1080p(container=VideoContainer.MP4)
    expr1080 = str(p1080)
    assert "ext=mp4" in expr1080
    assert "height<=1080" in expr1080

    # Пресет с указанием контейнера MKV
    p720 = FormatSelector.preset_720p(container=VideoContainer.MKV)
    expr720 = str(p720)
    assert "ext=mkv" in expr720
    assert "height<=720" in expr720
