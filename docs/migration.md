# Миграция с синхронного yt-dlp на async-yt-dlp

Руководство по переводу существующего кода со стандартного синхронного `yt-dlp` на `async-yt-dlp`.

---

## 1. Сравнение подходов

### Извлечение информации (Metadata Extraction)

#### Раньше (yt-dlp):
```python
from yt_dlp import YoutubeDL

ydl_opts = {"quiet": True, "skip_download": True}
with YoutubeDL(ydl_opts) as ydl:
    # Блокирует поток! Не типизировано!
    info = ydl.extract_info("https://...", download=False)
    title = info["title"]
    duration = info.get("duration")
```

#### Теперь (async-yt-dlp):
```python
from async_yt_dlp import AsyncYTDLP

async with AsyncYTDLP() as ytdlp:
    # Не блокирует event loop! Строго типизировано!
    info = await ytdlp.extract_info("https://...")
    title = info.title
    duration = info.duration_seconds
```

---

### Скачивание файла с отслеживанием прогресса

#### Раньше (yt-dlp):
```python
def my_hook(d):
    if d['status'] == 'downloading':
        print(d.get('_percent_str'))

ydl_opts = {
    'format': 'best',
    'progress_hooks': [my_hook],  # Вызывается синхронно в потоке, сложно связать с async loop
}

with YoutubeDL(ydl_opts) as ydl:
    ydl.download(["https://..."])
```

#### Теперь (async-yt-dlp):
```python
from async_yt_dlp import AsyncYTDLP, DownloadStatus, YTDLPOptions

options = YTDLPOptions(format="best")

async with AsyncYTDLP(default_options=options) as ytdlp:
    # Прямой асинхронный генератор с троттлингом и вычисленными свойствами!
    async for event in ytdlp.download_with_progress(url):
        if event.status == DownloadStatus.DOWNLOADING:
            print(f"{event.percent:.1f}% | {event.speed_str}")
```

---

## 2. Миграция словаря `ydl_opts` в `YTDLPOptions`

Большинство ключей `ydl_opts` напрямую соответствуют типизированным полям `YTDLPOptions`:

| Старый ключ `ydl_opts` | Новое поле `YTDLPOptions` |
| :--- | :--- |
| `'format'` | `format="best"` |
| `'outtmpl'` | `output_template="%(title)s.%(ext)s"` |
| `'paths': {'home': ...}` | `output_path=Path(...)` |
| `'paths': {'temp': ...}` | `temp_path=Path(...)` |
| `'proxy'` | `proxy="socks5://..."` |
| `'cookiefile'` | `cookies_file=Path("cookies.txt")` |
| `'retries'` | `retries=10` |
| `'ratelimit'` | `rate_limit=1048576` |
| `'extract_audio'` / PP | `extract_audio=True, audio_format="mp3"` |

Если в вашем коде используются редкие внутренние ключи, передайте их в `raw_options`:
```python
options = YTDLPOptions(
    format="best",
    raw_options={
        "my_rare_option": 123,
    },
)
```
