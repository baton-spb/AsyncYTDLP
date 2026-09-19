"""События прогресса и асинхронный мост (ProgressBridge) для async-yt-dlp.

Предоставляет:
- `DownloadStatus`: перечисление стадий загрузки и обработки.
- `ProgressEvent`: строго типизированное событие прогресса с вычисляемыми свойствами (процент, скорость, ETA).
- `ProgressBridge`: потокобезопасный мост, передающий события из синхронных хуков yt-dlp
  в очередь `asyncio.Queue` текущего event loop с регулируемым троттлингом и защитой от backpressure.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from async_yt_dlp._constants import DEFAULT_PROGRESS_QUEUE_SIZE, DEFAULT_THROTTLE_INTERVAL


class DownloadStatus(StrEnum):
    """Статусы жизненного цикла загрузки и обработки медиа."""

    DOWNLOADING = "downloading"
    FINISHED = "finished"  # Загрузка байт завершена, начинается постобработка
    POST_PROCESSING = "post_processing"
    COMPLETE = "complete"  # Вся цепочка полностью завершена
    ERROR = "error"
    CANCELLED = "cancelled"


def _format_bytes(size: float | int | None) -> str:
    """Форматирует размер в байтах в человекочитаемый вид (KiB, MiB, GiB)."""
    if size is None:
        return "N/A"
    bytes_val = float(size)
    if bytes_val < 1024:
        return f"{bytes_val:.0f} B"
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.2f} KiB"
    if bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.2f} MiB"
    return f"{bytes_val / (1024 * 1024 * 1024):.2f} GiB"


def _format_seconds(seconds: float | int | None) -> str:
    """Форматирует секунды в отображение `MM:SS` или `HH:MM:SS`."""
    if seconds is None or seconds < 0:
        return "Unknown"
    sec = int(seconds)
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    secs = sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@dataclass(frozen=True)
class ProgressEvent:
    """Типизированное событие прогресса скачивания или постобработки.

    Attributes:
        status: Текущий статус операции (`DownloadStatus`).
        downloaded_bytes: Количество скачанных байт.
        total_bytes: Известный общий размер файла в байтах.
        total_bytes_estimate: Оценочный общий размер файла в байтах.
        speed: Текущая скорость скачивания в байтах/сек.
        eta: Оценочное оставшееся время в секундах.
        elapsed: Время, прошедшее с начала скачивания, в секундах.
        fragment_index: Номер текущего загружаемого фрагмента.
        fragment_count: Общее количество фрагментов потока.
        filename: Имя итогового файла.
        tmp_filename: Имя временного файла (.part).
        postprocessor: Название активного постпроцессора.
        postprocessor_status: Статус постпроцессора ('started', 'finished').
        error: Сообщение об ошибке, если статус `ERROR`.
    """

    status: DownloadStatus
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    total_bytes_estimate: int | None = None
    speed: float | None = None
    eta: float | None = None
    elapsed: float | None = None
    fragment_index: int | None = None
    fragment_count: int | None = None
    filename: str | None = None
    tmp_filename: str | None = None
    postprocessor: str | None = None
    postprocessor_status: str | None = None
    error: str | None = None

    @property
    def effective_total_bytes(self) -> int | None:
        """Эффективный общий размер файла (точный или оценочный)."""
        return self.total_bytes if self.total_bytes is not None else self.total_bytes_estimate

    @property
    def percent(self) -> float | None:
        """Процент выполнения загрузки (от 0.0 до 100.0) или None при неизвестном размере."""
        if self.status in (DownloadStatus.FINISHED, DownloadStatus.COMPLETE):
            return 100.0
        tot = self.effective_total_bytes
        if tot and tot > 0 and self.downloaded_bytes is not None:
            pct = (self.downloaded_bytes / tot) * 100.0
            return min(100.0, max(0.0, pct))
        return None

    @property
    def speed_str(self) -> str:
        """Человекочитаемое представление скорости (например, '2.50 MiB/s')."""
        if self.speed is not None and self.speed > 0:
            return f"{_format_bytes(self.speed)}/s"
        return "Unknown"

    @property
    def eta_str(self) -> str:
        """Человекочитаемое представление оставшегося времени (например, '01:45')."""
        return _format_seconds(self.eta)

    @property
    def elapsed_str(self) -> str:
        """Человекочитаемое представление затраченного времени."""
        return _format_seconds(self.elapsed)

    @property
    def downloaded_str(self) -> str:
        """Форматированный объем уже загруженных данных."""
        return _format_bytes(self.downloaded_bytes)

    @property
    def total_str(self) -> str:
        """Форматированный общий объем данных."""
        return _format_bytes(self.effective_total_bytes)

    @classmethod
    def from_ytdlp(cls, d: dict[str, Any]) -> ProgressEvent:
        """Создает `ProgressEvent` из словаря `progress_hooks` yt-dlp."""
        raw_status = d.get("status", "")
        if raw_status == "downloading":
            status = DownloadStatus.DOWNLOADING
        elif raw_status == "finished":
            status = DownloadStatus.FINISHED
        elif raw_status == "error":
            status = DownloadStatus.ERROR
        else:
            status = DownloadStatus.DOWNLOADING

        return cls(
            status=status,
            downloaded_bytes=d.get("downloaded_bytes"),
            total_bytes=d.get("total_bytes"),
            total_bytes_estimate=d.get("total_bytes_estimate"),
            speed=d.get("speed"),
            eta=d.get("eta"),
            elapsed=d.get("elapsed"),
            fragment_index=d.get("fragment_index"),
            fragment_count=d.get("fragment_count"),
            filename=d.get("filename"),
            tmp_filename=d.get("tmpfilename"),
            error=str(d.get("error")) if d.get("error") else None,
        )

    @classmethod
    def from_postprocessor(cls, d: dict[str, Any]) -> ProgressEvent:
        """Создает `ProgressEvent` из словаря `postprocessor_hooks` yt-dlp."""
        return cls(
            status=DownloadStatus.POST_PROCESSING,
            postprocessor=d.get("postprocessor"),
            postprocessor_status=d.get("status"),
        )


class ProgressBridge:
    """Асинхронный мост, связывающий потоковые коллбэки yt-dlp с очередью asyncio.

    Особенности реализации:
    - Защита от блокировки воркера: отправка событий в очередь через `loop.call_soon_threadsafe`.
    - Троттлинг: частые события `DOWNLOADING` фильтруются по `throttle_interval`.
    - Гарантированная доставка: ключевые события (`FINISHED`, `POST_PROCESSING`, `ERROR`, `COMPLETE`)
      никогда не отбрасываются троттлингом.
    - Ограниченный размер очереди (`maxsize`): предотвращает неограниченный рост памяти при медленном
      потреблении событий async-кодом.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        *,
        throttle_interval: float = DEFAULT_THROTTLE_INTERVAL,
        queue_size: int = DEFAULT_PROGRESS_QUEUE_SIZE,
    ) -> None:
        self._loop = loop
        self._throttle_interval = max(0.0, throttle_interval)
        self._queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue(maxsize=queue_size)
        self._last_download_emit: float = 0.0
        self._closed: bool = False

    def sync_hook(self, progress_dict: dict[str, Any]) -> None:
        """Синхронный хук, вызываемый `FileDownloader` yt-dlp из worker thread."""
        if self._closed or self._loop.is_closed():
            return

        status = progress_dict.get("status")
        now = time.monotonic()

        # Применяем троттлинг только для частых промежуточных тиков загрузки
        if status == "downloading" and self._throttle_interval > 0:
            if (now - self._last_download_emit) < self._throttle_interval:
                return
            self._last_download_emit = now

        event = ProgressEvent.from_ytdlp(progress_dict)
        self._push_event(event)

    def sync_postprocessor_hook(self, pp_dict: dict[str, Any]) -> None:
        """Синхронный хук, вызываемый `PostProcessor` yt-dlp из worker thread."""
        if self._closed or self._loop.is_closed():
            return

        event = ProgressEvent.from_postprocessor(pp_dict)
        self._push_event(event)

    def finish(self, *, error: str | None = None) -> None:
        """Завершает поток событий, отправляя финальный маркер или ошибку."""
        if self._closed or self._loop.is_closed():
            return
        self._closed = True

        if error:
            self._push_event(ProgressEvent(status=DownloadStatus.ERROR, error=error))
        else:
            self._push_event(ProgressEvent(status=DownloadStatus.COMPLETE))

        # Sentinel маркер для завершения итератора
        self._push_event(None)

    def _push_event(self, event: ProgressEvent | None) -> None:
        """Потокобезопасно помещает событие в очередь event loop."""
        with contextlib.suppress(RuntimeError):
            self._loop.call_soon_threadsafe(self._put_nowait_safe, event)

    def _put_nowait_safe(self, event: ProgressEvent | None) -> None:
        """Выполняется внутри нити event loop для бесконфликтной записи в очередь."""
        if self._queue.full():
            # Если очередь переполнена медленным async consumer'ом:
            # выталкиваем старое событие из очереди, чтобы освободить место.
            with contextlib.suppress(asyncio.QueueEmpty):
                self._queue.get_nowait()

        with contextlib.suppress(asyncio.QueueFull):
            self._queue.put_nowait(event)

    async def __aiter__(self) -> AsyncIterator[ProgressEvent]:
        """Асинхронный генератор для чтения событий из очереди."""
        while True:
            event = await self._queue.get()
            if event is None:
                # Sentinel маркер завершения стрима
                break
            yield event
