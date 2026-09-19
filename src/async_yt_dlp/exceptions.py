"""Иерархия исключений для библиотеки async-yt-dlp.

Все исключения библиотеки наследуются от `AsyncYTDLPError` и поддерживают
сохранение контекста операции (URL, идентификатор задачи job_id), а также
корректное связывание причин через стандартный механизм exception chaining (`from exc`).
"""

from __future__ import annotations


class AsyncYTDLPError(Exception):
    """Базовое исключение для всех ошибок библиотеки async-yt-dlp.

    Attributes:
        message: Текстовое описание ошибки.
        url: URL медиа-ресурса, при обработке которого произошла ошибка (если доступен).
        job_id: Идентификатор задачи в очереди (если операция выполнялась в контексте задачи).
    """

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        job_id: str | None = None,
    ) -> None:
        """Инициализирует базовое исключение библиотеки async-yt-dlp.

        Args:
            message: Текстовое описание ошибки.
            url: URL медиа-ресурса, при обработке которого произошла ошибка.
            job_id: Идентификатор задачи в очереди.
        """
        super().__init__(message)
        self.message = message
        self.url = url
        self.job_id = job_id

    def __str__(self) -> str:
        """Возвращает строковое представление ошибки с контекстом URL и job_id."""
        parts: list[str] = [self.message]
        if self.url:
            parts.append(f"[url={self.url}]")
        if self.job_id:
            parts.append(f"[job_id={self.job_id}]")
        return " ".join(parts)


class ExtractionError(AsyncYTDLPError):
    """Ошибка при извлечении метаданных из медиа-ресурса.

    Возникает, если ресурс недоступен, удалён, защищён гео-ограничениями,
    требует авторизации или экстрактор yt-dlp завершился с ошибкой.
    """


class DownloadError(AsyncYTDLPError):
    """Ошибка при скачивании медиа-потоков или фрагментов.

    Возникает при сетевых сбоях, недоступности серверов раздачи,
    ошибках файловой системы во время записи или превышении числа повторов.
    """


class PostProcessingError(AsyncYTDLPError):
    """Ошибка на этапе постобработки медиа-файла.

    Возникает при ошибках запуска и работы ffmpeg/ffprobe, слиянии аудио/видео дорожек,
    конвертации форматов, извлечении аудио или встраивании субтитров и метаданных.
    """


class ConfigurationError(AsyncYTDLPError):
    """Ошибка конфигурации параметров yt-dlp или клиента async-yt-dlp."""


class ValidationError(AsyncYTDLPError):
    """Ошибка валидации входных данных (например, некорректный URL или путь)."""


class OperationTimeoutError(AsyncYTDLPError, TimeoutError):
    """Превышение таймаута ожидания или выполнения операции."""


class CancellationError(AsyncYTDLPError):
    """Операция была отменена по запросу пользователя или при shutdown."""


class DependencyError(AsyncYTDLPError):
    """Отсутствует необходимая внешняя зависимость (например, yt-dlp, ffmpeg или ffprobe)."""


class LifecycleError(AsyncYTDLPError):
    """Недопустимая операция в текущем состоянии жизненного цикла клиента.

    Например, попытка запуска операции на закрытом клиенте (ClientState.CLOSED).
    """


class QueueFullError(AsyncYTDLPError):
    """Очередь задач менеджера заполнена и достигнут предел ожидания."""


def map_ytdlp_error(
    exc: BaseException,
    *,
    url: str | None = None,
    job_id: str | None = None,
) -> AsyncYTDLPError:
    """Преобразует исключение yt-dlp в типизированное исключение async-yt-dlp.

    Сохраняет оригинальное исключение через exception chaining (`__cause__`),
    а также передает контекст (URL и job_id).

    Args:
        exc: Исходное исключение, пойманное при выполнении операции.
        url: URL медиа-ресурса.
        job_id: Идентификатор задачи.

    Returns:
        Экземпляр одного из подклассов `AsyncYTDLPError`.
    """
    if isinstance(exc, AsyncYTDLPError):
        # Если уже наше исключение — возвращаем как есть, при необходимости обновив контекст
        if url and not exc.url:
            exc.url = url
        if job_id and not exc.job_id:
            exc.job_id = job_id
        return exc

    # Проверяем по именам классов и модулей yt-dlp, чтобы избежать жёсткой связанности
    # с версиями yt-dlp при импорте редких внутренних ошибок
    exc_type_name = type(exc).__name__
    exc_module = getattr(type(exc), "__module__", "")
    exc_msg = str(exc)

    # Проверка на отмену загрузки
    if "DownloadCancelled" in exc_type_name or "MaxDownloadsReached" in exc_type_name:
        mapped_canc = CancellationError(
            f"Операция скачивания была отменена: {exc_msg}",
            url=url,
            job_id=job_id,
        )
        mapped_canc.__cause__ = exc
        return mapped_canc

    # Проверка на ошибки извлечения (ExtractorError, GeoRestrictedError, UserNotLive)
    if (
        "ExtractorError" in exc_type_name
        or "GeoRestrictedError" in exc_type_name
        or "UserNotLive" in exc_type_name
    ):
        mapped_ext = ExtractionError(
            f"Ошибка извлечения метаданных: {exc_msg}",
            url=url,
            job_id=job_id,
        )
        mapped_ext.__cause__ = exc
        return mapped_ext

    # Проверка на ошибки постобработки (PostProcessingError, AudioConversionError, FFmpegPostProcessorError)
    if (
        "PostProcessingError" in exc_type_name
        or "AudioConversionError" in exc_type_name
        or "FFmpeg" in exc_type_name
    ):
        mapped_pp = PostProcessingError(
            f"Ошибка постобработки: {exc_msg}",
            url=url,
            job_id=job_id,
        )
        mapped_pp.__cause__ = exc
        return mapped_pp

    # Проверка на ошибки загрузки (DownloadError, SameFileError)
    if "DownloadError" in exc_type_name or "SameFileError" in exc_type_name:
        mapped_dl = DownloadError(
            f"Ошибка скачивания: {exc_msg}",
            url=url,
            job_id=job_id,
        )
        mapped_dl.__cause__ = exc
        return mapped_dl

    # Проверка на таймауты
    if isinstance(exc, TimeoutError):
        mapped_to = OperationTimeoutError(
            f"Превышено время ожидания операции: {exc_msg}",
            url=url,
            job_id=job_id,
        )
        mapped_to.__cause__ = exc
        return mapped_to

    # Любое другое исключение yt-dlp или общее исключение
    if "yt_dlp" in exc_module or "YoutubeDL" in exc_type_name:
        mapped_ydl = AsyncYTDLPError(
            f"Ошибка yt-dlp ({exc_type_name}): {exc_msg}",
            url=url,
            job_id=job_id,
        )
        mapped_ydl.__cause__ = exc
        return mapped_ydl

    # Непредвиденная системная ошибка
    mapped_gen = AsyncYTDLPError(
        f"Внутренняя ошибка выполнения ({exc_type_name}): {exc_msg}",
        url=url,
        job_id=job_id,
    )
    mapped_gen.__cause__ = exc
    return mapped_gen
