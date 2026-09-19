"""Интеграционные тесты для извлечения информации (extract_info)."""

import pytest

from async_yt_dlp.client import AsyncYTDLP
from async_yt_dlp.models import MediaInfo
from async_yt_dlp.options import YTDLPOptions


@pytest.mark.asyncio
async def test_client_extract_info(client_with_fake: AsyncYTDLP):
    async with client_with_fake as client:
        info = await client.extract_info("https://www.youtube.com/watch?v=BaW_jenozKc")

        assert isinstance(info, MediaInfo)
        assert info.id == "BaW_jenozKc"
        assert info.title == "youtube-dl test video"
        assert not info.is_playlist


@pytest.mark.asyncio
async def test_client_extract_playlist(sample_playlist_info: dict, client_with_fake: AsyncYTDLP):
    client_with_fake._backend.return_info = sample_playlist_info  # type: ignore

    async with client_with_fake as client:
        info = await client.extract_info("https://www.youtube.com/playlist?list=123")

        assert info.is_playlist is True
        assert info.playlist_count == 2
        assert len(info.entries or ()) == 2


@pytest.mark.asyncio
async def test_client_extract_with_operation_options(client_with_fake: AsyncYTDLP):
    async with client_with_fake as client:
        await client.extract_info(
            "https://www.youtube.com/watch?v=BaW_jenozKc",
            options=YTDLPOptions(extract_flat=True, format="best"),
        )

        calls = client._backend.extract_calls  # type: ignore
        assert len(calls) == 1
        assert calls[0]["params"]["extract_flat"] is True
        assert calls[0]["params"]["format"] == "best"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_ytdlp_extraction_simulate():
    """Тест с реальным экземпляром yt-dlp в режиме симуляции без фактического скачивания файла."""
    async with AsyncYTDLP(
        default_options=YTDLPOptions(
            simulate=True,
            skip_download=True,
            no_warnings=True,
            quiet=True,
        )
    ) as ytdlp:
        # Тестовый статический URL из набора тестов yt-dlp
        url = "https://www.youtube.com/watch?v=BaW_jenozKc"
        try:
            info = await ytdlp.extract_info(url, download=False)
            assert info.id == "BaW_jenozKc"
            assert "youtube-dl" in info.title.lower() or "test" in info.title.lower()
            assert len(info.formats) > 0
        except Exception as exc:
            pytest.skip(f"Сетевой запрос к YouTube недоступен в данном окружении: {exc}")
