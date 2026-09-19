# Changelog

Все заметные изменения в проекте `async-yt-dlp` документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и проект придерживается [Семантического версионирования](https://semver.org/lang/ru/).

---

## [0.1.0] - 2026-09-19

### Добавлено
- **Главный асинхронный клиент**: `AsyncYTDLP` с методами `extract_info`, `download`, `download_with_progress`, `download_many` и `check_dependencies`.
- **Строго типизированная конфигурация**: класс `YTDLPOptions` с поддержкой слияния настроек, построения цепочек `postprocessors` и `raw_options` для forward-compatibility.
- **Типизированные модели данных**: `MediaInfo`, `FormatInfo`, `ThumbnailInfo`, `SubtitleInfo`, `DownloadResult`, `DependencyInfo`.
- **Потокобезопасный мост событий**: `ProgressBridge` с настраиваемым троттлингом для частых событий загрузки и гарантированной доставкой ключевых стадий.
- **Диспетчер параллельности**: `DownloadManager` на базе `asyncio.Semaphore` с контролем размера очереди (backpressure) и graceful shutdown.
- **Иерархия исключений**: `AsyncYTDLPError` и 9 специализированных подклассов с автоматическим связыванием причин (`from exc`) и сохранением контекста (`url`, `job_id`).
- **Безопасность и логирование**: автоматическая маскировка паролей, cookies, токенов и прокси через `redact_options` и `YTDLPLoggerAdapter`.
- **Проверка внешних зависимостей**: встроенная диагностика `ffmpeg`, `ffprobe`, версий `yt-dlp` и сред исполнения JavaScript.
- **Тестовый комплекс**: 60+ юнит-, интеграционных и нагрузочных тестов с высоким покрытием кода.
- **Документация на русском языке**: 15 подробных руководств в каталоге `docs/`.
- **Примеры использования**: 9 готовых скриптов в каталоге `examples/`, включая интеграцию с Telegram-ботом на `aiogram 3.x`.
- **Инфраструктура**: `Dockerfile`, `docker-compose.yml`, CI пайплайн для Gitea Actions.
