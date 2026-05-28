import pytest

import ba_monitor.providers as providers
from ba_monitor.providers import BarmoryStbProvider, _recent_match_from_stb


def test_recent_match_falls_back_to_rating_delta_for_unknown_winner() -> None:
    match = _recent_match_from_stb(
        123,
        42,
        {
            "MapId": 12,
            "EndTime": 1772992500,
            "TotalPlayTimeInSec": 1800,
            "Data": {
                "42": {
                    "TeamId": 1,
                    "OldRating": 1500,
                    "NewRating": 1512.5,
                    "DestructionScore": 3000,
                    "LossesScore": 2000,
                }
            },
        },
    )

    assert match.result == "win"


@pytest.mark.asyncio
async def test_resolve_short_player_id(monkeypatch) -> None:
    def fake_request_json(method, url, headers, payload=None):
        assert "players/info?stbid=186461" in url
        return {"info": {"steamId": "76561198379902699"}}

    monkeypatch.setattr(providers, "_request_json", fake_request_json)

    steam_id = await BarmoryStbProvider()._resolve_steam_id("186461")

    assert steam_id == "76561198379902699"


@pytest.mark.asyncio
async def test_resolve_player_name_prefers_exact_match(monkeypatch) -> None:
    def fake_request_json(method, url, headers, payload=None):
        assert "players/search" in url
        return {
            "players": [
                {"name": "山雾谷雨2", "steam_id": "76561198000000002"},
                {"name": "山雾谷雨", "steam_id": "76561198379902699"},
            ]
        }

    monkeypatch.setattr(providers, "_request_json", fake_request_json)

    steam_id = await BarmoryStbProvider()._resolve_steam_id("山雾谷雨")

    assert steam_id == "76561198379902699"
