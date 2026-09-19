# Устранение неполадок (Troubleshooting)

Часто встречающиеся проблемы и способы их решения при работе с `async-yt-dlp`.

---

## 1. Предупреждение "No supported JavaScript runtime could be found" или медленная загрузка YouTube

**Симптом:**
При извлечении информации с YouTube появляется предупреждение:
```
[youtube] No supported JavaScript runtime could be found. Only deno is enabled by default; to use another runtime add --js-runtimes RUNTIME[:PATH] to your command/config. YouTube extraction without a JS runtime has been deprecated, and some formats may be missing.
```
Или видео скачивается с заниженной скоростью, отсутствуют форматы высокого разрешения (1080p, 4K).

**Причина:**
YouTube использует EJS (External JavaScript Execution) для шифрования параметров подписи `n-sig`. Если среда JavaScript не подключена к `yt-dlp`, экстрактор переходит в деградированный режим fallback.

**Решение:**
1. Начиная с версии `async-yt-dlp >= 0.1.4`, библиотека автоматически выполняет поиск установленных движков (`node`, `deno`, `bun`) в системном `PATH` благодаря параметру `auto_detect_js=True` (по умолчанию).
2. Если ни один JS-рантайм не установлен, установите один из них:
   - **Windows**: `winget install OpenJS.NodeJS.LTS` или `winget install DenoLand.Deno`
   - **Ubuntu/Debian**: `sudo apt install nodejs`
   - **macOS**: `brew install node` или `brew install deno`
3. После установки перезапустите терминал или IDE, чтобы переменная окружения `PATH` обновилась.
4. Проверить доступность можно программно:
   ```python
   deps = await ytdlp.check_dependencies()
   print("Обнаруженные JS-рантаймы:", deps.js_runtimes)
   ```

---

## 2. Ошибка "UnicodeEncodeError: 'charmap' codec can't encode character" на Windows

**Симптом:**
При печати метаданных видео (например, `print(info.title)` или `print(info)`) в консоли Windows (PowerShell или cmd) возникает исключение:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f46e' in position ...: character maps to <undefined>
```

**Причина:**
По умолчанию консоль Windows в русской локали использует однобайтную кодировку `cp1251` (или OEM 866), которая не поддерживает Unicode-символы и эмодзи, часто встречающиеся в названиях роликов на YouTube.

**Решение:**
В точке входа вашего скрипта перенастройте стандартный поток вывода на UTF-8:
```python
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
```
Либо установите переменную окружения Windows: `PYTHONIOENCODING=utf-8`.

---

## 3. Ошибка "ffmpeg не найден" (DependencyError или PostProcessingError)

**Симптом:**
При попытке слияния видео и аудио или извлечения MP3 возникает ошибка:
`PostProcessingError: ffmpeg not found` или видео скачивается без звука.

**Решение:**
1. Установите `ffmpeg` и `ffprobe` в вашей операционной системе:
   - **Ubuntu/Debian**: `sudo apt update && sudo apt install -y ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Windows**: `winget install Gyan.FFmpeg` либо скачайте сборку с gyan.dev и добавьте путь в системный `PATH`.
2. Путь к бинарному файлу можно также передать явно в опциях:
   ```python
   from pathlib import Path
   options = YTDLPOptions(ffmpeg_location=Path(r"C:\ffmpeg\bin\ffmpeg.exe"))
   ```
3. Проверьте обнаружение через `await ytdlp.check_dependencies()`.

---

## 4. Ошибка "Sign in to confirm you're not a bot" (403 Forbidden)

**Симптом:**
YouTube блокирует запрос с сообщением о необходимости подтверждения личности или решения капчи.

**Решение:**
1. Используйте экспорт cookies из вашего браузера:
   ```python
   options = YTDLPOptions(cookies_from_browser="firefox")
   # Или через отдельный файл cookies:
   options = YTDLPOptions(cookies_file=Path("cookies.txt"))
   ```
2. Используйте прокси-сервер:
   ```python
   options = YTDLPOptions(proxy="socks5://user:pass@proxy-ip:1080")
   ```
3. Убедитесь, что в системе установлен JS-рантайм (см. раздел 1).

---

## 5. Ошибка `QueueFullError: Превышен лимит очереди ожидания`

**Симптом:**
Вызов метода падает с исключением `QueueFullError`.

**Решение:**
Количество одновременно поступивших запросов превысило емкость очереди семафора `queue_size`.
Увеличьте размер очереди или увеличьте лимит параллельности `max_concurrency`:
```python
ytdlp = AsyncYTDLP(max_concurrency=8, queue_size=500)
```

---

## 6. Ошибка `LifecycleError: Клиент находится в состоянии 'closed'`

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
