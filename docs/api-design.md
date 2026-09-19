# async-yt-dlp — Архитектура и дизайн API

## Обзор

`async-yt-dlp` — универсальная asyncio-обёртка над синхронным Python API `yt-dlp`.
Предоставляет строго типизированный, безопасный и удобный интерфейс для использования
в любых async-приложениях: Telegram-боты, FastAPI, Discord-боты, CLI, фоновые worker'ы.

---

## 1. Публичный API

### 1.1 Основной клиент

```python
from async_yt_dlp import AsyncYTDLP

async with AsyncYTDLP(
    max_concurrency=4,        # Макс. параллельных операций
    queue_size=100,           # Макс. размер очереди
    default_options=YTDLPOptions(
        format="bestvideo+bestaudio/best",
        output_template="%(title)s [%(id)s].%(ext)s",
    ),
) as ytdlp:
    # Извлечение метаданных
    info = await ytdlp.extract_info(url, download=False)
    print(info.title, info.duration, info.formats)

    # Скачивание
    result = await ytdlp.download(url)
    print(result.filepath)

    # Скачивание с прогрессом
    async for event in ytdlp.download_with_progress(url):
        print(event.status, event.percent, event.speed_str)
```

### 1.2 Извлечение метаданных

```python
info = await ytdlp.extract_info(url, download=False)

# Typed high-level поля
info.id             # str
info.title          # str
info.description    # str | None
info.duration       # float | None
info.uploader       # str | None
info.channel        # str | None
info.webpage_url    # str
info.thumbnail      # str | None
info.ext            # str | None
info.filesize       # int | None
info.is_playlist    # bool
info.entries        # list[MediaInfo] | None  (для плейлистов)
info.formats        # list[FormatInfo]
info.subtitles      # dict[str, list[SubtitleInfo]]
info.thumbnails     # list[ThumbnailInfo]

# Полный raw dict (dict-like, может быть не JSON-serializable)
info.raw_data

# JSON-serializable версия
serializable = info.to_dict()
```

### 1.3 Скачивание

```python
result = await ytdlp.download(url)

result.filepath         # Path — финальный путь к файлу
result.info             # MediaInfo — метаданные
result.requested_formats # list[FormatInfo] | None
result.elapsed          # float — время выполнения (секунды)
```

### 1.4 Скачивание с прогрессом

```python
async for event in ytdlp.download_with_progress(
    url,
    options=YTDLPOptions(format="bestaudio/best"),
    throttle_interval=0.5,  # Минимальный интервал между событиями (секунды)
):
    match event:
        case ProgressEvent(status=DownloadStatus.DOWNLOADING):
            print(f"{event.percent:.1f}% | {event.speed_str} | ETA: {event.eta_str}")
        case ProgressEvent(status=DownloadStatus.FINISHED):
            print(f"Скачивание завершено: {event.filepath}")
        case ProgressEvent(status=DownloadStatus.POST_PROCESSING):
            print(f"Постобработка: {event.postprocessor}")
        case ProgressEvent(status=DownloadStatus.ERROR):
            print(f"Ошибка: {event.error}")
```

### 1.5 Множественные URL

```python
# Параллельное скачивание нескольких URL
results = await ytdlp.download_many(
    [url1, url2, url3],
    on_error=ErrorPolicy.COLLECT,  # FAIL_FAST | COLLECT | SKIP
)

for result in results:
    if isinstance(result, DownloadResult):
        print(result.filepath)
    elif isinstance(result, AsyncYTDLPError):
        print(f"Ошибка: {result}")
```

### 1.6 Отмена

```python
import asyncio

task = asyncio.create_task(ytdlp.download(url))
# ...
task.cancel()
# ВНИМАНИЕ: task.cancel() НЕ гарантирует мгновенную остановку yt-dlp.
# Async Task будет отменён, но sync-поток yt-dlp продолжит работу
# до естественного завершения текущей операции.
```

### 1.7 Таймауты

```python
async with asyncio.timeout(300):  # 5 минут
    result = await ytdlp.download(url)
```

