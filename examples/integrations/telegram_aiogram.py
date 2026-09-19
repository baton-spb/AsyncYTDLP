"""Пример интеграции async-yt-dlp с Telegram-ботом на aiogram 3.x.

ВАЖНО:
- Библиотека `async-yt-dlp` полностью независима от Telegram.
- Данный файл является демонстрационным примером правильного паттерна использования
  клиента `AsyncYTDLP`, управления прогрессом и безопасного редактирования сообщений Telegram.
- Для запуска требуется: `pip install aiogram`.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Проверка наличия опциональной зависимости aiogram
try:
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import Command
    from aiogram.types import FSInputFile, Message
except ImportError:
    print("Для запуска данного примера необходимо установить aiogram:")
    print("pip install aiogram")
    sys.exit(0)

from async_yt_dlp import (
    AsyncYTDLP,
    AsyncYTDLPError,
    DownloadStatus,
    YTDLPOptions,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")

dp = Dispatcher()

# Рекомендуется использовать единый инстанс AsyncYTDLP на весь жизненный цикл бота
ytdlp_client = AsyncYTDLP(
    max_concurrency=3,
    default_options=YTDLPOptions(
        format="bestvideo[height<=720]+bestaudio/best[height<=720]",
        output_path="./telegram_downloads",
    ),
)


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Отправь мне ссылку на видео (YouTube и др.), "
        "и я скачаю его с отображением прогресса в реальном времени."
    )


@dp.message(F.text.startswith("http"))
async def handle_video_url(message: Message, bot: Bot) -> None:
    url = message.text.strip() if message.text else ""
    status_msg = await message.answer("⏳ Анализ ссылки и получение метаданных...")

    last_text = ""

    try:
        # 1. Извлечение информации
        info = await ytdlp_client.extract_info(url, download=False)
        await status_msg.edit_text(
            f"🎬 <b>{info.title}</b>\n"
            f"👤 Автор: {info.uploader or 'Неизвестен'}\n"
            f"⏱ Длительность: {info.duration_seconds} сек.\n\n"
            f"🚀 Начинаем скачивание...",
            parse_mode="HTML",
        )

        # 2. Скачивание со стримингом прогресса
        # В Telegram API действует rate-limit на editMessageText (не чаще 1 раза в 1-2 сек на чат),
        # поэтому устанавливаем throttle_interval=1.5
        download_result = None
        async for event in ytdlp_client.download_with_progress(url, throttle_interval=1.5):
            if event.status == DownloadStatus.DOWNLOADING:
                pct = f"{event.percent:.1f}%" if event.percent is not None else "N/A"
                text = (
                    f"🎬 <b>{info.title}</b>\n"
                    f"Загрузка: {pct} ({event.downloaded_str} / {event.total_str})\n"
                    f"Скорость: {event.speed_str} | ETA: {event.eta_str}"
                )
                if text != last_text:
                    last_text = text
                    await status_msg.edit_text(text, parse_mode="HTML")

            elif event.status == DownloadStatus.POST_PROCESSING:
                await status_msg.edit_text(
                    f"⚙️ Выполняется постобработка ({event.postprocessor or 'конвертация'})...",
                    parse_mode="HTML",
                )

        # 3. Получение готового файла
        download_result = await ytdlp_client.download(url)

        await status_msg.edit_text("📤 Отправка готового файла в Telegram...")
        media_file = FSInputFile(str(download_result.filepath))
        await message.answer_video(
            video=media_file,
            caption=f"✅ {info.title}",
            supports_streaming=True,
        )
        await status_msg.delete()

    except AsyncYTDLPError as err:
        await status_msg.edit_text(f"❌ Ошибка загрузки: {err}")
    except Exception as exc:
        await status_msg.edit_text(f"❌ Непредвиденная ошибка: {exc}")


async def main() -> None:
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("Укажите BOT_TOKEN в переменных окружения или отредактируйте файл.")
        return

    bot = Bot(token=BOT_TOKEN)

    # Запускаем клиент yt-dlp в контекстном менеджере
    async with ytdlp_client:
        print("Telegram-бот запущен. Ожидание сообщений...")
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
