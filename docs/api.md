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
- `get_available_resolutions() -> list[int]`: отсортированный по убыванию список доступных разрешений (например, `[2160, 1440, 1080, 720, 480, 360, 240, 144]`).
- `estimate_size(height: int | None = None) -> int | None`: расчетный суммарный размер файла (видео + аудио) в байтах.
- `estimate_size_str(height: int | None = None) -> str`: форматированный расчетный размер файла (например, `'62.01 MiB'`).
- `get_best_video_format(height: int | None = None, container: str | None = None) -> FormatInfo | None`: лучший видеопоток.
- `get_best_audio_format() -> FormatInfo | None`: лучший аудиопоток.
- `get_video_formats(height: int | None = None, container: str | None = None) -> list[FormatInfo]`: список доступных видеопотоков.
- `get_audio_formats() -> list[FormatInfo]`: список доступных аудиопотоков без видео.


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

---

## 3. Классы конфигурации

### `YTDLPOptions` (frozen dataclass)
- `format` (`FormatSelector | str | None`): селектор формата (объект или строка).
- `output_template` (`OutputTemplate | str | None`): шаблон имени файла.
- `output_path` (`Path | None`): директория сохранения.
- `container` (`VideoContainer | str | None`): принудительный медиа-контейнер (remux через ffmpeg).
- `auto_detect_js` (`bool`): автоматический поиск в системе и подключение JS-рантаймов (`Node.js`, `Deno`, `Bun`) для YouTube EJS. По умолчанию `True`.
- `js_runtimes` (`dict[str, dict[str, Any]] | None`): явная конфигурация сред исполнения JS.
- `no_warnings` (`bool`): перенаправление служебных предупреждений ядра в уровень DEBUG (исключение шума в терминале). По умолчанию `True`.
- `quiet` (`bool`): подавление стандартных информационных сообщений `yt-dlp`.
- `extract_audio` (`bool`): флаг извлечения только аудиопотока.
- `audio_format` (`AudioFormat | str | None`): целевой формат аудио (`mp3`, `m4a`, `flac`, `opus`, `wav`).
- `ffmpeg_location` (`Path | str | None`): путь к исполняемому файлу ffmpeg.
- `proxy` (`str | None`): URL прокси-сервера.
- `raw_options` (`dict[str, Any]`): словарь низкоуровневых параметров `yt-dlp` наивысшего приоритета.
- `merge(other: YTDLPOptions) -> YTDLPOptions`: объединение двух конфигураций.
- `to_safe_dict() -> dict[str, Any]`: маскированное представление для безопасного логирования.

### `FormatSelector`
- **Универсальная фабрика**: `FormatSelector.resolution(height, container=None, fps=None, exact=False)`.
- **Пресеты разрешений**: `preset_144p()`, `preset_240p()`, `preset_360p()`, `preset_480p()`, `preset_720p()`, `preset_1080p()`, `preset_1440p()` / `preset_2k()`, `preset_2160p()` / `preset_4k()`, `preset_4320p()` / `preset_8k()`.
- **Специальные пресеты**: `preset_max_quality()`, `preset_worst()`, `preset_best_audio()`, `preset_audio_only(ext)`, `preset_compatibility()`, `preset_telegram(max_size_mb)`.
- **Конструкторы**: `FormatSelector.video()`, `FormatSelector.audio()`.
- **Fluent-методы**: `max_height(h)`, `min_height(h)`, `exact_height(h)`, `ext(extension)`, `container(c)`, `vcodec(codec)`, `acodec(codec)`, `max_fps(rate)`, `merge(audio_selector)`, `fallback(other)`.
- `build() -> str`: генерация валидной строки селектора формата `yt-dlp`.


### `OutputTemplate`
- **Пресеты**: `title_only()`, `title_and_id()`, `dated()`, `playlist_folder()`, `channel_folder()`.
- **Fluent-методы**: `title()`, `id()`, `ext()`, `channel()`, `uploader()`, `dir()`, `custom(spec)`.
- **Оператор `/`**: конкатенация каталогов и шаблонов (`OutputTemplate().channel() / OutputTemplate.title_only()`).
- `build() -> str`: генерация строки шаблона.

### `VideoContainer` (Enum)
- Значения: `MP4`, `MKV`, `WEBM`, `MOV`, `AVI`, `FLV`, `TS`.

---

## 4. Диагностика окружения

### `DependencyInfo` (frozen dataclass)
Результат выполнения метода `await ytdlp.check_dependencies()`:
- `ytdlp_version` (`str | None`): версия установленной библиотеки `yt-dlp`.
- `ffmpeg_available` (`bool`): доступность `ffmpeg`.
- `ffmpeg_path` (`str | None`): путь к бинарному файлу `ffmpeg`.
- `ffmpeg_version` (`str | None`): версия `ffmpeg`.
- `ffprobe_available` (`bool`): доступность `ffprobe`.
- `has_aio_ffmpeg` (`bool`): установлен ли пакет `aio-ffmpeg` для асинхронной постобработки.
- `js_runtimes` (`dict[str, dict[str, Any]]`): словарь обнаруженных в системе JS-рантаймов (Node.js, Deno, Bun).

