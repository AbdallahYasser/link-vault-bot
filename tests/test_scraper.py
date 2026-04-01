import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.scraper import fetch_metadata, _clean


def test_clean_strips_whitespace():
    assert _clean("  hello   world  ") == "hello world"


def test_clean_empty():
    assert _clean("") == ""
    assert _clean(None) == ""


def test_clean_truncates():
    assert len(_clean("x" * 1000)) == 500


@pytest.mark.asyncio
async def test_fetch_metadata_parses_og_tags():
    html = """<html><head>
        <meta property="og:title" content="Test Title">
        <meta property="og:description" content="Test Description">
    </head></html>"""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            get=AsyncMock(return_value=mock_resp)
        ))
        mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await fetch_metadata("https://example.com")

    assert result["title"] == "Test Title"
    assert result["description"] == "Test Description"
