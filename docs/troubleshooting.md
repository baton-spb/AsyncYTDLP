# Устранение неполадок (Troubleshooting)

Часто встречающиеся проблемы и способы их решения при работе с `async-yt-dlp`.

---

## 1. Ошибка "ffmpeg не найден" (DependencyError или PostProcessingError)

**Симптом:**
При попытке слияния видео и аудио или извлечения MP3 возникает ошибка:
`PostProcessingError: ffmpeg not found` или видео скачивается без звука.

**Решение:**
1. Установите `ffmpeg` и `ffprobe` в вашей операционной системе:
   - **Ubuntu/Debian**: `sudo apt update && sudo apt install -y ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Windows**: скачайте сборку с gyan.dev и добавьте путь в системный PATH, либо передайте путь явно:
     ```python
     options = YTDLPOptions(ffmpeg_location=r"C:\ffmpeg\bin\ffmpeg.exe")
     ```
2. Проверьте обнаружение через `await ytdlp.check_dependencies()`.

---

## 2. Ошибка "Sign in to confirm you're not a bot" (403 Forbidden)

**Симптом:**
YouTube блокирует запрос с сообщением о необходимости подтверждения личности или решения капчи.

**Решение:**
1. Используйте экспорт cookies из вашего браузера:
   ```python
   options = YTDLPOptions(cookies_from_browser="firefox")
   # Или через файл cookies:
   options = YTDLPOptions(cookies_file=Path("cookies.txt"))
   ```
2. Используйте прокси-сервер:
   ```python
   options = YTDLPOptions(proxy="socks5://user:pass@proxy-ip:1080")
   ```
3. Установите движок Deno или Node.js для вычисления JavaScript-сигнатур YouTube.

---

## 3. Ошибка `QueueFullError: Превышен лимит очереди ожидания`

**Симптом:**
Вызов метода падает с исключением `QueueFullError`.

**Решение:**
Количество одновременно поступивших запросов превысило `queue_size`.
Увеличьте размер очереди или увеличьте лимит параллельности `max_concurrency`:
```python
ytdlp = AsyncYTDLP(max_concurrency=8, queue_size=500)
```

---

## 4. Ошибка `LifecycleError: Клиент находится в состоянии 'closed'`

**Симптом:**
Попытка вызова `download` или `extract_info` после выхода из блока `async with`.

**Решение:**
Все вызовы должны происходить внутри контекстного менеджера:
```python
async with AsyncYTDLP() as ytdlp:
    # Все операции выполняются здесь!
    result = await ytdlp.download(url)
```
Либо не используйте `async with`, а управляйте жизненным циклом вручную, вызвав `await ytdlp.close()` только при завершении всего приложения.
