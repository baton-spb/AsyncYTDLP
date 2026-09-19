# Исследование yt-dlp для async-yt-dlp

## 1. Архитектура yt-dlp

### 1.1 Основной поток выполнения

```
download(url_list)
  → для каждого url:
    → extract_info(url, download=True)
      → ie.extract(url)                    # Поиск и запуск подходящего экстрактора
      → process_ie_result(ie_result)
        → [playlist] → итерация по entries, рекурсивная обработка
        → [single]   → process_video_result(info_dict)
          → format selection                # Выбор формата
          → prepare_filename()              # Подготовка имени файла
          → process_info(info_dict)
            → dl(filename, info_dict)       # Фактическое скачивание
            → run_all_pps(info_dict)        # Постобработка
            → record_download_archive()     # Запись в архив
```

### 1.2 Ключевые классы

| Класс | Модуль | Назначение |
|-------|--------|------------|
| `YoutubeDL` | `yt_dlp/YoutubeDL.py` | Главный координатор |
| `InfoExtractor` | `yt_dlp/extractor/common.py` | Базовый экстрактор |
| `FileDownloader` | `yt_dlp/downloader/common.py` | Базовый загрузчик |
| `PostProcessor` | `yt_dlp/postprocessor/common.py` | Базовый постпроцессор |
| `RequestDirector` | `yt_dlp/networking/common.py` | HTTP-клиент |
| `FormatSorter` | `yt_dlp/utils/_utils.py` | Сортировка форматов |

### 1.3 Экспортируемые сущности (`__init__.py`)

- **Ошибки**: `DownloadCancelled`, `DownloadError`, `SameFileError`, `UnsafeExecExpansionError`, `CookieLoadError`
- **Постпроцессоры**: `FFmpegExtractAudioPP`, `FFmpegMergerPP`, `FFmpegPostProcessor`, и др.
- **Утилиты**: `expand_path`, `shell_quote`, `read_batch_urls`, `format_field`, `match_filter_func`
- **Классы**: `FormatSorter`, `GeoUtils`, `PlaylistEntries`, `DateRange`

---

## 2. YoutubeDL API

### 2.1 Конструктор

```python
def __init__(self, params=None, auto_init=True):
```

- `params` — словарь с ~200+ опциями
- `auto_init` — загружать ли экстракторы при инициализации

### 2.2 Ключевые методы

| Метод | Сигнатура | Возвращает |
|-------|-----------|------------|
| `extract_info` | `(url, download=True, ie_key=None, extra_info=None, process=True, force_generic_extractor=False)` | `dict \| None` |
| `download` | `(url_list)` | `int` (0=success, 1=error) |
| `sanitize_info` | `(info_dict, remove_private_keys=False)` | `dict` (JSON-serializable) |
| `prepare_filename` | `(info_dict, dir_type='', *, outtmpl=None, warn=False)` | `str` |
| `close` | `()` | `None` |

### 2.3 Тип возвращаемого значения `extract_info()`

> **КРИТИЧЕСКИ ВАЖНО**: Результат `extract_info()` НЕ гарантирован как JSON-serializable dict.

Может содержать:
- Генераторы (для `entries` в плейлистах)
- `LazyList` / `PagedList` объекты
- Callable объекты
- Внутренние ключи, начинающиеся с `_`

Для получения JSON-serializable результата: `YoutubeDL.sanitize_info(info)`.

### 2.4 Контекстный менеджер

```python
def __enter__(self):
    self.save_console_title()
    return self

def __exit__(self, *args):
    self.restore_console_title()
    self.close()
```

`close()` закрывает `_request_director`, сохраняет cookies. Не имеет защиты от двойного вызова.

---

## 3. Потокобезопасность

### 3.1 Вывод: YoutubeDL НЕ потокобезопасен

Мутабельное состояние без защиты:
- `_download_retcode` — целочисленный флаг ошибки
- `_num_downloads` — счётчик скачиваний
- `_printed_messages` — набор выведенных сообщений
- Cookie jar — общее состояние
- `_request_director` — HTTP-сессия

