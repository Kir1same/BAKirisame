from __future__ import annotations

import time
import uuid
import json
import urllib.error
import urllib.parse
import urllib.request
import asyncio
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PlayerStats:
    name: str
    steam_id: str
    rating: int
    rank: int | None
    win_rate: float
    kd_ratio: float
    matches: int
    leaves: int
    level: int
    updated_at: str | None = None


@dataclass(frozen=True)
class RecentMatch:
    match_id: int
    map_id: int | None
    result: str
    rating_delta: float | None
    duration_seconds: int | None
    ended_at: int | None


@dataclass(frozen=True)
class MatchSummary:
    match_id: int
    map_id: int | None
    duration_seconds: int | None
    ended_at: int | None
    winner_team: int | None
    player_count: int
    top_destruction: str | None
    top_damage: str | None


@dataclass(frozen=True)
class UnitStats:
    name: str
    pick_rate: float
    win_rate: float
    role: str
    note: str


@dataclass(frozen=True)
class MetaSnapshot:
    patch: str
    strongest_faction: str
    trending_units: list[str]
    note: str


class GameDataProvider(Protocol):
    async def get_player(self, query: str) -> PlayerStats:
        ...

    async def get_recent_matches(self, steam_id: str, limit: int = 5) -> list[RecentMatch]:
        ...

    async def get_match(self, match_id: str) -> MatchSummary:
        ...

    async def get_unit(self, query: str) -> UnitStats:
        ...

    async def get_meta(self) -> MetaSnapshot:
        ...


class MockGameDataProvider:
    async def get_player(self, query: str) -> PlayerStats:
        return PlayerStats(
            name=query or "Unknown",
            steam_id=query or "76561198000000000",
            rating=1680,
            rank=128,
            win_rate=0.542,
            kd_ratio=1.18,
            matches=238,
            leaves=3,
            level=42,
            updated_at="mock",
        )

    async def get_recent_matches(self, steam_id: str, limit: int = 5) -> list[RecentMatch]:
        return [
            RecentMatch(5545812 + i, 4, "胜利" if i % 2 == 0 else "失败", 12.5 - i, 1800 + i * 60, None)
            for i in range(limit)
        ]

    async def get_match(self, match_id: str) -> MatchSummary:
        return MatchSummary(
            match_id=int(match_id),
            map_id=4,
            duration_seconds=2136,
            ended_at=None,
            winner_team=1,
            player_count=10,
            top_destruction="Kirisame",
            top_damage="Marisa",
        )

    async def get_unit(self, query: str) -> UnitStats:
        return UnitStats(
            name=query or "M1A2 SEP v3",
            pick_rate=0.34,
            win_rate=0.526,
            role="重装甲突破",
            note="示例数据。单位库后续用 BArmory/BA Hub 或本地数据文件补齐。",
        )

    async def get_meta(self) -> MetaSnapshot:
        return MetaSnapshot(
            patch="mock",
            strongest_faction="RU",
            trending_units=["T-90M", "M1A2 SEP v3", "Pantsir-S1"],
            note="示例数据。全局环境会在玩家查询稳定后接入。",
        )


