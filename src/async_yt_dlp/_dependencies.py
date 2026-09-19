"""Проверка внешних зависимостей окружения (yt-dlp, ffmpeg, ffprobe, JS runtimes).

Функции модуля выполняют обнаружение исполняемых файлов в PATH или по заданным путям,
кешируют результат и возвращают строго типизированную структуру `DependencyInfo`.
"""

from __future__ import annotations

import functools
import importlib.util
import os
import shutil
import subprocess
import sys
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
    has_curl_cffi: bool = False
    has_crypto: bool = False
    has_mutagen: bool = False
    has_ejs: bool = False
    has_aio_ffmpeg: bool = False
    has_async_ffmpeg: bool = False

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
        from yt_dlp.version import __version__ as ytdlp_ver
    except ImportError:
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

    def _find_windows_candidates(filename: str) -> Path | None:
        """Ищет исполняемый файл в стандартных каталогах менеджеров пакетов Windows.

        Args:
            filename: Имя исполняемого файла (например, 'ffmpeg.exe').

        Returns:
            Абсолютный путь к найденному файлу или None, если файл не найден.
        """
        if sys.platform != "win32":
            return None
        candidates = [
            Path(os.path.expandvars(rf"%LOCALAPPDATA%\Microsoft\WinGet\Links\{filename}")),
            Path(os.path.expandvars(rf"%USERPROFILE%\scoop\shims\{filename}")),
            Path(os.path.expandvars(rf"%ProgramData%\chocolatey\bin\{filename}")),
            Path(rf"C:\Program Files\nodejs\{filename}"),
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    # Попытка обнаружения через aio_ffmpeg / async_ffmpeg (если установлен)
    has_aio_ffmpeg = (
        importlib.util.find_spec("aio_ffmpeg") is not None
        or importlib.util.find_spec("async_ffmpeg") is not None
    )
    has_async_ffmpeg = has_aio_ffmpeg
    if has_aio_ffmpeg:
        try:
            try:
                from aio_ffmpeg import find_ffmpeg as aff_find_ffmpeg
                from aio_ffmpeg import find_ffprobe as aff_find_ffprobe
            except ImportError:
                from async_ffmpeg import find_ffmpeg as aff_find_ffmpeg
                from async_ffmpeg import find_ffprobe as aff_find_ffprobe

            if not ffmpeg_bin:
                try:
                    found_ff = aff_find_ffmpeg(custom_ffmpeg_location)
                    if found_ff.is_file():
                        ffmpeg_bin = found_ff
                except Exception:
                    pass

            if not ffprobe_bin:
                try:
                    found_fp = aff_find_ffprobe(custom_ffmpeg_location)
                    if found_fp.is_file():
                        ffprobe_bin = found_fp
                except Exception:
                    pass
        except Exception:
            pass

    # Стандартный поиск через PATH и каталоги Windows
    if not ffmpeg_bin:
        found_ffmpeg = shutil.which("ffmpeg")
        ffmpeg_bin = Path(found_ffmpeg) if found_ffmpeg else _find_windows_candidates("ffmpeg.exe")

    if not ffprobe_bin:
        found_ffprobe = shutil.which("ffprobe")
        ffprobe_bin = (
            Path(found_ffprobe) if found_ffprobe else _find_windows_candidates("ffprobe.exe")
        )

    ffmpeg_ver: str | None = None
    if ffmpeg_bin:
        if has_aio_ffmpeg:
            try:
                try:
                    from aio_ffmpeg import get_binary_version_sync
                except ImportError:
                    from async_ffmpeg import get_binary_version_sync

                ffmpeg_ver = get_binary_version_sync(ffmpeg_bin)
            except Exception:
                ffmpeg_ver = _get_binary_version(ffmpeg_bin)
        else:
            ffmpeg_ver = _get_binary_version(ffmpeg_bin)

    # 3. Поиск JS runtimes
    found_runtimes: list[str] = []
    for rt in _KNOWN_JS_RUNTIMES:
        if shutil.which(rt) or (sys.platform == "win32" and _find_windows_candidates(f"{rt}.exe")):
            found_runtimes.append(rt)

    # 4. Проверка дополнительных Python-пакетов yt-dlp
    has_curl = importlib.util.find_spec("curl_cffi") is not None
    has_crypto = (
        importlib.util.find_spec("Cryptodome") is not None
        or importlib.util.find_spec("cryptography") is not None
    )
    has_mutagen = importlib.util.find_spec("mutagen") is not None
    has_ejs = importlib.util.find_spec("yt_dlp_ejs") is not None

    return DependencyInfo(
        ytdlp_version=ytdlp_ver,
        ffmpeg_available=ffmpeg_bin is not None,
        ffprobe_available=ffprobe_bin is not None,
        ffmpeg_version=ffmpeg_ver,
        ffmpeg_path=ffmpeg_bin,
        ffprobe_path=ffprobe_bin,
        js_runtimes=tuple(found_runtimes),
        has_curl_cffi=has_curl,
        has_crypto=has_crypto,
        has_mutagen=has_mutagen,
        has_ejs=has_ejs,
        has_aio_ffmpeg=has_aio_ffmpeg,
        has_async_ffmpeg=has_async_ffmpeg,
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