Единственная защита: `_file_access_lock = threading.Lock()` — только для файловых операций.

### 3.2 Решение для обёртки

**Один экземпляр `YoutubeDL` на одну операцию (extract/download).**

Нельзя переиспользовать один экземпляр для параллельных скачиваний из разных потоков.

---

## 4. Progress Hooks

### 4.1 Download Progress Hooks

Регистрация: `params['progress_hooks']` или `ydl.add_progress_hook(ph)`

Вызываются синхронно в потоке загрузки.

#### Поля при `status == 'downloading'`:
| Поле | Тип | Описание |
|------|-----|----------|
| `status` | `str` | `'downloading'` |
| `info_dict` | `dict` | Информация о видео |
| `filename` | `str` | Финальное имя файла |
| `tmpfilename` | `str` | Временное имя файла |
| `downloaded_bytes` | `int` | Скачано байт |
| `total_bytes` | `int \| None` | Общий размер |
| `total_bytes_estimate` | `int \| None` | Оценочный размер |
| `elapsed` | `float` | Прошло секунд |
| `eta` | `float \| None` | Осталось секунд |
| `speed` | `float \| None` | Скорость (байт/с) |
| `fragment_index` | `int \| None` | Индекс фрагмента |
| `fragment_count` | `int \| None` | Всего фрагментов |

#### Поля при `status == 'finished'`:
| Поле | Тип | Описание |
|------|-----|----------|
| `status` | `str` | `'finished'` |
| `downloaded_bytes` | `int` | Всего скачано |
| `total_bytes` | `int` | Общий размер |
| `elapsed` | `float` | Время скачивания |

#### Поля при `status == 'error'`:
| Поле | Тип | Описание |
|------|-----|----------|
| `status` | `str` | `'error'` |
| `error` | `any` | Информация об ошибке |

### 4.2 Postprocessor Hooks

Регистрация: `params['postprocessor_hooks']` или `ydl.add_postprocessor_hook(ph)`

#### Поля:
| Поле | Тип | Описание |
|------|-----|----------|
| `status` | `str` | `'started'` или `'finished'` |
| `postprocessor` | `str` | Имя постпроцессора |
| `info_dict` | `dict` | Информация о видео |

---

## 5. Стадии постобработки (POSTPROCESS_WHEN)

```python
POSTPROCESS_WHEN = (
    'pre_process',     # До начала обработки
    'after_filter',    # После фильтрации
    'video',           # Для каждого видео (после загрузки)
    'before_dl',       # Перед загрузкой
    'post_process',    # Основная постобработка (default)
    'after_move',      # После перемещения файла
    'after_video',     # После всего цикла для видео
    'playlist',        # Для всего плейлиста
)
```

---

## 6. Иерархия исключений yt-dlp

```
YoutubeDLError (base)
├── ExtractorError
│   ├── GeoRestrictedError
│   └── UserNotLive
├── DownloadError
├── DownloadCancelled
│   └── MaxDownloadsReached
├── PostProcessingError
│   └── AudioConversionError
├── SameFileError
├── UnsafeExecExpansionError
└── CookieLoadError
```

Особенности:
- `ExtractorError` хранит `exc_info`, `cause`, `video_id`
- `DownloadError` хранит `exc_info`
- `DownloadCancelled` — механизм отмены внутри yt-dlp
- `MaxDownloadsReached` наследует `DownloadCancelled`

---

## 7. Блокирующие операции

### 7.1 Что реально блокирует event loop

| Операция | Блокирует? | Длительность |
|----------|-----------|--------------|
| `extract_info()` | ✅ Да | Секунды — десятки секунд (сетевые запросы) |
| `download()` | ✅ Да | Секунды — часы (скачивание файла) |
| `process_info()` | ✅ Да | Включает download + postprocessing |
| `sanitize_info()` | ⚠️ Незначительно | Миллисекунды (CPU-bound) |
| `prepare_filename()` | ⚠️ Незначительно | Микросекунды |
| `close()` | ⚠️ Может | Сохранение cookies + закрытие соединений |
| Постобработка (ffmpeg) | ✅ Да | Секунды — минуты |
| `slow_down()` | ✅ Да | `time.sleep()` для rate limit |