class BarmoryStbProvider:
    def __init__(self, base_url: str = "https://barmory.net", client_id: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id or str(uuid.uuid4())
        self._attest_token: str | None = None
        self._attest_expires_at = 0

    async def get_player(self, query: str) -> PlayerStats:
        steam_id = _require_steam_id(query)
        profile = await self._get_stb(f"/stb/commander/{steam_id}/steam", cache_key="day")
        stats = await self._get_stb(f"/stb/commander/{steam_id}/stats", cache_key="day")
        rating_stats = stats.get("statisticByLobbyType", {}).get("Rating", {})
        matches = int(rating_stats.get("fightsCount") or 0)
        wins = int(rating_stats.get("winsCount") or 0)

        return PlayerStats(
            name=profile.get("name") or stats.get("name") or steam_id,
            steam_id=str(profile.get("steamId") or steam_id),
            rating=round(float(profile.get("rt") or 0)),
            rank=_optional_int(profile.get("rk")),
            win_rate=wins / matches if matches else 0.0,
            kd_ratio=float(rating_stats.get("kdRatio") or 0),
            matches=matches,
            leaves=int(rating_stats.get("leavesCount") or 0),
            level=int(profile.get("lvl") or stats.get("level") or 0),
            updated_at=stats.get("updateDate"),
        )

    async def get_recent_matches(self, steam_id: str, limit: int = 5) -> list[RecentMatch]:
        steam_id = _require_steam_id(steam_id)
        profile = await self._get_stb(f"/stb/commander/{steam_id}/steam", cache_key="day")
        commander_id = profile["id"]
        match_ids = await self._get_stb(f"/stb/commander/{commander_id}/matches", cache_key="hour")
        summaries: list[RecentMatch] = []
        for match_id in match_ids[:limit]:
            match_data = await self._get_stb(f"/stb/match/{match_id}", cache_key=None)
            summaries.append(_recent_match_from_stb(int(match_id), int(commander_id), match_data))
        return summaries

    async def get_match(self, match_id: str) -> MatchSummary:
        numeric_id = int(match_id.strip())
        data = await self._get_stb(f"/stb/match/{numeric_id}", cache_key=None)
        return _match_summary_from_stb(numeric_id, data)

    async def get_unit(self, query: str) -> UnitStats:
        return await MockGameDataProvider().get_unit(query)

    async def get_meta(self) -> MetaSnapshot:
        return await MockGameDataProvider().get_meta()

    async def _get_stb(self, path: str, cache_key: str | None) -> object:
        token = await self._get_attest_token()
        url = f"{self.base_url}{path}"
        params = {}
        if cache_key == "day":
            params["time"] = time.strftime("%Y-%m-%d", time.gmtime())
        elif cache_key == "hour":
            params["time"] = time.strftime("%Y-%m-%d_%H", time.gmtime())
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        headers = self._headers("stb", token)
        return await asyncio.to_thread(_request_json, "GET", url, headers)

    async def _get_attest_token(self) -> str:
        now = int(time.time())
        if self._attest_token and self._attest_expires_at - now > 60:
            return self._attest_token

        payload = await asyncio.to_thread(
            _request_json,
            "POST",
            f"{self.base_url}/gateway/attest",
            self._headers("BEZ"),
            {},
        )

        self._attest_token = payload["token"]
        self._attest_expires_at = int(payload["expiresAt"])
        return self._attest_token

    def _headers(self, request_type: str, attest_token: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "BA-Monitor-Kirisame/0.1",
            "X-Barmory-ID": self.client_id,
            "X-Barmory-Version": "6",
            "X-Type": request_type,
        }
        if attest_token:
            headers["X-Barmory-Attest"] = attest_token
        return headers


def build_provider(base_url: str | None, api_key: str | None, source: str = "barmory") -> GameDataProvider:
    if source == "mock":
        return MockGameDataProvider()
    if source == "barmory":
        return BarmoryStbProvider(base_url or "https://barmory.net", client_id=api_key)
    return MockGameDataProvider()


def _require_steam_id(query: str) -> str:
    steam_id = query.strip()
    if not steam_id.isdigit() or len(steam_id) < 16:
        raise ValueError("请输入 SteamID64，例如：76561198157609957")
    return steam_id


def _request_json(method: str, url: str, headers: dict[str, str], payload: object | None = None) -> object:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BArmory request failed: {exc.code} {body[:200]}") from exc


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _recent_match_from_stb(match_id: int, commander_id: int, data: dict) -> RecentMatch:
    player = data.get("Data", {}).get(str(commander_id), {})
    old_rating = player.get("OldRating")
    new_rating = player.get("NewRating")
    rating_delta = None
    if old_rating is not None and new_rating is not None:
        rating_delta = float(new_rating) - float(old_rating)

    team_id = player.get("TeamId")
    winner_team = data.get("WinnerTeam")
    if winner_team is None:
        result = "未知"
    elif team_id == winner_team:
        result = "胜利"
    else:
        result = "失败"

    return RecentMatch(
        match_id=match_id,
        map_id=_optional_int(data.get("MapId")),
        result=result,
        rating_delta=rating_delta,
        duration_seconds=_optional_int(data.get("TotalPlayTimeInSec")),
        ended_at=_optional_int(data.get("EndTime")),
    )


def _match_summary_from_stb(match_id: int, data: dict) -> MatchSummary:
    players = list(data.get("Data", {}).values())

    def top_player(field: str) -> str | None:
        ranked = [p for p in players if p.get(field) is not None]
        if not ranked:
            return None
        best = max(ranked, key=lambda p: float(p.get(field) or 0))
        return f"{best.get('Name', 'Unknown')} ({round(float(best.get(field) or 0))})"

    return MatchSummary(
        match_id=match_id,
        map_id=_optional_int(data.get("MapId")),
        duration_seconds=_optional_int(data.get("TotalPlayTimeInSec")),
        ended_at=_optional_int(data.get("EndTime")),
        winner_team=_optional_int(data.get("WinnerTeam")),
        player_count=len(players),
        top_destruction=top_player("Destruction"),
        top_damage=top_player("DamageDealt"),
    )
