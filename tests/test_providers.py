from datetime import datetime, timezone

import pytest

import ba_monitor.providers as providers
from ba_monitor.providers import (
    BarmoryStbProvider,
    _recent_match_from_stb,
    _server_condition_from_batrace,
    _server_condition_from_steam,
    _server_condition_is_fresh,
    _normalize_batrace_time,
)


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


def test_server_condition_from_batrace() -> None:
    condition = _server_condition_from_batrace(
        {
            "serversByRegion": [
                {"region": "亚太", "total": 2, "active": 2, "lastSeen": "2026-05-29T06:01:30.000Z"}
            ],
            "online": {
                "online": 3157,
                "inLobby": 48,
                "inSearching": 45,
                "inBattle": 1127,
                "instances": 460,
                "timestamp": "2026-05-29T06:01:30.000Z",
            },
        }
    )

    assert condition.online == 3157
    assert condition.regions[0].region == "亚太"


def test_server_condition_from_steam() -> None:
    condition = _server_condition_from_steam({"response": {"player_count": 2567, "result": 1}})

    assert condition.online == 2567
    assert condition.source == "Steam"
    assert condition.detail_available is False
    assert condition.in_battle is None


def test_server_condition_old_batrace_snapshot_is_not_fresh() -> None:
    condition = _server_condition_from_batrace(
        {
            "serversByRegion": [],
            "online": {
                "online": 3157,
                "inLobby": 48,
                "inSearching": 45,
                "inBattle": 1127,
                "instances": 460,
                "timestamp": "2020-01-01T00:00:00.000Z",
            },
        }
    )

    assert _server_condition_is_fresh(condition) is False


def test_normalize_batrace_future_time_as_china_local(monkeypatch) -> None:
    class FrozenDateTime:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 5, 29, 10, 0, tzinfo=timezone.utc)

        @classmethod
        def fromisoformat(cls, value):
            return datetime.fromisoformat(value)

    monkeypatch.setattr("ba_monitor.providers.datetime", FrozenDateTime)

    assert _normalize_batrace_time("2026-05-29T18:00:00.000Z") == "2026-05-29T10:00:00+00:00"