### 7.2 Операции внутри скачивания

- HTTP-запросы (blocking I/O)
- Запись на диск (blocking I/O)
- `time.sleep()` в rate limiting
- ffmpeg subprocess (blocking wait)
- Фрагментированное скачивание может использовать `ThreadPoolExecutor`

---

## 8. Аутентификация и секреты

### 8.1 Опции, содержащие секретные данные

| Параметр | Тип | Содержимое |
|----------|-----|------------|
| `password` | `str` | Пароль учётной записи |
| `videopassword` | `str` | Пароль для видео |
| `cookiefile` | `str` | Путь к файлу cookies (не секрет сам по себе) |
| `cookiesfrombrowser` | `tuple` | Браузер/профиль |
| `proxy` | `str` | URL прокси (может содержать credentials) |
| `client_certificate_password` | `str` | Пароль TLS-ключа |
| `netrc_location` | `str` | Путь к .netrc |
| `username` | `str` | Имя пользователя |
| `twofactor` | `str` | 2FA код |
| Заголовки (`http_headers`) | `dict` | Могут содержать `Authorization`, cookies |
| `extractor_args` | `dict` | Могут содержать токены (po_token, api_key) |

### 8.2 Необходимая редакция при логировании

Ключи для маскирования: `password`, `videopassword`, `proxy`, `client_certificate_password`,
`username`, `twofactor`, а также значения заголовков `Authorization`, `Cookie`, `Set-Cookie`.

---

## 9. Файловая система

### 9.1 Поведение yt-dlp

- Использует `.part` файлы во время скачивания (контролируется `nopart`)
- `prepare_filename()` санитизирует имена файлов
- `sanitize_filename()` удаляет небезопасные символы
- `sanitize_path()` обрабатывает Windows-специфичные ограничения
- `restrictfilenames` — только ASCII
- `windowsfilenames` — принудительная совместимость с Windows
- `trim_file_name` — ограничение длины имени файла
- Временные файлы создаются в каталоге `paths['temp']`

### 9.2 Финальный путь к файлу

После постобработки `info_dict` содержит ключ `filepath` — это финальный путь.
Он может отличаться от `filename`, если постпроцессор изменил расширение или имя.

---

## 10. Зависимости yt-dlp

### 10.1 Обязательные
- Python ≥ 3.10 (CPython) / ≥ 3.11 (PyPy)
- `certifi`, `requests`, `urllib3`

### 10.2 Настоятельно рекомендуемые
- **ffmpeg + ffprobe** — внешние бинарники (НЕ Python package!)
- **yt-dlp-ejs** — для JavaScript-интерпретации
- **JS runtime** — deno (рекомендуется), node, bun, quickjs

### 10.3 Опциональные
- `curl_cffi` — TLS-fingerprint импersonация
- `mutagen` — встраивание метаданных в аудио
- `pycryptodomex` — AES-128 расшифровка
- `websockets` — скачивание через WebSocket
- `brotli` / `brotlicffi` — Brotli encoding

---

## 11. Плагины

### 11.1 Структура
```
yt_dlp_plugins/
    extractor/
        myplugin.py
    postprocessor/
        myplugin.py
```

### 11.2 Каталоги поиска
- `${XDG_CONFIG_HOME}/yt-dlp/plugins/`
- `${APPDATA}/yt-dlp/plugins/` (Windows)
- `~/.yt-dlp/plugins/`
- `--plugin-dirs` аргумент
- `YTDLP_PLUGIN_DIRS` переменная окружения

### 11.3 Для обёртки
Обёртка не должна ломать плагины. Все настройки (`plugin_dirs`, `YTDLP_NO_PLUGINS`)
должны пробрасываться без модификации.

---

## 12. Retry-механизмы yt-dlp