### 1.8 Конфигурация

```python
# Typed конфигурация
options = YTDLPOptions(
    format="bestvideo+bestaudio/best",
    output_template="%(title)s.%(ext)s",
    output_path=Path("/downloads"),
    temp_path=Path("/tmp/ytdlp"),
    retries=10,
    fragment_retries=10,
    quiet=True,
    no_warnings=True,
    cookies_file=Path("cookies.txt"),
    proxy="socks5://127.0.0.1:1080",
    extract_audio=False,
    embed_thumbnail=False,
    embed_metadata=False,
    postprocessors=[
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
    ],
    # Любые yt-dlp опции, не охваченные typed полями
    raw_options={
        "some_future_option": "value",
    },
)

async with AsyncYTDLP(
    max_concurrency=4,
    default_options=options,
) as ytdlp:
    # Можно переопределить на уровне операции
    result = await ytdlp.download(
        url,
        options=YTDLPOptions(format="bestaudio/best"),
    )
```

### 1.9 Проверка зависимостей

```python
deps = await ytdlp.check_dependencies()
print(deps.ytdlp_version)      # str
print(deps.ffmpeg_available)    # bool
print(deps.ffprobe_available)   # bool
print(deps.ffmpeg_version)      # str | None
```

---

## 2. Архитектура компонентов

```
┌─────────────────────────────────────┐
│         Пользовательское            │
│         приложение                  │
└──────────────┬──────────────────────┘
               │
     ┌─────────▼─────────┐
     │    AsyncYTDLP      │  ← Главный клиент
     │    (client.py)     │     lifecycle, public API
     └─────────┬──────────┘
               │
     ┌─────────▼─────────┐
     │  DownloadManager   │  ← Concurrency control
     │   (manager.py)     │     Semaphore, queue
     └─────────┬──────────┘
               │
     ┌─────────▼─────────┐
     │  ThreadBackend     │  ← Execution layer
     │   (backend.py)     │     asyncio.to_thread()
     └─────────┬──────────┘
               │
     ┌─────────▼─────────┐
     │  yt_dlp.YoutubeDL  │  ← Синхронный yt-dlp
     │   (внешняя зав.)   │     в отдельном потоке
     └───────────────────┘
```

### 2.1 Слои

| Слой | Модуль | Ответственность |
|------|--------|----------------|
| **Client** | `client.py` | Public API, lifecycle (NEW→RUNNING→CLOSING→CLOSED), context manager |
| **Manager** | `manager.py` | Concurrency control (Semaphore), queue backpressure, graceful shutdown |
| **Backend** | `backend.py` | Мост async↔sync, thread execution, progress bridge, cancellation |
| **Options** | `options.py` | Typed конфигурация, merging, преобразование в raw yt-dlp params |
| **Models** | `models.py` | `MediaInfo`, `FormatInfo`, `DownloadResult`, `ThumbnailInfo`, etc. |
| **Progress** | `progress.py` | `ProgressEvent`, async bridge, throttling |
| **Errors** | `exceptions.py` | Иерархия исключений, маппинг yt-dlp → async-yt-dlp |
| **Logger** | `_logging.py` | Adapter для yt-dlp logger, redaction |

---

## 3. Execution Backend: Thread

### 3.1 Почему Thread, а не Subprocess

| Критерий | Thread | Subprocess |
|----------|--------|------------|
| Доступ к Python API | ✅ Полный | ❌ Только CLI |
| Progress hooks | ✅ Прямой callback | ❌ Парсинг stdout |
| info_dict | ✅ Полный typed dict | ❌ JSON из stdout |
| Postprocessor hooks | ✅ Да | ❌ Нет |
| Format selector callback | ✅ Да | ❌ Нет |
| Match filter callback | ✅ Да | ❌ Нет |
| Отмена | ⚠️ Cooperative | ✅ SIGTERM |
| Изоляция процесса | ❌ Общий процесс | ✅ Отдельный процесс |
| Memory footprint | ✅ Минимальный | ⚠️ Дублирование |
| Сложность реализации | ✅ Умеренная | ⚠️ Высокая (сериализация) |

