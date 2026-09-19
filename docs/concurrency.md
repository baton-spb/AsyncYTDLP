# Управление параллельностью и очередями в async-yt-dlp

Скачивание видео и конвертация через `ffmpeg` — это ресурсоемкие операции, которые интенсивно
нагружают сетевой канал, диск и процессор.

Библиотека `async-yt-dlp` предоставляет встроенный механизм контроля параллельности
и защиту от перегрузки (backpressure).

---

## 1. Параметры параллельности `AsyncYTDLP`

При создании клиента задаются два ключевых параметра:

```python
from async_yt_dlp import AsyncYTDLP

ytdlp = AsyncYTDLP(
    max_concurrency=4,  # Не более 4 параллельно работающих потоков yt-dlp
    queue_size=100,     # До 100 запросов могут ожидать своей очереди в семафоре
)
```

### Как это работает:
1. `max_concurrency`:
   - Управляется с помощью `asyncio.Semaphore`.
   - Гарантирует, что ни при каких обстоятельствах в системе не будет одновременно запущено более `max_concurrency` потоков `YoutubeDL`.
2. `queue_size`:
   - Если все `max_concurrency` слотов заняты, новые запросы становятся в очередь ожидания.
   - Если количество ожидающих задач превышает `queue_size`, библиотека немедленно выбрасывает исключение `QueueFullError`, предотвращая неконтролируемое накопление задач в памяти (backpressure).

---

## 2. Пакетная загрузка: `download_many`

Для эффективной одновременной загрузки нескольких URL используйте метод `download_many`:

```python
import asyncio
from async_yt_dlp import AsyncYTDLP, ErrorPolicy

async def main():
    urls = [
        "https://www.youtube.com/watch?v=1",
        "https://www.youtube.com/watch?v=2",
        "https://www.youtube.com/watch?v=3",
    ]

    async with AsyncYTDLP(max_concurrency=2) as ytdlp:
        # download_many использует structured concurrency (asyncio.TaskGroup)
        results = await ytdlp.download_many(
            urls,
            on_error=ErrorPolicy.COLLECT,
        )

        for res in results:
            if isinstance(res, DownloadResult):
                print(f"Скачан: {res.filepath}")
            else:
                print(f"Ошибка загрузки: {res}")
```

### Политики обработки ошибок (`ErrorPolicy`):
- `ErrorPolicy.COLLECT` (по умолчанию): сохраняет результаты успешных загрузок и ошибки для каждого URL в результирующем списке.
- `ErrorPolicy.FAIL_FAST`: при возникновении первой же ошибки прерывает выполнение всех остальных задач группы.
- `ErrorPolicy.SKIP`: возвращает только успешные результаты `DownloadResult`, отбрасывая ошибки.

---

## 3. Рекомендации по настройке `max_concurrency`

| Сценарий использования | Рекомендуемый `max_concurrency` | Пояснение |
| :--- | :--- | :--- |
| **Telegram-бот (VPS 1-2 vCPU)** | 2 – 3 | Защита от перегрузки CPU при работе `ffmpeg` |
| **Telegram-бот (Сервер 4-8 vCPU)** | 4 – 8 | Оптимальный баланс пропускной способности |
| **Скрапинг метаданных (только extract)** | 10 – 20 | Операции только сетевые, ffmpeg не запускается |
| **Локальный CLI скрипт** | 2 – 4 | Не забивает весь домашний интернет-канал |
