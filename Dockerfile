# syntax=docker/dockerfile:1
FROM python:3.14-slim AS base

# Установка системных зависимостей (ffmpeg, ffprobe, ca-certificates, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание непривилегированного пользователя appuser
RUN useradd -m -u 10001 -s /bin/bash appuser

WORKDIR /app

# Установка менеджера uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Копирование описания проекта и установка зависимостей
COPY pyproject.toml README.md ./
COPY src/ src/

RUN uv pip install --system --no-cache .

# Подготовка каталога для скачиваний с правами appuser
RUN mkdir -p /app/downloads && chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    DOWNLOADS_DIR=/app/downloads

VOLUME ["/app/downloads"]

CMD ["python", "-c", "import async_yt_dlp; print('async-yt-dlp', async_yt_dlp.__version__, 'готов к работе!')"]
