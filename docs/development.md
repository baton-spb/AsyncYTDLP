# Руководство для разработчиков

Руководство по локальной разработке, тестированию и внесению изменений в кодовую базу `async-yt-dlp`.

---

## 1. Настройка окружения

Для управления зависимостями и виртуальным окружением рекомендуется использовать современный инструмент `uv`:

```bash
# Клонирование репозитория
git clone https://gitea.example.com/org/async-yt-dlp.git
cd async-yt-dlp

# Синхронизация виртуального окружения и установка dev-зависимостей
uv sync --extra dev
```

---

## 2. Форматирование и статический анализ

В проекте настроены строгие правила линтинга и форматирования через `Ruff` и строгая типизация через `Mypy`.

### Проверка форматирования:
```bash
uv run ruff format --check src/ tests/ examples/
```

### Автоматическое форматирование кода:
```bash
uv run ruff format src/ tests/ examples/
```

### Запуск линтера:
```bash
uv run ruff check src/ tests/ examples/
```

### Проверка статической типизации:
```bash
uv run mypy src/
```

Все проверки должны завершаться без ошибок перед отправкой изменений.

---

## 3. Структура проекта

```text
async-yt-dlp/
├── src/async_yt_dlp/
│   ├── __init__.py          # Публичный экспорт библиотеки
│   ├── client.py            # Главный класс AsyncYTDLP и управление состояниями
│   ├── manager.py           # DownloadManager (семафоры, очереди, graceful shutdown)
│   ├── backend.py           # ThreadBackend (мост к yt-dlp через asyncio.to_thread)
│   ├── options.py           # YTDLPOptions (типизированная конфигурация)
│   ├── models.py            # MediaInfo, FormatInfo, DownloadResult
│   ├── progress.py          # ProgressEvent, ProgressBridge (троттлинг)
│   ├── exceptions.py        # Иерархия AsyncYTDLPError и маппинг
│   ├── _logging.py          # Адаптер логирования и санитизация секретов
│   ├── _validation.py       # Валидация URL и путей
│   └── _dependencies.py     # Инспекция ffmpeg/ffprobe/JS движков
├── tests/
│   ├── unit/                # Быстрые изолированные юнит-тесты
│   ├── integration/         # Интеграционные тесты
│   └── performance/         # Тесты производительности и оверхеда
├── examples/                # Примеры использования
└── docs/                    # Документация на русском языке
```
