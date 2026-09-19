"""Пример гибкой конфигурации с использованием raw_options и прокси."""

import asyncio
from pathlib import Path

from async_yt_dlp import AsyncYTDLP, AsyncYTDLPError, YTDLPOptions


async def main() -> None:
    url = "https://www.youtube.com/watch?v=BaW_jenozKc"

    # Сочетание строго типизированных полей и низкоуровневых raw_options
    options = YTDLPOptions(
        # Высокоуровневые типизированные параметры
        format="bestvideo+bestaudio/best",
        output_path=Path("./downloads"),
        retries=10,
        socket_timeout=15.0,
        # Настройки прокси и cookies (при необходимости)
        # proxy="socks5://127.0.0.1:1080",
        # cookies_file=Path("cookies.txt"),
        # Любые низкоуровневые опции yt-dlp для тонкой настройки
        raw_options={
            "geo_bypass": True,
            "hls_prefer_native": True,
            "concurrent_fragment_downloads": 4,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            },
        },
    )

    async with AsyncYTDLP(default_options=options) as ytdlp:
        try:
            print("Параметры операции (с маскированием секретов для логов):")
            print(options.to_safe_dict())

            info = await ytdlp.extract_info(url, download=False)
            print(f"\nУспешно получены метаданные: {info.title}")

        except AsyncYTDLPError as err:
            print(f"Ошибка выполнения: {err}")


if __name__ == "__main__":
    asyncio.run(main())