**Решение**: Thread execution через `asyncio.to_thread()`.

Subprocess backend может быть добавлен в будущем (v2+), если возникнет потребность
в изоляции процессов. Архитектура позволяет это через `DownloadBackend` protocol.

### 3.2 Один YoutubeDL на операцию

YoutubeDL **не потокобезопасен**: мутабельное состояние (`_download_retcode`, `_num_downloads`,
cookie jar, `_request_director`) изменяется без защиты.

Поэтому: **каждая операция (extract/download) создаёт свой экземпляр YoutubeDL**.

```python
# В backend.py
def _run_sync(self, url: str, options: dict, ...) -> dict:
    with YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=download)
```

### 3.3 Thread Pool Strategy

Используем `asyncio.to_thread()` (default executor) + `asyncio.Semaphore(max_concurrency)`.

Не нужен отдельный `ThreadPoolExecutor`, потому что:
- `asyncio.to_thread()` уже использует default executor
- `Semaphore` контролирует параллельность на уровне asyncio
- Default executor автоматически масштабируется
- Меньше lifecycle-кода для управления

---

## 4. Concurrency Control

```python
class DownloadManager:
    def __init__(self, max_concurrency: int, queue_size: int):
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._active_count: int = 0
        self._closed: bool = False

    async def execute(self, operation, ...):
        if self._closed:
            raise RuntimeError("Manager закрыт")
        async with self._semaphore:
            self._active_count += 1
            try:
                return await operation()
            finally:
                self._active_count -= 1
```

Семафор гарантирует, что не будет больше `max_concurrency` одновременных
экземпляров yt-dlp.

---

## 5. Progress Bridge

### 5.1 Механизм

```
Worker Thread (sync)           Event Loop (async)
─────────────────              ────────────────────
yt-dlp вызывает               
progress_hook(dict)            
       │                       
       ▼                       
loop.call_soon_threadsafe(     
    queue.put_nowait, event)   
                               queue.get() ──▶ async for event
```

### 5.2 Реализация

```python
class ProgressBridge:
    """Мост между sync progress hooks yt-dlp и async consumers."""
    
    def __init__(self, loop: asyncio.AbstractEventLoop, throttle: float = 0.0):
        self._loop = loop
        self._queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue(maxsize=256)
        self._throttle = throttle
        self._last_emit = 0.0
    
    def sync_hook(self, progress_dict: dict) -> None:
        """Вызывается yt-dlp в worker thread."""
        now = time.monotonic()
        if self._throttle > 0 and (now - self._last_emit) < self._throttle:
            if progress_dict.get('status') == 'downloading':
                return  # Throttle downloading events
        self._last_emit = now
        event = ProgressEvent.from_ytdlp(progress_dict)
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
    
    def sync_pp_hook(self, pp_dict: dict) -> None:
        """Вызывается postprocessor'ами yt-dlp."""
        event = ProgressEvent.from_postprocessor(pp_dict)
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
    
    async def __aiter__(self):
        while True:
            event = await self._queue.get()
            if event is None:  # Sentinel: операция завершена
                break
            yield event
```

### 5.3 Throttling

- `downloading` события throttle по `throttle_interval` (default: 0)
- `finished`, `error`, postprocessor события НЕ throttle (всегда доставляются)
- Queue bounded (maxsize=256) — если consumer медленный, старые `downloading` события
  отбрасываются; важные события (`finished`, `error`) всегда доставляются

---

## 6. Cancellation Model

### 6.1 Честная документация

```
asyncio.CancelledError
        │
        ▼
  AsyncYTDLP.download()
        │
        ├── До входа в to_thread() → мгновенная отмена ✅
        ├── Во время ожидания Semaphore → мгновенная отмена ✅
        └── Во время выполнения yt-dlp в thread → ???
                │
                ├── asyncio Task отменяется ✅
                ├── CancelledError выбрасывается в await ✅
                ├── Результат yt-dlp отбрасывается ✅
                └── Но sync thread yt-dlp продолжает работу! ⚠️
                    (до естественного завершения операции)
```

