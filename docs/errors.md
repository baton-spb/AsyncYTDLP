# Обработка ошибок и иерархия исключений

Библиотека `async-yt-dlp` предоставляет строгую иерархию типизированных исключений.
Любая ошибка содержит контекст (исходный URL и `job_id`), а также сохраняет
оригинальную причину сбоя через механизм exception chaining (`from exc`).

---

## 1. Дерево исключений

```text
AsyncYTDLPError (Базовый класс, содержит url и job_id)
├── ExtractionError         (Ошибки парсинга страницы, недоступности видео, гео-блокировок)
├── DownloadError           (Сетевые ошибки, сбои серверов CDN, ошибки записи на диск)
├── PostProcessingError     (Сбои ffmpeg/ffprobe, ошибки конвертации или слияния)
├── ConfigurationError      (Некорректная комбинация настроек)
├── ValidationError         (Невалидный URL, запрещенная схема, некорректный путь)
├── OperationTimeoutError   (Превышение допустимого времени ожидания)
├── CancellationError       (Операция отменена по инициативе пользователя)
├── DependencyError         (Отсутствие необходимых бинарников ffmpeg/ffprobe)
├── LifecycleError          (Попытка вызова метода на закрытом клиенте)
└── QueueFullError          (Переполнение очереди ожидания семафора)
```

---

## 2. Примеры обработки исключений

### Обработка недоступных видео или ошибок сети
```python
from async_yt_dlp import (
    AsyncYTDLP,
    DownloadError,
    ExtractionError,
    PostProcessingError,
)

async with AsyncYTDLP() as ytdlp:
    try:
        result = await ytdlp.download("https://www.youtube.com/watch?v=invalid_id")
    except ExtractionError as err:
        print(f"Видео удалено или недоступно: {err}")
        print(f"URL: {err.url}, ID задачи: {err.job_id}")
    except DownloadError as err:
        print(f"Ошибка загрузки файлов: {err}")
    except PostProcessingError as err:
        print(f"Ошибка конвертации ffmpeg: {err}")
    except AsyncYTDLPError as err:
        print(f"Общая ошибка библиотеки: {err}")
```

### Доступ к оригинальному исключению (Chaining)
Вы всегда можете получить исходное исключение ядра `yt-dlp` через атрибут `__cause__`:

```python
try:
    await ytdlp.extract_info(url)
except ExtractionError as err:
    original_exc = err.__cause__
    print(f"Исходное исключение yt-dlp: {type(original_exc).__name__}: {original_exc}")
```

---

## 3. Обработка перегрузки и очередей
```python
from async_yt_dlp import QueueFullError

try:
    await ytdlp.download(url)
except QueueFullError:
    print("Сервер перегружен: очередь задач заполнена. Повторите попытку позже.")
```
