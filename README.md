# async-yt-dlp

<p align="center">
  <b>Высокопроизводительная, строго типизированная асинхронная Python-библиотека обёртка над yt-dlp.</b>
</p>

<p align="center">
  <a href="#возможности">Возможности</a> •
  <a href="#установка">Установка</a> •
  <a href="#быстрый-старт">Быстрый старт</a> •
  <a href="#архитектура">Архитектура</a> •
  <a href="#документация">Документация</a> •
  <a href="#лицензия">Лицензия</a>
</p>

---

`async-yt-dlp` — это универсальный асинхронный SDK / adapter layer над мощным синхронным ядром `yt-dlp`. Библиотека спроектирована для использования в любых современных async-приложениях:
- Telegram-ботах (aiogram, telethon, pyrogram)
- Discord-ботах (discord.py)
- Веб-сервисах и API (FastAPI, Litestar, Aiohttp)
- Фоновых воркерах и очередях (Celery, ARQ, Taskiq)

Библиотека **не зависит** от Telegram или каких-либо веб-фреймворков и является полностью самостоятельным проектом.

---

## Возможности

-  **100% Async Native**: Все блокирующие операции сети, диска и ffmpeg вынесены в системные потоки через `asyncio.to_thread`. Event loop никогда не блокируется.
-  **Строгая типизация**: Модели `MediaInfo`, `FormatInfo`, `DownloadResult`, `ProgressEvent` (PEP 561 `py.typed`, совместимо со строгим режимом `mypy`).
-  **Потокобезопасность**: Изолированный экземпляр `YoutubeDL` на каждую операцию исключает состояние гонки и порчу сессий.
-  **Плавный стриминг прогресса**: Асинхронный генератор `download_with_progress` с адаптивным троттлингом (защита от перегрузки интерфейса и спама).
-  **Контроль параллельности**: Встроенный `DownloadManager` на базе `asyncio.Semaphore` с ограничением емкости очереди (backpressure).
-  **Структурированная конкурентность**: Поддержка Python 3.14 `asyncio.TaskGroup` в пакетной загрузке `download_many`.
-  **Честная модель отмены**: Корректная обработка `task.cancel()`, таймаутов `asyncio.timeout` и graceful shutdown.
-  **Безопасность данных**: Автоматическая маскировка паролей, токенов, cookies и прокси в логах; защита от SSRF и протокола `file://`.
-  **Проверка зависимостей**: Встроенная диагностика окружения (`check_dependencies`) для проверки `yt-dlp`, `ffmpeg`, `ffprobe` и JS-движков.

---

## Установка

Требуется Python **3.14+**.

```bash
pip install async-yt-dlp
```

Или с использованием `uv`:
```bash
uv add async-yt-dlp
```

---

## Быстрый старт

### 1. Извлечение метаданных видео или плейлиста
```python
import asyncio
from async_yt_dlp import AsyncYTDLP

async def main():
    async with AsyncYTDLP() as ytdlp:
        info = await ytdlp.extract_info("https://www.youtube.com/watch?v=BaW_jenozKc")
        print(f"🎬 {info.title}")
        print(f"👤 Автор: {info.uploader}")
        print(f"⏱ Длительность: {info.duration_seconds} сек.")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Скачивание видео с настройками качества
```python
import asyncio
from pathlib import Path
from async_yt_dlp import AsyncYTDLP, YTDLPOptions

async def main():
    options = YTDLPOptions(
        format="bestvideo[height<=720]+bestaudio/best[height<=720]",
        output_path=Path("./downloads"),
        output_template="%(title)s.%(ext)s",
    )

    async with AsyncYTDLP(default_options=options) as ytdlp:
        result = await ytdlp.download("https://www.youtube.com/watch?v=BaW_jenozKc")
        print(f"✅ Файл сохранен: {result.filepath} ({result.file_size} байт)")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Стриминг прогресса загрузки в реальном времени
```python
import asyncio
from async_yt_dlp import AsyncYTDLP, DownloadStatus

async def main():
    async with AsyncYTDLP() as ytdlp:
        url = "https://www.youtube.com/watch?v=BaW_jenozKc"
        
        async for event in ytdlp.download_with_progress(url, throttle_interval=0.5):
            if event.status == DownloadStatus.DOWNLOADING:
                print(f"\rЗагрузка: {event.percent:.1f}% | {event.speed_str} | ETA: {event.eta_str}", end="")
            elif event.status == DownloadStatus.COMPLETE:
                print("\nГотово!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Архитектура

```
┌───────────────────────────────────────────────┐
│     Приложение (Telegram, Web, CLI, Bot)      │
└───────────────────────┬───────────────────────┘
                        │
            ┌───────────▼───────────┐
            │       AsyncYTDLP      │  ← Фасад, API, Lifecycle
            └───────────┬───────────┘
                        │
            ┌───────────▼───────────┐
            │    DownloadManager    │  ← Semaphore, Backpressure, Shutdown
            └───────────┬───────────┘
                        │
            ┌───────────▼───────────┐
            │     ThreadBackend     │  ← asyncio.to_thread, изолированный
            └───────────┬───────────┘     экземпляр YoutubeDL на операцию
                        │
            ┌───────────▼───────────┐
            │   yt_dlp.YoutubeDL    │  ← Синхронный движок yt-dlp
            └───────────────────────┘
```

Подробное описание архитектуры доступно в документе [docs/architecture.md](docs/architecture.md).

---

## Документация

Подробные руководства на русском языке находятся в каталоге `docs/`:

1. [Быстрый старт](docs/getting-started.md)
2. [Архитектура и дизайн](docs/architecture.md)
3. [Справочник публичного API](docs/api.md)
4. [Конфигурация YTDLPOptions](docs/configuration.md)
5. [Управление параллельностью](docs/concurrency.md)
6. [Модель отмены и таймауты](docs/cancellation.md)
7. [Отслеживание прогресса](docs/progress.md)
8. [Иерархия исключений](docs/errors.md)
9. [Безопасность и санитизация](docs/security.md)
10. [Производительность и оптимизация](docs/performance.md)
11. [Развертывание и Docker](docs/deployment.md)
12. [Руководство для разработчиков](docs/development.md)
13. [Тестирование](docs/testing.md)
14. [Устранение неполадок](docs/troubleshooting.md)
15. [Миграция с синхронного yt-dlp](docs/migration.md)

---

## Примеры использования

В каталоге `examples/` представлены готовые примеры кода:
- [Простое извлечение информации](examples/simple_extract.py)
- [Скачивание файла](examples/simple_download.py)
- [Отображение прогресса](examples/progress.py)
- [Работа с плейлистами](examples/playlist.py)
- [Извлечение аудио и MP3 конвертация](examples/audio_extraction.py)
- [Продвинутые параметры](examples/custom_options.py)
- [Отмена задач и таймауты](examples/cancellation.py)
- [Пакетная параллельная загрузка](examples/concurrency.py)
- [Интеграция с Telegram-ботом на aiogram 3.x](examples/integrations/telegram_aiogram.py)

---

## Лицензия

Проект распространяется под лицензией MIT. Подробнее см. в файле [LICENSE](LICENSE).
