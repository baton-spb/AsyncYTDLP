"""Слой выполнения (Execution Backend) для запуска синхронного yt-dlp.

Предоставляет:
- `DownloadBackend`: протокол (`Protocol`) абстрактного бэкенда выполнения.
- `ThreadBackend`: основная продакшн-реализация на базе управляемого пула потоков
  через `asyncio.to_thread()` со строгой изоляцией экземпляров `YoutubeDL`.
"""

from __future__ import annotations

import asyncio
import contextvars
import os
import time
from collections.abc import Mapping
from typing import Protocol, cast

from async_yt_dlp._logging import YTDLPLoggerAdapter, logger
from async_yt_dlp.exceptions import map_ytdlp_error
from async_yt_dlp.progress import ProgressBridge

# Контекстная переменная для сквозной трассировки идентификатора задачи
current_job_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_job_id", default=None
)


class DownloadBackend(Protocol):
    """Протокол для бэкендов выполнения yt-dlp."""

    async def extract_info(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        download: bool = False,
        extra_info: Mapping[str, object] | None = None,
        job_id: str | None = None,
    ) -> dict[str, object]:
        """Асинхронно извлекает метаданные медиа-ресурса."""
        ...

    async def download(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        progress_bridge: ProgressBridge | None = None,
        extra_info: Mapping[str, object] | None = None,
        job_id: str | None = None,
    ) -> tuple[dict[str, object], float]:
        """Асинхронно скачивает медиа-ресурс и возвращает `(info_dict, elapsed_seconds)`."""
        ...

    async def close(self) -> None:
        """Освобождает ресурсы бэкенда."""
        ...


class ThreadBackend:
    """Бэкенд выполнения yt-dlp в пуле рабочих потоков через `asyncio.to_thread`.

    Ключевые архитектурные принципы:
    1. Изоляция потокобезопасности: для каждой операции создается изолированный
       экземпляр `yt_dlp.YoutubeDL`, так как внутреннее состояние `YoutubeDL`
       не является потокобезопасным при параллельном вызове.
    2. Event Loop разгружен: все блокирующие сетевые вызовы, дисковые операции
       и процессы ffmpeg выполняются исключительно в потоках ОС.
    3. Преобразование ошибок: любые ошибки синхронного ядра перехватываются
       и транслируются в типизированную иерархию `AsyncYTDLPError`.
    """

    def __init__(self) -> None:
        """Инициализирует бэкенд выполнения операций yt-dlp в пуле потоков."""
        self._is_closed: bool = False

    async def extract_info(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        download: bool = False,
        extra_info: Mapping[str, object] | None = None,
        job_id: str | None = None,
    ) -> dict[str, object]:
        """Извлекает словарь метаданных для заданного URL."""
        if self._is_closed:
            raise RuntimeError("ThreadBackend закрыт.")

        token = current_job_id.set(job_id)
        try:
            return await asyncio.to_thread(
                self._sync_extract,
                url,
                params,
                download=download,
                extra_info=extra_info,
                job_id=job_id,
            )
        except Exception as exc:
            mapped_exc = map_ytdlp_error(exc, url=url, job_id=job_id)
            logger.debug("Ошибка при извлечении метаданных: %s", mapped_exc)
            raise mapped_exc from exc
        finally:
            current_job_id.reset(token)

    async def download(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        progress_bridge: ProgressBridge | None = None,
        extra_info: Mapping[str, object] | None = None,
        job_id: str | None = None,
    ) -> tuple[dict[str, object], float]:
        """Скачивает медиа-ресурс и передает события прогресса в `ProgressBridge`."""
        if self._is_closed:
            raise RuntimeError("ThreadBackend закрыт.")

        token = current_job_id.set(job_id)
        start_time = time.monotonic()
        try:
            info_dict = await asyncio.to_thread(
                self._sync_download,
                url,
                params,
                progress_bridge=progress_bridge,
                extra_info=extra_info,
                job_id=job_id,
            )
            elapsed = time.monotonic() - start_time
            if progress_bridge:
                progress_bridge.finish()
            return info_dict, elapsed
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            if progress_bridge:
                progress_bridge.finish(error=str(exc))
            mapped_exc = map_ytdlp_error(exc, url=url, job_id=job_id)
            logger.debug("Ошибка при скачивании ресурса: %s", mapped_exc)
            raise mapped_exc from exc
        finally:
            current_job_id.reset(token)

    def _sync_extract(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        download: bool,
        extra_info: Mapping[str, object] | None,
        job_id: str | None,
    ) -> dict[str, object]:
        """Синхронная функция извлечения, выполняемая в отдельном потоке."""
        from yt_dlp import YoutubeDL

        opts: dict[str, object] = dict(params)
        self._ensure_ffmpeg_location(opts)

        # Настройка адаптера логирования, если пользователь не указал свой
        if "logger" not in opts:
            opts["logger"] = YTDLPLoggerAdapter()

        with YoutubeDL(opts) as ydl:
            result = ydl.extract_info(url, download=download, extra_info=extra_info)
            if result is None:
                # При ignoreerrors=True yt-dlp может вернуть None при неудаче
                raise RuntimeError(
                    f"Не удалось извлечь метаданные для {url} (yt-dlp вернул пустой результат)"
                )
            return cast(dict[str, object], result)

    def _sync_download(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        progress_bridge: ProgressBridge | None,
        extra_info: Mapping[str, object] | None,
        job_id: str | None,
    ) -> dict[str, object]:
        """Синхронная функция скачивания, выполняемая в отдельном потоке."""
        from yt_dlp import YoutubeDL

        opts: dict[str, object] = dict(params)
        self._ensure_ffmpeg_location(opts)

        if "logger" not in opts:
            opts["logger"] = YTDLPLoggerAdapter()

        # Регистрация хуков прогресса в словарь параметров
        if progress_bridge:
            existing_progress = list(cast(list[object], opts.get("progress_hooks") or []))
            existing_progress.append(progress_bridge.sync_hook)
            opts["progress_hooks"] = existing_progress

            existing_pps = list(cast(list[object], opts.get("postprocessor_hooks") or []))
            existing_pps.append(progress_bridge.sync_postprocessor_hook)
            opts["postprocessor_hooks"] = existing_pps

        with YoutubeDL(opts) as ydl:
            result = ydl.extract_info(url, download=True, extra_info=extra_info)
            if result is None:
                raise RuntimeError(f"Не удалось скачать медиа-ресурс для {url}")
            return cast(dict[str, object], result)

    @staticmethod
    def _ensure_ffmpeg_location(opts: dict[str, object]) -> None:
        """Автоматически разрешает расположение ffmpeg, если не задано пользователем явно."""
        from async_yt_dlp._dependencies import check_dependencies

        deps = check_dependencies()
        if deps.ffmpeg_path is not None:
            ffmpeg_dir = str(deps.ffmpeg_path.parent)
            if "ffmpeg_location" not in opts:
                opts["ffmpeg_location"] = ffmpeg_dir
            current_path = os.environ.get("PATH", "")
            if ffmpeg_dir not in current_path:
                os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}"

    async def close(self) -> None:
        """Очистка бэкенда."""
        self._is_closed = True
