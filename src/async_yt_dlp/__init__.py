"""async-yt-dlp — высококачественная асинхронная обёртка над yt-dlp для Python 3.14+.

Предоставляет:
- Строго типизированный асинхронный клиент `AsyncYTDLP`.
- Неизменяемую типизированную конфигурацию `YTDLPOptions`.
- Модели данных `MediaInfo`, `FormatInfo`, `DownloadResult`.
- Асинхронный мост и поток событий прогресса `ProgressEvent`, `DownloadStatus`.
- Контроль параллельности и управление жизненным циклом `DownloadManager`.
- Полную иерархию типизированных исключений `AsyncYTDLPError`.
"""

from async_yt_dlp._constants import __version__
from async_yt_dlp._dependencies import DependencyInfo, check_dependencies
from async_yt_dlp._logging import redact_options, redact_url
from async_yt_dlp._validation import validate_path, validate_url
from async_yt_dlp.backend import DownloadBackend, ThreadBackend
from async_yt_dlp.client import AsyncYTDLP, ClientState, ErrorPolicy
from async_yt_dlp.exceptions import (
    AsyncYTDLPError,
    CancellationError,
    ConfigurationError,
    DependencyError,
    DownloadError,
    ExtractionError,
    LifecycleError,
    OperationTimeoutError,
    PostProcessingError,
    QueueFullError,
    ValidationError,
    map_ytdlp_error,
)
from async_yt_dlp.manager import DownloadJob, DownloadManager
from async_yt_dlp.models import (
    DownloadResult,
    FormatInfo,
    MediaInfo,
    SubtitleInfo,
    ThumbnailInfo,
)
from async_yt_dlp.options import YTDLPOptions
from async_yt_dlp.progress import (
    DownloadStatus,
    ProgressBridge,
    ProgressEvent,
)

__all__ = [
    "AsyncYTDLP",
    "AsyncYTDLPError",
    "CancellationError",
    "ClientState",
    "ConfigurationError",
    "DependencyError",
    "DependencyInfo",
    "DownloadBackend",
    "DownloadError",
    "DownloadJob",
    "DownloadManager",
    "DownloadResult",
    "DownloadStatus",
    "ErrorPolicy",
    "ExtractionError",
    "FormatInfo",
    "LifecycleError",
    "MediaInfo",
    "OperationTimeoutError",
    "PostProcessingError",
    "ProgressBridge",
    "ProgressEvent",
    "QueueFullError",
    "SubtitleInfo",
    "ThreadBackend",
    "ThumbnailInfo",
    "ValidationError",
    "YTDLPOptions",
    "__version__",
    "check_dependencies",
    "map_ytdlp_error",
    "redact_options",
    "redact_url",
    "validate_path",
    "validate_url",
]
