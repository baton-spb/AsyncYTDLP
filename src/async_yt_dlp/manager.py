"""Менеджер параллельности, жизненного цикла задач и корректного shutdown.

Предоставляет:
- `DownloadJob`: модель описания задачи на загрузку с уникальным ID и метаданными.
- `DownloadManager`: диспетчер параллельного выполнения операций на базе `asyncio.Semaphore`,
  ограничивающий одновременное использование ресурсов и обеспечивающий graceful shutdown.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

from async_yt_dlp._constants import DEFAULT_MAX_CONCURRENCY, DEFAULT_QUEUE_SIZE
from async_yt_dlp._logging import logger
from async_yt_dlp.exceptions import LifecycleError, QueueFullError
from async_yt_dlp.options import YTDLPOptions

T = TypeVar("T")


@dataclass(frozen=True)
class DownloadJob:
    """Модель описания задачи на извлечение или загрузку.

    Attributes:
        url: Исходный URL ресурса.
        job_id: Уникальный идентификатор задачи.
        options: Индивидуальные параметры задачи (`YTDLPOptions`).
        created_at: Timestamp создания задачи.
        metadata: Произвольные пользовательские метаданные (не используются библиотекой напрямую).
    """

    url: str
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    options: YTDLPOptions = field(default_factory=YTDLPOptions)
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, object] = field(default_factory=dict)


class DownloadManager:
    """Менеджер параллельности и жизненного цикла операций yt-dlp.

    Гарантирует:
    - Bounded concurrency: не более `max_concurrency` параллельно запущенных потоков yt-dlp.
    - Backpressure: лимитирование одновременно ожидающих задач через `queue_size`.
    - Graceful shutdown: завершение активных задач перед закрытием без зависших воркеров.
    """

    def __init__(
        self,
        *,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        queue_size: int = DEFAULT_QUEUE_SIZE,
    ) -> None:
        """Инициализирует менеджер параллельных операций загрузки.

        Args:
            max_concurrency: Максимальное количество одновременно выполняемых операций.
            queue_size: Максимальный размер очереди ожидающих операций.

        Raises:
            ValueError: Если max_concurrency или queue_size меньше 1.
        """
        if max_concurrency < 1:
            raise ValueError(f"max_concurrency должен быть >= 1, получено: {max_concurrency}")
        if queue_size < 1:
            raise ValueError(f"queue_size должен быть >= 1, получено: {queue_size}")

        self._max_concurrency = max_concurrency
        self._queue_size = queue_size
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._active_tasks: set[asyncio.Task[object]] = set()
        self._active_jobs: dict[str, DownloadJob] = {}
        self._waiting_count: int = 0
        self._is_closed: bool = False
        self._shutdown_event = asyncio.Event()

    @property
    def max_concurrency(self) -> int:
        """Максимально допустимое число одновременных операций."""
        return self._max_concurrency

    @property
    def active_count(self) -> int:
        """Количество операций, выполняющихся в данный момент."""
        return len(self._active_tasks)

    @property
    def waiting_count(self) -> int:
        """Количество операций, ожидающих в очереди освобождения семафора."""
        return self._waiting_count

    @property
    def is_closed(self) -> bool:
        """Закрыт ли менеджер для приема новых задач."""
        return self._is_closed

    @property
    def active_jobs(self) -> tuple[DownloadJob, ...]:
        """Кортеж текущих выполняющихся задач (снапшот)."""
        return tuple(self._active_jobs.values())

    def get_job(self, job_id: str) -> DownloadJob | None:
        """Возвращает экземпляр задачи по ее идентификатору, если она активна."""
        return self._active_jobs.get(job_id)

    async def run_operation(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        job_id: str | None = None,
        job: DownloadJob | None = None,
    ) -> T:
        """Выполняет асинхронную операцию под контролем семафора параллельности.

        Args:
            operation: Асинхронная корутина-фабрика без аргументов, возвращающая результат.
            job_id: Необязательный идентификатор задачи для логирования.

        Raises:
            LifecycleError: Если менеджер уже находится в состоянии shutdown.
            QueueFullError: Если превышена емкость ожидания `queue_size`.
        """
        if self._is_closed:
            raise LifecycleError("DownloadManager закрыт: новые операции не принимаются.")

        if self._waiting_count >= self._queue_size:
            raise QueueFullError(
                f"Превышен лимит очереди ожидания ({self._queue_size}). "
                "Сервер перегружен, попробуйте позже."
            )

        self._waiting_count += 1
        current_task = asyncio.current_task()
        effective_job_id = job.job_id if job is not None else job_id

        try:
            # Ожидание слота семафора
            async with self._semaphore:
                self._waiting_count -= 1

                if self._is_closed:
                    raise LifecycleError("DownloadManager был закрыт во время ожидания в очереди.")

                if current_task:
                    self._active_tasks.add(current_task)
                if job is not None:
                    self._active_jobs[job.job_id] = job

                logger.debug(
                    "Запуск операции [job_id=%s] (активных: %d, в очереди: %d)",
                    effective_job_id or "direct",
                    self.active_count,
                    self.waiting_count,
                )

                try:
                    return await operation()
                finally:
                    if job is not None:
                        self._active_jobs.pop(job.job_id, None)
                    if current_task:
                        self._active_tasks.discard(current_task)
                    if self._is_closed and not self._active_tasks:
                        self._shutdown_event.set()
        finally:
            # Если задача была отменена ещё до входа в семафор
            if current_task and current_task in self._active_tasks:
                self._active_tasks.discard(current_task)
            if job is not None:
                self._active_jobs.pop(job.job_id, None)

    async def shutdown(self, *, wait: bool = True, timeout: float | None = 15.0) -> None:
        """Выполняет graceful shutdown менеджера.

        1. Запрещает прием новых операций.
        2. При `wait=True` ожидает завершения текущих активных операций до истечения `timeout`.
        3. При превышении таймаута или `wait=False` отменяет ожидающие задачи.

        Args:
            wait: Дожидаться ли завершения активных загрузок.
            timeout: Максимальное время ожидания завершения (в секундах).
        """
        if self._is_closed:
            return

        self._is_closed = True
        logger.info(
            "Инициализирован shutdown DownloadManager (активных задач: %d)",
            len(self._active_tasks),
        )

        if not self._active_tasks:
            self._shutdown_event.set()
            return

        if wait:
            try:
                if timeout is not None and timeout > 0:
                    async with asyncio.timeout(timeout):
                        while self._active_tasks:
                            await asyncio.sleep(0.1)
                else:
                    while self._active_tasks:
                        await asyncio.sleep(0.1)
            except TimeoutError:
                logger.warning(
                    "Истек таймаут shutdown (%s c), принудительно отменяем %d оставшихся задач",
                    timeout,
                    len(self._active_tasks),
                )
                self._cancel_active_tasks()
        else:
            self._cancel_active_tasks()

        self._shutdown_event.set()

    def _cancel_active_tasks(self) -> None:
        """Отменяет все зарегистрированные активные задачи."""
        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()
        self._active_tasks.clear()
        self._active_jobs.clear()
