# Справочник публичного API async-yt-dlp

Полное описание классов, методов и типов данных библиотеки `async_yt_dlp`.

---

## 1. Класс `AsyncYTDLP`

Главная точка входа в библиотеку.

```python
class AsyncYTDLP:
    def __init__(
        self,
        *,
        max_concurrency: int = 4,
        queue_size: int = 100,
        default_options: YTDLPOptions | None = None,
        backend: DownloadBackend | None = None,
    ) -> None:
```

### Параметры конструктора:
- `max_concurrency` (`int`): максимальное число одновременно выполняемых операций yt-dlp.
- `queue_size` (`int`): максимальное количество задач, ожидающих в очереди семафора.
- `default_options` (`YTDLPOptions | None`): базовые параметры yt-dlp для всех вызовов клиента.
- `backend` (`DownloadBackend | None`): бэкенд выполнения (по умолчанию `ThreadBackend`).

### Свойства:
- `state` (`ClientState`): текущее состояние (`NEW`, `RUNNING`, `CLOSING`, `CLOSED`).
- `is_closed` (`bool`): находится ли клиент в процессе закрытия или закрыт.

### Методы:

#### `async def extract_info(...) -> MediaInfo`
Извлекает нормализованные метаданные видео или плейлиста.
```python
async def extract_info(
    self,
    url: str,
    *,
    download: bool = False,
    options: YTDLPOptions | None = None,
    extra_info: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> MediaInfo:
```

#### `async def download(...) -> DownloadResult`
Скачивает медиа-ресурс и выполняет постобработку.
```python
async def download(
    self,
    url: str,
    *,
    options: YTDLPOptions | None = None,
    on_progress: Callable[[ProgressEvent], Any] | None = None,
    extra_info: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> DownloadResult:
```

#### `async def download_with_progress(...) -> AsyncIterator[ProgressEvent]`
Асинхронный генератор для чтения событий прогресса в реальном времени.
```python
async def download_with_progress(
    self,
    url: str,
    *,
    options: YTDLPOptions | None = None,
    throttle_interval: float = 0.5,
    extra_info: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> AsyncIterator[ProgressEvent]:
```

#### `async def download_many(...) -> list[DownloadResult | AsyncYTDLPError]`
Пакетное параллельное скачивание нескольких URL на базе `asyncio.TaskGroup`.
```python
async def download_many(
    self,
    urls: Sequence[str],
    *,
    options: YTDLPOptions | None = None,
    on_error: ErrorPolicy = ErrorPolicy.COLLECT,
) -> list[DownloadResult | AsyncYTDLPError]:
```

#### `async def check_dependencies(...) -> DependencyInfo`
Проверяет окружение и доступность `yt-dlp`, `ffmpeg`, `ffprobe` и сред JavaScript.

#### `async def close(wait: bool = True, timeout: float | None = 15.0) -> None`
Выполняет корректное завершение работы менеджера и бэкенда.

---

## 2. Модели данных

### `MediaInfo` (frozen dataclass)
- `id` (`str`): идентификатор ресурса.
- `title` (`str`): название.
- `duration` (`float | None`): длительность в секундах.
- `duration_seconds` (`int | None`): длительность в целых секундах.
- `uploader` (`str | None`): имя автора.
- `webpage_url` (`str`): канонический URL.
- `ext` (`str | None`): расширение файла.
- `filesize` (`int | None`): размер в байтах.
- `is_playlist` (`bool`): является ли плейлистом.
- `entries` (`tuple[MediaInfo, ...] | None`): список элементов для плейлиста.
- `formats` (`tuple[FormatInfo, ...]`): доступные форматы.
- `thumbnails` (`tuple[ThumbnailInfo, ...]`): обложки и миниатюры.
- `subtitles` (`dict[str, tuple[SubtitleInfo, ...]]`): дорожки субтитров по языкам.
- `raw_data` (`dict[str, Any]`): полный исходный словарь yt-dlp.
- `to_dict(remove_private_keys=False) -> dict[str, Any]`: безопасное JSON-представление.

### `FormatInfo` (frozen dataclass)
- `format_id` (`str`): ID формата (например, '137', '22', 'ba').
- `ext` (`str | None`): расширение.
- `width` / `height` (`int | None`): разрешение видео.
- `fps` (`float | None`): частота кадров.
- `vcodec` / `acodec` (`str | None`): кодеки.
- `filesize` (`int | None`): размер потока.
- `tbr`, `vbr`, `abr` (`float | None`): битрейты.
- `has_video` / `has_audio` (`bool`): наличие видео/аудио потоков.

### `DownloadResult` (frozen dataclass)
- `filepath` (`Path`): финальный путь к файлу.
- `filename` (`str`): имя файла.
- `exists` (`bool`): существует ли файл на диске.
- `file_size` (`int`): размер файла в байтах.
- `elapsed` (`float`): затраченное время в секундах.
- `info` (`MediaInfo`): метаданные медиа.

### `ProgressEvent` (frozen dataclass)
- `status` (`DownloadStatus`): `DOWNLOADING`, `FINISHED`, `POST_PROCESSING`, `COMPLETE`, `ERROR`.
- `downloaded_bytes` (`int | None`): скачано байт.
- `total_bytes` (`int | None`): общий размер.
- `speed` (`float | None`): скорость (байт/с).
- `eta` (`float | None`): осталось секунд.
- `percent` (`float | None`): процент выполнения (0.0 - 100.0).
- `speed_str` (`str`): форматированная скорость (например, '2.45 MiB/s').
- `eta_str` (`str`): форматированное время (например, '01:23').
- `postprocessor` (`str | None`): название текущего постпроцессора.