**Yt-dlp в worker thread НЕ имеет внешнего API для остановки.**

Единственный механизм внутри yt-dlp: `DownloadCancelled` exception,
но его нельзя инжектировать в чужой thread извне.

### 6.2 Что делает обёртка

1. `CancelledError` → немедленно возвращает управление в async-код
2. Результат sync-операции (когда она завершится) отбрасывается
3. `.part` файлы остаются на диске (управляются yt-dlp)
4. Worker thread завершается естественно
5. При `close()` — ожидаем завершения всех активных потоков

### 6.3 Shutdown

```
close() / __aexit__()
    │
    ├── Устанавливаем _closed = True
    ├── Новые операции → RuntimeError
    ├── Ожидаем завершения активных операций
    └── Cleanup
```

---

## 7. Typed Models

### 7.1 MediaInfo

```python
@dataclass(frozen=True)
class MediaInfo:
    """Метаданные медиа-контента."""
    id: str
    title: str
    description: str | None
    duration: float | None
    uploader: str | None
    uploader_id: str | None
    channel: str | None
    channel_id: str | None
    channel_url: str | None
    webpage_url: str
    thumbnail: str | None
    ext: str | None
    filesize: int | None
    filesize_approx: int | None
    upload_date: str | None
    view_count: int | None
    like_count: int | None
    live_status: str | None
    age_limit: int | None
    categories: list[str]
    tags: list[str]
    
    # Playlist-specific
    is_playlist: bool
    entries: list[MediaInfo] | None
    playlist_count: int | None
    
    # Format information
    formats: list[FormatInfo]
    requested_formats: list[FormatInfo] | None
    subtitles: dict[str, list[SubtitleInfo]]
    thumbnails: list[ThumbnailInfo]
    
    # Raw yt-dlp dict (dict-like, может быть не JSON-serializable)
    raw_data: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable представление (через sanitize_info)."""
        ...
    
    @classmethod
    def from_ytdlp(cls, info_dict: dict[str, Any]) -> MediaInfo:
        """Создание из raw yt-dlp info_dict."""
        ...
```

### 7.2 FormatInfo

```python
@dataclass(frozen=True)
class FormatInfo:
    format_id: str
    ext: str | None
    width: int | None
    height: int | None
    fps: float | None
    vcodec: str | None
    acodec: str | None
    filesize: int | None
    filesize_approx: int | None
    tbr: float | None       # Total bitrate
    vbr: float | None       # Video bitrate
    abr: float | None       # Audio bitrate
    asr: int | None          # Audio sample rate
    format_note: str | None
    protocol: str | None
    resolution: str | None
    dynamic_range: str | None
    audio_channels: int | None
    has_video: bool
    has_audio: bool
    raw_data: dict[str, Any]
```

### 7.3 DownloadResult

```python
@dataclass(frozen=True)
class DownloadResult:
    filepath: Path
    info: MediaInfo
    elapsed: float
    requested_formats: list[FormatInfo] | None
```

### 7.4 ProgressEvent

```python
@dataclass(frozen=True)
class ProgressEvent:
    status: DownloadStatus
    
    # Download progress (status == DOWNLOADING)
    downloaded_bytes: int | None
    total_bytes: int | None
    total_bytes_estimate: int | None
    speed: float | None
    eta: float | None
    elapsed: float | None
    fragment_index: int | None
    fragment_count: int | None
    filename: str | None
    
    # Post-processing (status == POST_PROCESSING)
    postprocessor: str | None
    
    # Convenience
    @property
    def percent(self) -> float | None: ...
    @property
    def speed_str(self) -> str: ...
    @property
    def eta_str(self) -> str: ...
```

### 7.5 DownloadStatus

```python
class DownloadStatus(Enum):
    EXTRACTING = "extracting"
    DOWNLOADING = "downloading"
    FINISHED = "finished"            # Скачивание завершено
    POST_PROCESSING = "post_processing"
    COMPLETE = "complete"            # Вся операция завершена
    ERROR = "error"
    CANCELLED = "cancelled"
```