| Параметр | Умолчание | Описание |
|----------|-----------|----------|
| `retries` | 10 | Попытки скачивания |
| `fragment_retries` | 10 | Попытки для фрагментов |
| `file_access_retries` | 3 | Попытки доступа к файлам |
| `extractor_retries` | 3 | Попытки при ошибках экстрактора |
| `retry_sleep_functions` | `{}` | Функции задержки между попытками |

Wrapper НЕ должен дублировать эти retry-механизмы. Они должны пробрасываться
как параметры yt-dlp.

---

## 13. Лицензия

- Основной код: **The Unlicense** (public domain)
- Бинарные сборки: GPLv3+ (из-за PyInstaller)
- Зависимости имеют свои лицензии (MIT, Apache-2.0, BSD, GPLv2+)

Для async-yt-dlp рекомендуется MIT или The Unlicense (совместимо с yt-dlp).

---

## 14. Python 3.14 asyncio возможности

### 14.1 Доступные API

| API | Версия | Использование |
|-----|--------|---------------|
| `asyncio.TaskGroup` | 3.11+ | Structured concurrency |
| `asyncio.timeout()` | 3.11+ | Дедлайн-based таймауты |
| `asyncio.to_thread()` | 3.9+ | Запуск блокирующего кода |
| `asyncio.Queue.shutdown()` | 3.13+ | Graceful shutdown очереди |
| `asyncio.Semaphore` | давно | Ограничение параллельности |
| `ExceptionGroup` | 3.11+ | Группировка исключений |
| `except*` | 3.11+ | Обработка ExceptionGroup |
| `contextvars` с `to_thread` | 3.9+ | Автоматическое копирование контекста |

### 14.2 Ключевые особенности

- `asyncio.to_thread()` копирует `contextvars.Context` в поток — полезно для `job_id`
- `asyncio.Queue.shutdown()` вызывает `QueueShutDown` у ожидающих consumer'ов
- `TaskGroup` гарантирует завершение всех задач при выходе
- `asyncio.timeout()` конвертирует `CancelledError` в `TimeoutError`
- `to_thread()` НЕ МОЖЕТ отменить уже работающий sync-код

---

## 15. Выводы для архитектуры

### 15.1 Execution Backend

**Решение: Thread execution (не subprocess)**

Причины:
1. Python API yt-dlp значительно богаче CLI
2. Прямой доступ к `extract_info()`, `sanitize_info()`, progress hooks
3. Не нужен парсинг stdout/stderr subprocess
4. Typed progress events через hooks
5. Доступ к полному `info_dict`
6. Subprocess добавил бы сложность сериализации без выгоды

### 15.2 Concurrency Model

```
AsyncYTDLP
  → asyncio.Semaphore (max_concurrency)
  → для каждой операции:
    → asyncio.to_thread(sync_operation)
    → отдельный YoutubeDL instance на операцию
```

Не нужен `ThreadPoolExecutor` с фиксированным пулом worker'ов — `asyncio.to_thread()`
использует default executor, а `Semaphore` контролирует параллельность.

### 15.3 Progress Bridge

```
worker thread
  → sync progress_hook callback
  → asyncio.Queue (thread-safe put_nowait через loop.call_soon_threadsafe)
  → async consumer (async for event in queue)
```

### 15.4 Cancellation Model

1. **До начала**: Задача отменяется до входа в `to_thread` → стандартный `CancelledError`
2. **Во время ожидания семафора**: `CancelledError` → задача не запускается
3. **Во время выполнения**: `CancelledError` НЕ останавливает sync-поток!
   - Устанавливаем флаг `_cancelled = True`
   - Поток продолжает работу до естественного завершения
   - Результат отбрасывается
4. **Cleanup**: Временные файлы остаются (yt-dlp управляет .part файлами)

### 15.5 Lifecycle

```
NEW → RUNNING → CLOSING → CLOSED
```

- `async with AsyncYTDLP()` — управляет lifecycle
- `close()` — прекращает приём новых задач, ожидает завершения активных
- После `close()` — любой вызов → `RuntimeError`
