"""Главный клиент библиотеки `AsyncYTDLP`.

Предоставляет современный, строго типизированный и безопасный asyncio API
для взаимодействия с `yt-dlp` без ручного управления потоками, семафорами и синхронизацией.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from async_yt_dlp._constants import (
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_THROTTLE_INTERVAL,
)
from async_yt_dlp._dependencies import DependencyInfo, check_dependencies
from async_yt_dlp._logging import logger
from async_yt_dlp._validation import validate_path, validate_url
from async_yt_dlp.backend import DownloadBackend, ThreadBackend
from async_yt_dlp.exceptions import (
    AsyncYTDLPError,
    LifecycleError,
)
from async_yt_dlp.manager import DownloadManager
from async_yt_dlp.models import DownloadResult, MediaInfo
from async_yt_dlp.options import YTDLPOptions
from async_yt_dlp.progress import ProgressBridge, ProgressEvent


class ClientState(StrEnum):
    """Состояния жизненного цикла клиента `AsyncYTDLP`."""

    NEW = "new"
    RUNNING = "running"
    CLOSING = "closing"
    CLOSED = "closed"


class ErrorPolicy(StrEnum):
    """Политика обработки ошибок при пакетной загрузке нескольких URL (`download_many`)."""

    FAIL_FAST = "fail_fast"  # Прерывание всей группы при первой ошибке
    COLLECT = "collect"  # Сохранение ошибок в результирующем списке
    SKIP = "skip"  # Игнорирование ошибок, возврат только успешных результатов


class AsyncYTDLP:
    """Главный асинхронный клиент-обёртка над yt-dlp.

    Пример базового использования:
    ```python
    async with AsyncYTDLP(max_concurrency=4) as ytdlp:
        # Извлечение метаданных
        info = await ytdlp.extract_info("https://...")
        print(info.title, info.duration)

        # Скачивание файла
        result = await ytdlp.download("https://...")
        print(result.filepath)
    ```

    Отслеживание прогресса через async iterator:
    ```python
    async with AsyncYTDLP() as ytdlp:
        async for event in ytdlp.download_with_progress("https://..."):
            print(event.status, event.percent, event.speed_str)
    ```
    """

    def __init__(
        self,
        *,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        queue_size: int = DEFAULT_QUEUE_SIZE,
        default_options: YTDLPOptions | None = None,
        backend: DownloadBackend | None = None,
    ) -> None:
        """Инициализирует клиент `AsyncYTDLP`.

        Args:
            max_concurrency: Максимальное количество одновременных рабочих потоков yt-dlp.
            queue_size: Максимальный размер очереди задач при пиковой нагрузке.
            default_options: Базовые параметры yt-dlp, применяемые ко всем операциям клиента.
            backend: Пользовательский бэкенд выполнения (по умолчанию `ThreadBackend`).
        """
        self._default_options = default_options or YTDLPOptions()
        self._backend = backend or ThreadBackend()
        self._manager = DownloadManager(
            max_concurrency=max_concurrency,
            queue_size=queue_size,
        )
        self._state: ClientState = ClientState.NEW

    @property
    def state(self) -> ClientState:
        """Текущее состояние жизненного цикла клиента."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Закрыт ли клиент для новых операций."""
        return self._state in (ClientState.CLOSING, ClientState.CLOSED)

    async def __aenter__(self) -> Self:
        """Вход в контекстный менеджер (переводит клиент в состояние RUNNING)."""
        if self._state == ClientState.CLOSED:
            raise LifecycleError("Невозможно повторно открыть уже закрытый клиент AsyncYTDLP.")
        self._state = ClientState.RUNNING
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Выход из контекстного менеджера с автоматическим вызовом graceful close()."""
        await self.close()

    def _ensure_running(self) -> None:
        """Проверяет допустимость вызова операций в текущем состоянии."""
        if self._state == ClientState.NEW:
            # Разрешаем прямой вызов без `async with`, автоматически активируя состояние
            self._state = ClientState.RUNNING
            return

        if self._state != ClientState.RUNNING:
            raise LifecycleError(
                f"Клиент находится в состоянии '{self._state.value}'. "
                "Операции разрешены только в состоянии 'running'."
            )

    async def close(self, *, wait: bool = True, timeout: float | None = 15.0) -> None:
        """Выполняет корректное завершение работы клиента (graceful shutdown).

        1. Запрещает приём новых операций.
        2. Дожидается завершения активных операций менеджера.
        3. Закрывает execution backend.
        Метод идемпотентен: повторные вызовы безопасны.

        Args:
            wait: Дожидаться ли завершения активных скачиваний.
            timeout: Максимальное время ожидания (в секундах).
        """
        if self._state == ClientState.CLOSED:
            return

        self._state = ClientState.CLOSING
        try:
            await self._manager.shutdown(wait=wait, timeout=timeout)
            await self._backend.close()
        finally:
            self._state = ClientState.CLOSED
            logger.info("Клиент AsyncYTDLP успешно закрыт.")

    async def extract_info(
        self,
        url: str,
        *,
        download: bool = False,
        options: YTDLPOptions | None = None,
        extra_info: dict[str, Any] | None = None,
        job_id: str | None = None,
    ) -> MediaInfo:
        """Извлекает нормализованные метаданные медиа-ресурса или плейлиста.

        Args:
            url: URL видео, плейлиста или поисковой фразы.
            download: Выполнять ли также загрузку медиа (по умолчанию False).
            options: Дополнительные параметры для данной операции.
            extra_info: Дополнительный словарь для передачи в `extract_info`.
            job_id: Идентификатор задачи для трассировки.

        Returns:
            Экземпляр `MediaInfo` с типизированными метаданными.
        """
        self._ensure_running()
        validated_url = validate_url(
            url,
            allow_file_urls=(
                options.allow_file_urls if options else self._default_options.allow_file_urls
            ),
        )

        effective_opts = self._default_options.merge(options)
        params = effective_opts.to_ytdlp_params()

        async def _op() -> dict[str, Any]:
            return await self._backend.extract_info(
                validated_url,
                params,
                download=download,
                extra_info=extra_info,
                job_id=job_id,
            )

        raw_info = await self._manager.run_operation(_op, job_id=job_id)
        return MediaInfo.from_ytdlp(raw_info)

    async def download(
        self,
        url: str,
        *,
        options: YTDLPOptions | None = None,
        on_progress: Callable[[ProgressEvent], Any] | None = None,
        extra_info: dict[str, Any] | None = None,
        job_id: str | None = None,
        _bridge: ProgressBridge | None = None,
    ) -> DownloadResult:
        """Скачивает медиа-ресурс и возвращает `DownloadResult`.

        Args:
            url: URL видео или аудио для загрузки.
            options: Параметры загрузки и постобработки.
            on_progress: Опциональный callback (синхронный или асинхронный),
                         вызываемый при каждом событии прогресса.
            extra_info: Дополнительные данные yt-dlp.
            job_id: Идентификатор задачи для трассировки.
            _bridge: Внутренний мост событий (используется `download_with_progress`).

        Returns:
            `DownloadResult` с итоговым путем к файлу, метаданными и длительностью скачивания.
        """
        self._ensure_running()
        validated_url = validate_url(
            url,
            allow_file_urls=(
                options.allow_file_urls if options else self._default_options.allow_file_urls
            ),
        )

        effective_opts = self._default_options.merge(options)
        params = effective_opts.to_ytdlp_params()

        loop = asyncio.get_running_loop()
        bridge = _bridge or ProgressBridge(loop)
        consumer_task: asyncio.Task[None] | None = None

        # Если передан внешний коллбэк on_progress, запускаем фоновый читатель моста
        if on_progress is not None and _bridge is None:

            async def _consume_progress() -> None:
                async for event in bridge:
                    try:
                        res = on_progress(event)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as cb_err:
                        logger.warning("Ошибка в пользовательском on_progress callback: %s", cb_err)

            consumer_task = asyncio.create_task(
                _consume_progress(), name=f"progress-{job_id or 'direct'}"
            )

        async def _op() -> tuple[dict[str, Any], float]:
            return await self._backend.download(
                validated_url,
                params,
                progress_bridge=bridge,
                extra_info=extra_info,
                job_id=job_id,
            )

        try:
            raw_info, elapsed = await self._manager.run_operation(_op, job_id=job_id)
        finally:
            if consumer_task is not None:
                await consumer_task

        media_info = MediaInfo.from_ytdlp(raw_info)

        # Определение финального пути к скачанному файлу
        filepath_str = (
            raw_info.get("filepath") or raw_info.get("_filename") or raw_info.get("filename")
        )
        if (
            not filepath_str
            and "requested_downloads" in raw_info
            and raw_info["requested_downloads"]
        ):
            req_first = raw_info["requested_downloads"][0]
            filepath_str = (
                req_first.get("filepath") or req_first.get("_filename") or req_first.get("filename")
            )

        final_path = (
            validate_path(filepath_str)
            if filepath_str
            else Path(f"{media_info.id}.{media_info.ext or 'mp4'}")
        )

        return DownloadResult(
            filepath=final_path,
            info=media_info,
            elapsed=elapsed,
            requested_formats=media_info.requested_formats,
        )

    async def download_with_progress(
        self,
        url: str,
        *,
        options: YTDLPOptions | None = None,
        throttle_interval: float = DEFAULT_THROTTLE_INTERVAL,
        extra_info: dict[str, Any] | None = None,
        job_id: str | None = None,
    ) -> AsyncIterator[ProgressEvent]:
        """Асинхронный генератор событий прогресса скачивания.

        Позволяет транслировать статус, скорость и проценты загрузки в UI, Telegram-боты,
        FastAPI SSE или консоль.

        Пример:
        ```python
        async for event in ytdlp.download_with_progress(url):
            if event.status == DownloadStatus.DOWNLOADING:
                print(f"{event.percent:.1f}% | {event.speed_str}")
        ```
        """
        self._ensure_running()
        loop = asyncio.get_running_loop()
        bridge = ProgressBridge(loop, throttle_interval=throttle_interval)

        # Запускаем операцию загрузки в отдельной задаче, связанной с мостом
        download_task = asyncio.create_task(
            self.download(
                url,
                options=options,
                extra_info=extra_info,
                job_id=job_id,
                _bridge=bridge,
            ),
            name=f"dl-stream-{job_id or 'direct'}",
        )

        try:
            async for event in bridge:
                yield event
            # Дожидаемся успешного завершения задачи или проброса ошибки
            await download_task
        except asyncio.CancelledError:
            download_task.cancel()
            raise
        except Exception:
            if not download_task.done():
                download_task.cancel()
            raise

    async def download_many(
        self,
        urls: Sequence[str],
        *,
        options: YTDLPOptions | None = None,
        on_error: ErrorPolicy = ErrorPolicy.COLLECT,
    ) -> list[DownloadResult | AsyncYTDLPError]:
        """Пакетное скачивание нескольких URL с контролируемой параллельностью.

        Использует структурированную конкурентность Python 3.14 (`asyncio.TaskGroup`).

        Args:
            urls: Последовательность URL-адресов для скачивания.
            options: Общие параметры для всех загрузок группы.
            on_error: Политика обработки ошибок (`FAIL_FAST`, `COLLECT`, `SKIP`).

        Returns:
            Список результатов `DownloadResult` или объектов `AsyncYTDLPError`.
        """
        self._ensure_running()
        if not urls:
            return []

        results: list[DownloadResult | AsyncYTDLPError | None] = [None] * len(urls)

        async def _worker(idx: int, target_url: str) -> None:
            try:
                res = await self.download(target_url, options=options)
                results[idx] = res
            except AsyncYTDLPError as err:
                if on_error == ErrorPolicy.FAIL_FAST:
                    raise
                results[idx] = err
            except Exception as unk_err:
                if on_error == ErrorPolicy.FAIL_FAST:
                    raise
                from async_yt_dlp.exceptions import map_ytdlp_error

                results[idx] = map_ytdlp_error(unk_err, url=target_url)

        async with asyncio.TaskGroup() as tg:
            for i, u in enumerate(urls):
                tg.create_task(_worker(i, u), name=f"batch-{i}")

        if on_error == ErrorPolicy.SKIP:
            return [r for r in results if isinstance(r, DownloadResult)]

        # COLLECT или FAIL_FAST (если без исключений)
        return [r for r in results if r is not None]

    async def check_dependencies(self, *, force_refresh: bool = False) -> DependencyInfo:
        """Проверяет состояние системных зависимостей (yt-dlp, ffmpeg, ffprobe, JS engines)."""
        loc = self._default_options.ffmpeg_location
        return check_dependencies(loc, force_refresh=force_refresh)
