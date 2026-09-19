"""Проверка внешних зависимостей окружения (yt-dlp, ffmpeg, ffprobe, JS runtimes).

Функции модуля выполняют обнаружение исполняемых файлов в PATH или по заданным путям,
кешируют результат и возвращают строго типизированную структуру `DependencyInfo`.
"""

from __future__ import annotations

import functools
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True)
class DependencyInfo:
    """Информация о доступных в системе зависимостях и внешних утилитах.

    Attributes:
        ytdlp_version: Версия установленной библиотеки yt-dlp.
        ffmpeg_available: Доступен ли исполняемый файл ffmpeg.
        ffprobe_available: Доступен ли исполняемый файл ffprobe.
        ffmpeg_version: Текстовая версия ffmpeg (первая строка `ffmpeg -version`) или None.
        ffmpeg_path: Абсолютный путь к исполняемому файлу ffmpeg или None.
        ffprobe_path: Абсолютный путь к исполняемому файлу ffprobe или None.
        js_runtimes: Список найденных сред исполнения JavaScript (deno, node, bun, quickjs).
    """

    ytdlp_version: str
    ffmpeg_available: bool
    ffprobe_available: bool
    ffmpeg_version: str | None = None
    ffmpeg_path: Path | None = None
    ffprobe_path: Path | None = None
    js_runtimes: tuple[str, ...] = ()

    @property
    def has_ffmpeg_suite(self) -> bool:
        """Доступен ли полный набор ffmpeg + ffprobe для пост-процессинга."""
        return self.ffmpeg_available and self.ffprobe_available

    @property
    def has_js_runtime(self) -> bool:
        """Доступна ли хотя бы одна среда выполнения JavaScript."""
        return len(self.js_runtimes) > 0


_KNOWN_JS_RUNTIMES: Final[tuple[str, ...]] = ("deno", "node", "bun", "qjs", "quickjs")


def _get_binary_version(binary_path: Path) -> str | None:
    """Извлекает версию утилиты вызовом `--version` с коротким таймаутом."""
    try:
        proc = subprocess.run(
            [str(binary_path), "-version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3.0,
        )
        if proc.returncode == 0 and proc.stdout:
            # Возвращаем первую строку вывода (например: "ffmpeg version 7.0.2...")
            return proc.stdout.splitlines()[0].strip()
    except subprocess.SubprocessError, OSError:
        pass
    return None


@functools.lru_cache(maxsize=4)
def _inspect_dependencies_cached(custom_ffmpeg_location: str | None = None) -> DependencyInfo:
    """Внутренняя кешированная проверка зависимостей."""
    # 1. Проверка yt-dlp
    try:
        import yt_dlp

        ytdlp_ver = getattr(yt_dlp, "__version__", "unknown")
    except ImportError:
        ytdlp_ver = "not_installed"

    # 2. Поиск ffmpeg и ffprobe
    ffmpeg_bin: Path | None = None
    ffprobe_bin: Path | None = None

    if custom_ffmpeg_location:
        loc = Path(custom_ffmpeg_location).expanduser()
        if loc.is_file():
            ffmpeg_bin = loc
            sibling_probe = loc.parent / ("ffprobe.exe" if loc.suffix == ".exe" else "ffprobe")
            if sibling_probe.is_file():
                ffprobe_bin = sibling_probe
        elif loc.is_dir():
            for name in ("ffmpeg.exe", "ffmpeg"):
                candidate = loc / name
                if candidate.is_file():
                    ffmpeg_bin = candidate
                    break
            for name in ("ffprobe.exe", "ffprobe"):
                candidate = loc / name
                if candidate.is_file():
                    ffprobe_bin = candidate
                    break

    if not ffmpeg_bin:
        found_ffmpeg = shutil.which("ffmpeg")
        if found_ffmpeg:
            ffmpeg_bin = Path(found_ffmpeg)

    if not ffprobe_bin:
        found_ffprobe = shutil.which("ffprobe")
        if found_ffprobe:
            ffprobe_bin = Path(found_ffprobe)

    ffmpeg_ver: str | None = None
    if ffmpeg_bin:
        ffmpeg_ver = _get_binary_version(ffmpeg_bin)

    # 3. Поиск JS runtimes
    found_runtimes: list[str] = []
    for rt in _KNOWN_JS_RUNTIMES:
        if shutil.which(rt):
            found_runtimes.append(rt)

    return DependencyInfo(
        ytdlp_version=ytdlp_ver,
        ffmpeg_available=ffmpeg_bin is not None,
        ffprobe_available=ffprobe_bin is not None,
        ffmpeg_version=ffmpeg_ver,
        ffmpeg_path=ffmpeg_bin,
        ffprobe_path=ffprobe_bin,
        js_runtimes=tuple(found_runtimes),
    )


def check_dependencies(
    custom_ffmpeg_location: Path | str | None = None,
    *,
    force_refresh: bool = False,
) -> DependencyInfo:
    """Проверяет состояние окружения и доступность внешних зависимостей.

    Результаты кешируются, поэтому повторные вызовы выполняются мгновенно.

    Args:
        custom_ffmpeg_location: Пользовательский путь к ffmpeg или каталогу с бинарниками.
        force_refresh: Сбросить кеш и повторно опросить систему.

    Returns:
        Объект `DependencyInfo` со сведениями о версиях и путях.
    """
    if force_refresh:
        _inspect_dependencies_cached.cache_clear()

    location_str = str(custom_ffmpeg_location) if custom_ffmpeg_location else None
    return _inspect_dependencies_cached(location_str)