---

## 8. Иерархия исключений

```python
class AsyncYTDLPError(Exception):
    """Базовое исключение async-yt-dlp."""
    url: str | None
    job_id: str | None

class ExtractionError(AsyncYTDLPError):
    """Ошибка извлечения метаданных."""
    # Маппится из yt_dlp ExtractorError, GeoRestrictedError, UserNotLive

class DownloadError(AsyncYTDLPError):
    """Ошибка скачивания."""
    # Маппится из yt_dlp DownloadError

class PostProcessingError(AsyncYTDLPError):
    """Ошибка постобработки."""
    # Маппится из yt_dlp PostProcessingError

class ConfigurationError(AsyncYTDLPError):
    """Ошибка конфигурации."""

class ValidationError(AsyncYTDLPError):
    """Ошибка валидации входных данных."""

class TimeoutError(AsyncYTDLPError):
    """Превышен таймаут операции."""

class CancellationError(AsyncYTDLPError):
    """Операция отменена."""

class DependencyError(AsyncYTDLPError):
    """Отсутствует внешняя зависимость (ffmpeg, и т.д.)."""

class LifecycleError(AsyncYTDLPError):
    """Неправильное использование lifecycle."""
```

Все исключения используют exception chaining (`raise XError(...) from original`).

---

## 9. Options Merging

### 9.1 Приоритет (от низкого к высокому)

```
1. Внутренние defaults async-yt-dlp
2. default_options при создании AsyncYTDLP
3. options при вызове операции (extract_info, download)
4. raw_options (всегда имеют высший приоритет)
```

### 9.2 Typed → yt-dlp params

```python
class YTDLPOptions:
    def to_ytdlp_params(self) -> dict[str, Any]:
        """Преобразование typed опций в raw dict для YoutubeDL."""
        params = {}
        if self.format is not None:
            params["format"] = self.format
        if self.output_template is not None:
            params["outtmpl"] = {"default": self.output_template}
        if self.output_path is not None:
            params["paths"] = {"home": str(self.output_path)}
        # ...
        # raw_options перезаписывают всё
        if self.raw_options:
            params.update(self.raw_options)
        return params
```

---

## 10. Logging

### 10.1 YT-DLP Logger Adapter

```python
class YTDLPLoggerAdapter:
    """Перехватывает вывод yt-dlp и перенаправляет в стандартный logging."""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def debug(self, msg: str) -> None:
        if msg.startswith("[debug] "):
            self._logger.debug(msg[8:])
        else:
            self._logger.info(msg)
    
    def info(self, msg: str) -> None:
        self._logger.info(msg)
    
    def warning(self, msg: str) -> None:
        self._logger.warning(msg)
    
    def error(self, msg: str) -> None:
        self._logger.error(msg)
```

### 10.2 Redaction

```python
SENSITIVE_KEYS = frozenset({
    "password", "videopassword", "username", "twofactor",
    "client_certificate_password", "proxy", "cookiefile",
})

SENSITIVE_HEADERS = frozenset({
    "authorization", "cookie", "set-cookie", "proxy-authorization",
})

def redact_options(options: dict) -> dict:
    """Маскирует секретные данные для логирования."""
    ...
```

---

## 11. Lifecycle

```python
class ClientState(Enum):
    NEW = "new"
    RUNNING = "running"
    CLOSING = "closing"
    CLOSED = "closed"

class AsyncYTDLP:
    async def __aenter__(self) -> Self:
        self._state = ClientState.RUNNING
        return self
    
    async def __aexit__(self, *exc) -> None:
        await self.close()
    
    async def close(self) -> None:
        if self._state == ClientState.CLOSED:
            return
        self._state = ClientState.CLOSING
        # Ожидаем завершения активных операций
        await self._manager.shutdown()
        self._state = ClientState.CLOSED
    
    def _ensure_running(self) -> None:
        if self._state != ClientState.RUNNING:
            raise LifecycleError(
                f"AsyncYTDLP в состоянии {self._state.value}, "
                f"операции доступны только в состоянии RUNNING"
            )
```

