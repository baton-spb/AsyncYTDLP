"""Главный клиент библиотеки `AsyncYTDLP`.

Предоставляет современный, строго типизированный и безопасный asyncio API
для взаимодействия с `yt-dlp` без ручного управления потоками, семафорами и синхронизацией.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from types import TracebackType
from typing import Self

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
from async_yt_dlp.manager import DownloadJob, DownloadManager
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
    """Политика обработки ошибок при пакетной загрузке (`download_many`)."""

    FAIL_FAST = "fail_fast"  # Прерывание всей группы при первой ошибке
    COLLECT = "collect"  # Сбор результатов и объектов исключений в общий список
    SKIP = "skip"  # Пропуск неудавшихся загрузок (возвращаются только успешные результаты)


class AsyncYTDLP:
    """Главный асинхронный клиент для управления операциями yt-dlp."""

    def __init__(
        self,
        *,
        options: YTDLPOptions | None = None,
        default_options: YTDLPOptions | None = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        queue_size: int = DEFAULT_QUEUE_SIZE,
        backend: DownloadBackend | None = None,
    ) -> None:
        """Инициализирует клиент `AsyncYTDLP`.

        Args:
            options: Базовые параметры yt-dlp по умолчанию для всех операций клиента.
            default_options: Альтернативный параметр для options (обратная совместимость).
            max_concurrency: Максимальное количество одновременных операций yt-dlp.
            queue_size: Максимальный размер очереди ожидания слота параллельности.
            backend: Кастомный бэкенд выполнения. Если не задан, используется `ThreadBackend`.
        """
        self._default_options = options or default_options or YTDLPOptions()
        self._backend: DownloadBackend = backend or ThreadBackend()
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

    @property
    def manager(self) -> DownloadManager:
        """Экземпляр менеджера параллельности и очереди задач."""
        return self._manager

    async def __aenter__(self) -> Self:
        """Вход в контекстный менеджер (переводит клиент в состояние RUNNING)."""
        if self._state == ClientState.CLOSED:
            raise LifecycleError("Невозможно повторно открыть уже закрытый клиент AsyncYTDLP.")
        self._state = ClientState.RUNNING
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
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
        extra_info: Mapping[str, object] | None = None,
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

        async def _op() -> dict[str, object]:
            """Выполняет вызов бэкенда для извлечения метаданных."""
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
        on_progress: Callable[[ProgressEvent], object] | None = None,
        extra_info: Mapping[str, object] | None = None,
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
                """Считывает события прогресса из моста и передает их в пользовательский callback."""
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

        job = DownloadJob(
            url=validated_url,
            job_id=job_id or str(uuid.uuid4()),
            options=effective_opts,
        )

        async def _op() -> tuple[dict[str, object], float]:
            """Выполняет вызов бэкенда для скачивания медиа-ресурса."""
            return await self._backend.download(
                validated_url,
                params,
                progress_bridge=bridge,
                extra_info=extra_info,
                job_id=job.job_id,
            )

        try:
            raw_info, elapsed = await self._manager.run_operation(_op, job_id=job.job_id, job=job)
        finally:
            if consumer_task is not None:
                await consumer_task

        media_info = MediaInfo.from_ytdlp(raw_info)

        # Определение финального пути к скачанному файлу
        filepath_str: str | None = None
        raw_filepath = (
            raw_info.get("filepath") or raw_info.get("_filename") or raw_info.get("filename")
        )
        if raw_filepath:
            filepath_str = str(raw_filepath)
        elif raw_info.get("requested_downloads"):
            req_downloads = raw_info["requested_downloads"]
            if isinstance(req_downloads, list) and req_downloads:
                req_first = req_downloads[0]
                if isinstance(req_first, Mapping):
                    rf = (
                        req_first.get("filepath")
                        or req_first.get("_filename")
                        or req_first.get("filename")
                    )
                    if rf:
                        filepath_str = str(rf)

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
        extra_info: Mapping[str, object] | None = None,
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
            """Выполняет скачивание отдельного URL в группе задач."""
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

    async def download_playlist(
        self,
        url: str,
        *,
        options: YTDLPOptions | None = None,
        start: int | None = None,
        end: int | None = None,
        max_items: int | None = None,
        on_progress: Callable[[ProgressEvent], object] | None = None,
        on_error: ErrorPolicy = ErrorPolicy.COLLECT,
    ) -> AsyncIterator[DownloadResult | AsyncYTDLPError]:
        """Асинхронный генератор для последовательной загрузки элементов плейлиста.

        Извлекает метаданные плейлиста, фильтрует диапазон записей и последовательно
        скачивает каждое медиа, отдавая результат по мере готовности через `yield`.

        Args:
            url: URL плейлиста, канала или отдельного видео.
            options: Опции yt-dlp для загрузки элементов.
            start: Начальный индекс элемента (1-индексированный, как в yt-dlp).
            end: Конечный индекс элемента (включительно, 1-индексированный).
            max_items: Максимальное количество элементов для скачивания.
            on_progress: Опциональный callback прогресса для каждого скачивания.
            on_error: Стратегия обработки ошибок (FAIL_FAST, COLLECT, SKIP).

        Yields:
            Объекты `DownloadResult` или исключения `AsyncYTDLPError` (при политике COLLECT).

        Raises:
            AsyncYTDLPError: При первой ошибке, если выбрана политика `FAIL_FAST`.
        """
        self._ensure_running()
        extract_opts = (options or self._default_options).merge(
            YTDLPOptions(extract_flat="in_playlist", skip_download=True)
        )
        info = await self.extract_info(url, options=extract_opts)

        entries: list[MediaInfo] = (
            list(info.entries) if info.is_playlist and info.entries else [info]
        )

        # Применение диапазона start / end (1-based index)
        start_idx = max(0, start - 1) if (start is not None and start > 0) else 0
        end_idx = end if (end is not None and end > 0) else None
        selected = entries[start_idx:end_idx]

        if max_items is not None and max_items > 0:
            selected = selected[:max_items]

        for item in selected:
            item_url = (
                item.webpage_url
                or (f"https://www.youtube.com/watch?v={item.id}" if item.id else None)
                or url
            )
            try:
                result = await self.download(
                    item_url,
                    options=options,
                    on_progress=on_progress,
                    job_id=f"pl-{item.id or 'item'}",
                )
                yield result
            except AsyncYTDLPError as err:
                if on_error == ErrorPolicy.FAIL_FAST:
                    raise
                if on_error == ErrorPolicy.COLLECT:
                    yield err
            except Exception as unk_err:
                from async_yt_dlp.exceptions import map_ytdlp_error

                mapped = map_ytdlp_error(unk_err, url=item_url)
                if on_error == ErrorPolicy.FAIL_FAST:
                    raise mapped from unk_err
                if on_error == ErrorPolicy.COLLECT:
                    yield mapped

    async def download_playlist_all(
        self,
        url: str,
        *,
        options: YTDLPOptions | None = None,
        start: int | None = None,
        end: int | None = None,
        max_items: int | None = None,
        on_progress: Callable[[ProgressEvent], object] | None = None,
        on_error: ErrorPolicy = ErrorPolicy.COLLECT,
    ) -> list[DownloadResult | AsyncYTDLPError]:
        """Скачивает все элементы плейлиста и возвращает полный список результатов.

        Удобная обертка над генератором `download_playlist` для сценариев,
        где требуется дождаться завершения всего пакета.
        """
        results: list[DownloadResult | AsyncYTDLPError] = []
        async for res in self.download_playlist(
            url,
            options=options,
            start=start,
            end=end,
            max_items=max_items,
            on_progress=on_progress,
            on_error=on_error,
        ):
            results.append(res)
        return results

    async def check_dependencies(self, *, force_refresh: bool = False) -> DependencyInfo:
        """Проверяет состояние системных зависимостей (yt-dlp, ffmpeg, ffprobe, JS engines)."""
        loc = self._default_options.ffmpeg_location
        return check_dependencies(loc, force_refresh=force_refresh)
