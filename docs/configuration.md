# Конфигурация YTDLPOptions

Библиотека `async-yt-dlp` предоставляет класс `YTDLPOptions` (неизменяемый frozen dataclass),
который гарантирует строгую типизацию настроек, валидацию и защиту от опечаток.

---

## 1. Основные категории параметров

### Выбор формата
```python
YTDLPOptions(
    format="bestvideo+bestaudio/best",
    format_sort=["res:1080", "fps:60"],
    format_sort_force=True,
)
```

### Пути и шаблоны имен файлов
```python
YTDLPOptions(
    output_template="%(title)s [%(id)s].%(ext)s",
    output_path=Path("/var/media/downloads"),
    temp_path=Path("/tmp/ytdlp_cache"),
    restrict_filenames=True,  # Только ASCII символы
    windows_filenames=True,  # Совместимость с файловой системой Windows
    no_overwrites=True,  # Не перезаписывать уже существующие файлы
)
```

### Сеть и прокси
```python
YTDLPOptions(
    proxy="socks5://127.0.0.1:1080",
    socket_timeout=30.0,
    impersonate="chrome",  # Маскировка TLS-fingerprint через curl_cffi
    http_headers={
        "User-Agent": "Custom-Agent/1.0",
        "Referer": "https://example.com",
    },
)
```

### Авторизация и Cookies
```python
YTDLPOptions(
    cookies_file=Path("/etc/cookies/youtube.txt"),
    cookies_from_browser="firefox",  # Загрузка cookies напрямую из профиля браузера
    username="user@example.com",
    password="my_password",
)
```

### Постобработка и ffmpeg
```python
YTDLPOptions(
    extract_audio=True,
    audio_format="mp3",  # mp3, m4a, flac, opus, wav
    audio_quality="192K",
    embed_thumbnail=True,  # Встроить обложку в аудио/видео
    embed_metadata=True,  # Записать теги (название, автор, альбом)
    embed_subtitles=True,  # Встроить субтитры в контейнер
    ffmpeg_location=Path("/opt/homebrew/bin/ffmpeg"),
)
```

---

## 2. Использование `raw_options` для forward-compatibility

Если в новой версии `yt-dlp` появилась новая опция, которой еще нет в типизированных полях `YTDLPOptions`,
вы можете передать ее напрямую через словарь `raw_options`:

```python
options = YTDLPOptions(
    format="best",
    raw_options={
        "concurrent_fragment_downloads": 4,
        "geo_bypass": True,
        "hls_prefer_native": True,
    },
)
```

> [!NOTE]
> Значения из `raw_options` имеют **наивысший приоритет** и переопределяют любые типизированные поля.

---

## 3. Слияние конфигураций (Merging)

Вы можете определить базовую конфигурацию на уровне клиента и переопределять отдельные параметры
в конкретных вызовах `extract_info` или `download`:

```python
# Базовые настройки для всего клиента
client_options = YTDLPOptions(
    output_path=Path("./downloads"),
    proxy="socks5://127.0.0.1:9050",
    retries=5,
)

async with AsyncYTDLP(default_options=client_options) as ytdlp:
    # 1. Скачивание обычного видео (используются базовые настройки)
    await ytdlp.download("https://...")

    # 2. Скачивание только аудио (переопределяем format и включаем extract_audio)
    # output_path, proxy и retries унаследуются из client_options автоматически!
    await ytdlp.download(
        "https://...",
        options=YTDLPOptions(extract_audio=True, audio_format="mp3"),
    )
```

---

## 4. Безопасное логирование

Для вывода параметров в логи или отладки используйте метод `.to_safe_dict()`:
```python
print(options.to_safe_dict())
# Пароли, токены, учетные данные прокси и cookies будут замаскированы звездочками (********)
```