---

## 12. Backend Protocol

```python
class DownloadBackend(Protocol):
    """Протокол для execution backend."""
    
    async def extract_info(
        self,
        url: str,
        params: dict[str, Any],
        download: bool = False,
    ) -> dict[str, Any]: ...
    
    async def download(
        self,
        url: str,
        params: dict[str, Any],
        progress_bridge: ProgressBridge | None = None,
    ) -> dict[str, Any]: ...
    
    async def close(self) -> None: ...
```

---

## 13. Структура проекта

```
async-yt-dlp/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── .gitignore
├── .editorconfig
│
├── src/
│   └── async_yt_dlp/
│       ├── __init__.py          # Public exports
│       ├── client.py            # AsyncYTDLP — главный клиент
│       ├── manager.py           # DownloadManager — concurrency
│       ├── backend.py           # ThreadBackend — sync↔async мост
│       ├── options.py           # YTDLPOptions — typed конфигурация
│       ├── models.py            # MediaInfo, FormatInfo, DownloadResult, etc.
│       ├── progress.py          # ProgressEvent, ProgressBridge, throttling
│       ├── exceptions.py        # Иерархия исключений
│       ├── _logging.py          # Logger adapter, redaction
│       ├── _validation.py       # URL validation, input sanitization
│       ├── _dependencies.py     # Проверка зависимостей (ffmpeg, etc.)
│       └── _constants.py        # Версия, defaults
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_options.py
│   │   ├── test_models.py
│   │   ├── test_progress.py
│   │   ├── test_exceptions.py
│   │   ├── test_logging.py
│   │   ├── test_validation.py
│   │   └── test_lifecycle.py
│   ├── integration/
│   │   ├── test_extract.py
│   │   ├── test_download.py
│   │   ├── test_progress_bridge.py
│   │   ├── test_concurrency.py
│   │   └── test_cancellation.py
│   └── e2e/
│       └── test_real_downloads.py
│
├── examples/
│   ├── simple_extract.py
│   ├── simple_download.py
│   ├── progress.py
│   ├── playlist.py
│   ├── audio_extraction.py
│   ├── custom_options.py
│   ├── cancellation.py
│   ├── concurrency.py
│   └── integrations/
│       └── telegram_aiogram.py
│
├── docs/
│   ├── getting-started.md
│   ├── architecture.md
│   ├── api.md
│   ├── api-design.md
│   ├── configuration.md
│   ├── concurrency.md
│   ├── cancellation.md
│   ├── progress.md
│   ├── errors.md
│   ├── security.md
│   ├── performance.md
│   ├── deployment.md
│   ├── development.md
│   ├── testing.md
│   ├── troubleshooting.md
│   ├── migration.md
│   └── research.md
│
├── Dockerfile
├── docker-compose.yml
│
└── .gitea/
    └── workflows/
        └── ci.yml
```

---

## 14. Почему не просто `asyncio.to_thread`

Простая обёртка:
```python
async def download(url):
    return await asyncio.to_thread(YoutubeDL().download, [url])
```

**Не решает:**

| Проблема | Решение в async-yt-dlp |
|----------|----------------------|
| Concurrency control | `Semaphore` + `DownloadManager` |
| Lifecycle management | `ClientState` + context manager |
| Cancellation semantics | Documented cooperative model |
| Progress bridge | `ProgressBridge` + `call_soon_threadsafe` |
| Cleanup | Graceful shutdown + resource tracking |
| Backpressure | Bounded queue, Semaphore |
| Structured concurrency | Scoped operations, no orphan threads |
| Typed API | `MediaInfo`, `FormatInfo`, `DownloadResult` |
| Error abstraction | Mapped exception hierarchy |
| Thread safety | One YoutubeDL per operation |
| Secret redaction | Logger adapter + redaction |
| Dependency checks | `check_dependencies()` |
