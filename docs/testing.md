# Тестирование async-yt-dlp

В проекте реализован полный тестовый комплекс, покрывающий все слои архитектуры:
юнит-тесты, интеграционные сценарии и бенчмарки производительности.

---

## 1. Запуск тестов

### Запуск всех стандартных тестов:
```bash
uv run pytest tests/ -v -m "not integration"
```

### Запуск только юнит-тестов:
```bash
uv run pytest tests/unit/ -v
```

### Запуск тестов производительности:
```bash
uv run pytest tests/performance/ -v
```

### Запуск интеграционных тестов с реальной сетью:
```bash
uv run pytest tests/integration/ -v -m "integration"
```

---

## 2. Анализ покрытия кода (Code Coverage)

Для генерации отчета о тестовом покрытии:

```bash
uv run coverage run -m pytest tests/ -m "not integration"
uv run coverage report -m
```

Для генерации HTML-отчета:
```bash
uv run coverage html
# Откройте htmlcov/index.html в браузере
```

---

## 3. Организация тестов

- **`tests/conftest.py`**: общие фикстуры, реалистичные словари метаданных yt-dlp, мок-бэкенд `FakeBackend`.
- **`tests/unit/`**:
  - `test_options.py`: валидация, слияние настроек, генерация параметров yt-dlp.
  - `test_models.py`: парсинг `MediaInfo`, `FormatInfo`, сериализация JSON.
  - `test_progress.py`: вычисление процентов и скорости, троттлинг в `ProgressBridge`.
  - `test_exceptions.py`: иерархия ошибок, exception chaining.
  - `test_logging.py`: маскирование паролей, cookies, заголовков и URL.
  - `test_validation.py`: проверка схем URL и путей на диске.
  - `test_lifecycle.py`: состояния клиента и корректный закрытие.
  - `test_manager.py`: семафоры параллельности, переполнение очереди, shutdown.
  - `test_backend.py`: изоляция потоков выполнения `ThreadBackend`.
- **`tests/integration/`**:
  - `test_client_extract.py`: сценарии извлечения метаданных.
  - `test_client_download.py`: скачивание со стримингом прогресса и метод `download_many`.
  - `test_concurrency.py`: реальный учет параллельности семафора.
  - `test_cancellation.py`: отмена задач и таймауты `asyncio.timeout`.
- **`tests/performance/`**:
  - `test_overhead.py`: замер оверхеда моста прогресса и диспетчеризации задач.
