# Быстрый старт с async-yt-dlp

Руководство по началу работы с библиотекой `async-yt-dlp`.

## Требования

- **Python**: 3.11 или новее.
- **yt-dlp**: 2024.01.01 или новее.
- **ffmpeg** и **ffprobe** (опционально, но рекомендуется для слияния аудио/видео и конвертации форматов).
- **Среда JavaScript** (Node.js, Deno или Bun) — рекомендуется для извлечения YouTube без ограничений по скорости и форматам.

---

## Установка

Установка через `pip`:
```bash
pip install async-yt-dlp
```

Или с использованием менеджера пакетов `uv`:
```bash
uv add async-yt-dlp
```

---

## Первый запуск: Извлечение метаданных

Для получения информации о видео или плейлисте без фактического скачивания медиа-файлов используйте метод `extract_info`:

```python
import asyncio
import sys
from async_yt_dlp import AsyncYTDLP

# Корректный вывод Unicode/эмодзи в консоли Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    async with AsyncYTDLP() as ytdlp:
        info = await ytdlp.extract_info("https://www.youtube.com/watch?v=BaW_jenozKc")

        print(f"Название:     {info.title}")
        print(f"Автор:        {info.uploader}")
        print(f"Длительность: {info.duration_seconds} сек.")
        print(f"Форматов:     {len(info.formats)}")


if __name__ == "__main__":
    asyncio.run(main())
```

> [!NOTE]
> Начиная с версии `0.1.4`, библиотека автоматически обнаруживает установленные в системе среды JavaScript (Node.js, Deno, Bun) и передает их ядру `yt-dlp`. Предупреждения об отсутствии JS-рантайма подавляются автоматически.

---

## Скачивание видеофайла с объектной конфигурацией

Метод `download` скачивает ресурс и возвращает объект `DownloadResult` с путем к итоговому файлу:

```python
import asyncio
from pathlib import Path
from async_yt_dlp import (
    AsyncYTDLP,
    FormatSelector,
    OutputTemplate,
    VideoContainer,
    YTDLPOptions,
)


async def main() -> None:
    options = YTDLPOptions(
        # 1. Сетевой уровень: выбираем только качество/разрешение стрима с сервера
        format=FormatSelector.preset_720p(),
        # 2. Файловый уровень: гарантируем расширение и формат .mp4 на диске через FFmpeg
        container=VideoContainer.MP4,
        output_path=Path("./downloads"),
        output_template=OutputTemplate.title_only(),
    )

    async with AsyncYTDLP(default_options=options) as ytdlp:
        result = await ytdlp.download("https://www.youtube.com/watch?v=BaW_jenozKc")

        print(f"Файл сохранен: {result.filepath}")
        print(f"Размер:        {result.file_size / (1024 * 1024):.2f} MiB")
        print(f"Время:         {result.elapsed:.2f} сек.")


if __name__ == "__main__":
    asyncio.run(main())
```

> [!TIP]
> **Принцип DRY и этапы конвейера скачивания:**
> Не дублируйте `container` одновременно в `FormatSelector` и в `YTDLPOptions`!
> - `FormatSelector` отвечает **за сетевые потоки** (качество, высота кадра, битрейт, кодеки на удаленном сервере).
> - `YTDLPOptions(container=...)` отвечает **за итоговый локальный файл** (сборка и быстрый FFmpeg-ремуксинг в целевой `.mp4` на диске).
> 
> Если указать `container` в `YTDLPOptions`, библиотека сама скачает наилучшие потоки (даже если видео на сервере хранится в WebM/VP9, а аудио в Opus) и автоматически упакует их в единый `.mp4` на выходе.


---

## Отслеживание прогресса в реальном времени

Для приложений с графическим интерфейсом, Telegram-ботов или веб-сервисов доступен асинхронный генератор `download_with_progress`:

```python
import asyncio
from async_yt_dlp import AsyncYTDLP, DownloadStatus


async def main() -> None:
    async with AsyncYTDLP() as ytdlp:
        url = "https://www.youtube.com/watch?v=BaW_jenozKc"

        async for event in ytdlp.download_with_progress(url, throttle_interval=0.2):
            if event.status == DownloadStatus.DOWNLOADING:
                line = f"Загрузка: {event.percent:.1f}% | {event.speed_str} | ETA: {event.eta_str}"
                # \033[K очищает остаток строки терминала, ljust(70) исключает наложение старых символов
                print(f"\r\033[K{line:<70}", end="", flush=True)
            elif event.status == DownloadStatus.POST_PROCESSING:
                if event.postprocessor_status == "started":
                    print(f"\r\033[KПостобработка: {event.postprocessor}...", flush=True)
            elif event.status == DownloadStatus.COMPLETE:
                print("\r\033[KЗагрузка успешно завершена!", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Проверка окружения и утилит

Библиотека включает встроенный метод диагностики установленных зависимостей:

```python
import asyncio
from async_yt_dlp import AsyncYTDLP


async def main() -> None:
    async with AsyncYTDLP() as ytdlp:
        deps = await ytdlp.check_dependencies()
        print(f"Версия yt-dlp:    {deps.ytdlp_version}")
        print(f"ffmpeg доступен:  {deps.ffmpeg_available} ({deps.ffmpeg_path})")
        print(f"ffprobe доступен: {deps.ffprobe_available}")
        print(f"JS движки:        {deps.js_runtimes}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Следующие шаги

- Ознакомьтесь с [Архитектурой библиотеки](architecture.md).
- Узнайте о возможностях типизированной [Конфигурации](configuration.md).
- Изучите особенности [Параллельности](concurrency.md) и [Отмены задач](cancellation.md).
- Ознакомьтесь с решениями типовых проблем в [Устранении неполадок](troubleshooting.md).
