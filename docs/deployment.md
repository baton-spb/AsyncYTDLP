# Развертывание и Docker

Руководство по развертыванию сервисов на базе `async-yt-dlp` в production-окружении.

---

## 1. Системные требования

- **ОС**: Linux (Ubuntu 22.04+, Debian 12+, Alpine 3.20+), macOS, Windows.
- **Python**: 3.14+.
- **ffmpeg & ffprobe**: последняя стабильная версия (рекомендуется 6.x / 7.x).
- **Deno** или **Node.js**: рекомендуется для поддержки JS-челленджей YouTube.

---

## 2. Развертывание в Docker

В корне репозитория подготовлен оптимизированный мультистейдж `Dockerfile` с установленными `ffmpeg` и `deno`.

### Сборка образа:
```bash
docker build -t async-yt-dlp:latest .
```

### Запуск контейнера:
```bash
docker run --rm -v $(pwd)/downloads:/app/downloads async-yt-dlp:latest
```

---

## 3. Запуск через docker-compose

```yaml
version: '3.8'

services:
  app:
    build: .
    restart: unless-stopped
    volumes:
      - ./downloads:/app/downloads
    environment:
      - PYTHONUNBUFFERED=1
```

Запуск:
```bash
docker-compose up -d
```
