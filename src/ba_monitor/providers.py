from __future__ import annotations

import time
import uuid
import json
import urllib.error
import urllib.parse
import urllib.request
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    kills: int = 0
    deaths: int = 0
    total_match_time_seconds: int = 0
    ranked_total: int | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class RecentMatch:
    match_id: int
    map_id: int | None
    result: str
    rating_delta: float | None
    duration_seconds: int | None
    ended_at: int | None
    kills: int | None = None
    losses: int | None = None
    destruction_score: float | None = None
    losses_score: float | None = None
    objectives_captured: int | None = None


@dataclass(frozen=True)
class DistributionBucket:
    bucket: float
    count: int


@dataclass(frozen=True)
class PlayerDistribution:
    rating: list[DistributionBucket]
    kd: list[DistributionBucket]
    total_players: int | None


@dataclass(frozen=True)
class ServerRegionCondition:
    region: str
    total: int
    active: int
    last_seen: str | None = None


@dataclass(frozen=True)
class ServerCondition:
    online: int
    in_lobby: int | None
    in_searching: int | None
    in_battle: int | None
    instances: int | None
    timestamp: str | None
    regions: list[ServerRegionCondition]
    source: str = "unknown"
    detail_available: bool = True


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
class CategoryPreference:
    key: str
    name: str
    total_cost: int
    percentage: float


@dataclass(frozen=True)
class HighlightUnit:
    unit_id: int
    name: str
    category: str
    spawn_count: int
    total_damage: float
    total_cost: int
    avg_roi: float


@dataclass(frozen=True)
class PlayStyleAxis:
    key: str
    value: float
    label: str


@dataclass(frozen=True)
class PlayerAnalysis:
    match_count: int
    category_preferences: list[CategoryPreference]
    highlight_units: list[HighlightUnit]
    play_style_axes: list[PlayStyleAxis]
    primary_style: str
    recent_win_rate: float | None = None
    recent_avg_objectives: float | None = None
    recent_avg_net_score: float | None = None
    recent_rating_delta: float | None = None


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

    async def get_recent_matches(self, steam_id: str, days: int = 1, limit: int = 20) -> list[RecentMatch]:
        ...

    async def get_player_analysis(self, steam_id: str) -> PlayerAnalysis | None:
        ...

    async def get_player_distribution(self) -> PlayerDistribution:
        ...

    async def get_server_condition(self) -> ServerCondition:
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
            kills=280,
            deaths=237,
            total_match_time_seconds=238 * 2100,
            ranked_total=200_000,
            updated_at="mock",
        )

    async def get_recent_matches(self, steam_id: str, days: int = 1, limit: int = 20) -> list[RecentMatch]:
        return [
            RecentMatch(
                5545812 + i,
                4,
                "win" if i % 2 == 0 else "loss",
                12.5 - i,
                1800 + i * 60,
                None,
                kills=38 + i,
                losses=28 + i,
                destruction_score=4200 + i * 120,
                losses_score=3100 + i * 80,
                objectives_captured=2 + i % 3,
            )
            for i in range(min(limit, max(1, days) * 4))
        ]

    async def get_player_analysis(self, steam_id: str) -> PlayerAnalysis | None:
        return PlayerAnalysis(
            match_count=50,
            category_preferences=[
                CategoryPreference("vehicles", "载具", 76000, 24.0),
                CategoryPreference("support", "支援", 66000, 21.0),
                CategoryPreference("infantry", "步兵", 52000, 16.5),
                CategoryPreference("aircrafts", "战机", 46000, 14.5),
            ],
            highlight_units=[
                HighlightUnit(63, "Assaultmen SMAW", "步兵", 59, 2657.0, 4130, 0.64),
                HighlightUnit(11, "M142 HIMARS", "支援", 18, 4200.0, 3600, 1.17),
                HighlightUnit(8, "AH-64D Longbow", "直升机", 12, 3100.0, 1320, 2.35),
            ],
            play_style_axes=[
                PlayStyleAxis("aggression", 65, "aggressive"),
                PlayStyleAxis("economy", 79, "efficient"),
                PlayStyleAxis("teamplay", 88, "team_player"),
            ],
            primary_style="team_player",
            recent_win_rate=0.56,
            recent_avg_objectives=3.4,
            recent_avg_net_score=860.0,
            recent_rating_delta=38.0,
        )

    async def get_player_distribution(self) -> PlayerDistribution:
        rating = [
            DistributionBucket(bucket, max(1, round(24000 * (1 - index / 65) ** 2)))
            for index, bucket in enumerate(range(250, 3500, 50))
        ]
        return PlayerDistribution(
            rating=rating,
            kd=[
                DistributionBucket(0.1 * index, max(1, round(26000 * (1 - index / 32) ** 2)))
                for index in range(31)
            ],
            total_players=sum(item.count for item in rating),
        )

    async def get_server_condition(self) -> ServerCondition:
        return ServerCondition(
            online=3157,
            in_lobby=48,
            in_searching=45,
            in_battle=1127,
            instances=460,
            timestamp="2026-05-29T06:01:30.000Z",
            regions=[
                ServerRegionCondition("亚太", 2, 2, "2026-05-29T06:01:30.000Z"),
                ServerRegionCondition("北美", 32, 32, "2026-05-29T06:01:30.000Z"),
                ServerRegionCondition("欧洲", 4, 4, "2026-05-29T06:01:30.000Z"),
            ],
            source="mock",
        )

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
        self._batrace_base_url = "https://app.batrace.top"
        self._leaderboard_total: int | None = None
        self._leaderboard_total_loaded = False

    async def get_player(self, query: str) -> PlayerStats:
        steam_id = await self._resolve_steam_id(query)
        profile = await self._get_stb(f"/stb/commander/{steam_id}/steam", cache_key="day")
        stats = await self._get_stb(f"/stb/commander/{steam_id}/stats", cache_key="day")
        rating_stats = stats.get("statisticByLobbyType", {}).get("Rating", {})
        matches = int(rating_stats.get("fightsCount") or 0)
        wins = int(rating_stats.get("winsCount") or 0)
        kills = int(rating_stats.get("killsCount") or 0)
        deaths = int(rating_stats.get("deathsCount") or 0)

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
            kills=kills,
            deaths=deaths,
            total_match_time_seconds=int(rating_stats.get("totalMatchTimeSec") or 0),
            ranked_total=await self._get_leaderboard_total(),
            updated_at=stats.get("updateDate"),
        )

    async def get_recent_matches(self, steam_id: str, days: int = 1, limit: int = 20) -> list[RecentMatch]:
        steam_id = await self._resolve_steam_id(steam_id)
        days = max(1, min(days, 30))
        limit = max(1, min(limit, 100))
        profile = await self._get_stb(f"/stb/commander/{steam_id}/steam", cache_key="day")
        commander_id = profile["id"]
        match_ids = await self._get_stb(f"/stb/commander/{commander_id}/matches", cache_key="hour")
        summaries: list[RecentMatch] = []
        cutoff = int(time.time()) - days * 24 * 60 * 60
        scan_limit = min(len(match_ids), max(limit * 4, days * 24))
        for match_id in match_ids[:scan_limit]:
            try:
                match_data = await self._get_stb(f"/stb/match/{match_id}", cache_key=None)
            except RuntimeError as exc:
                if "BArmory request failed: 404" in str(exc):
                    continue
                raise
            summary = _recent_match_from_stb(int(match_id), int(commander_id), match_data)
            if summary.ended_at is not None and summary.ended_at < cutoff:
                continue
            summaries.append(summary)
            if len(summaries) >= limit:
                break
        return summaries

    async def get_player_analysis(self, steam_id: str) -> PlayerAnalysis | None:
        steam_id = await self._resolve_steam_id(steam_id)
        profile = await self._get_stb(f"/stb/commander/{steam_id}/steam", cache_key="day")
        commander_id = profile["id"]
        try:
            payload = await asyncio.to_thread(
                _request_json,
                "GET",
                f"{self._batrace_base_url}/api/analysis/player?stbid={commander_id}",
                _plain_headers(),
            )
        except Exception:
            return None
        return _player_analysis_from_batrace(payload)

    async def get_player_distribution(self) -> PlayerDistribution:
        try:
            payload = await asyncio.to_thread(
                _request_json,
                "GET",
                "https://dash.batrace.top/api/players/distribution?metric=rating",
                _plain_headers(),
            )
        except Exception as exc:
            raise RuntimeError("无法获取全服分布数据") from exc
        return _player_distribution_from_batrace(payload if isinstance(payload, dict) else {})

    async def get_server_condition(self) -> ServerCondition:
        cache_buster = int(time.time())
        try:
            payload = await asyncio.to_thread(
                _request_json,
                "GET",
                f"https://dash.batrace.top/api/home/server-status?_={cache_buster}",
                _plain_headers(),
            )
            condition = _server_condition_from_batrace(payload if isinstance(payload, dict) else {})
            if _server_condition_is_fresh(condition):
                return condition
        except Exception:
            pass

        payload = await asyncio.to_thread(
            _request_json,
            "GET",
            "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=1604270",
            _plain_headers(),
        )
        return _server_condition_from_steam(payload if isinstance(payload, dict) else {})

    async def get_match(self, match_id: str) -> MatchSummary:
        numeric_id = int(match_id.strip())
        data = await self._get_stb(f"/stb/match/{numeric_id}", cache_key=None)
        return _match_summary_from_stb(numeric_id, data)

    async def get_unit(self, query: str) -> UnitStats:
        return await MockGameDataProvider().get_unit(query)

    async def get_meta(self) -> MetaSnapshot:
        return await MockGameDataProvider().get_meta()

    async def _resolve_steam_id(self, query: str) -> str:
        cleaned = query.strip()
        if cleaned.isdigit() and len(cleaned) >= 16:
            return cleaned
        if cleaned.isdigit():
            payload = await asyncio.to_thread(
                _request_json,
                "GET",
                f"https://dash.batrace.top/api/players/info?stbid={urllib.parse.quote(cleaned)}",
                _plain_headers(),
            )
            info = payload.get("info") if isinstance(payload, dict) else None
            if isinstance(info, dict):
                steam_id = str(info.get("steamId") or info.get("steam_id") or "")
                if steam_id.isdigit() and len(steam_id) >= 16:
                    return steam_id
            raise ValueError(f"没有找到 ID 为 {cleaned} 的玩家。")

        if not cleaned:
            raise ValueError("请输入 SteamID64、玩家 ID 或玩家名。")
        payload = await asyncio.to_thread(
            _request_json,
            "GET",
            f"https://dash.batrace.top/api/players/search?q={urllib.parse.quote(cleaned)}&limit=5",
            _plain_headers(),
        )
        players = payload.get("players") if isinstance(payload, dict) else None
        if not isinstance(players, list) or not players:
            raise ValueError(f"没有搜索到玩家：{cleaned}")
        exact = next(
            (
                player
                for player in players
                if isinstance(player, dict) and str(player.get("name") or "").casefold() == cleaned.casefold()
            ),
            None,
        )
        player = exact or next((player for player in players if isinstance(player, dict)), None)
        steam_id = str((player or {}).get("steam_id") or (player or {}).get("steamId") or "")
        if steam_id.isdigit() and len(steam_id) >= 16:
            return steam_id
        raise ValueError(f"搜索到了玩家 {cleaned}，但没有可用 SteamID。")

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

    async def _get_leaderboard_total(self) -> int | None:
        if self._leaderboard_total_loaded:
            return self._leaderboard_total
        self._leaderboard_total_loaded = True
        try:
            data = await asyncio.to_thread(
                _request_json,
                "GET",
                "https://dash.batrace.top/api/leaderboard/rank?limit=1&offset=0",
                _plain_headers(),
            )
        except Exception:
            return None
        if isinstance(data, dict):
            self._leaderboard_total = _optional_int(data.get("total"))
        return self._leaderboard_total

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


def _plain_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": "BA-Monitor-Kirisame/0.1",
    }


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
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
    if winner_team is None or team_id is None:
        result = "unknown"
    elif team_id == winner_team:
        result = "win"
    else:
        result = "loss"
    if result == "unknown" and rating_delta is not None:
        if rating_delta > 0:
            result = "win"
        elif rating_delta < 0:
            result = "loss"

    return RecentMatch(
        match_id=match_id,
        map_id=_optional_int(data.get("MapId")),
        result=result,
        rating_delta=rating_delta,
        duration_seconds=_optional_int(data.get("TotalPlayTimeInSec")),
        ended_at=_optional_int(data.get("EndTime")),
        kills=_optional_int(player.get("Destruction")),
        losses=_optional_int(player.get("Losses")),
        destruction_score=_optional_float(player.get("DestructionScore")),
        losses_score=_optional_float(player.get("LossesScore")),
        objectives_captured=_optional_int(player.get("ObjectivesCaptured")),
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


def _player_analysis_from_batrace(data: dict) -> PlayerAnalysis:
    categories = [
        CategoryPreference(
            key=str(item.get("categoryKey") or "unknown"),
            name=_category_name(str(item.get("categoryKey") or "unknown")),
            total_cost=round(float(item.get("totalCost") or 0)),
            percentage=float(item.get("percentage") or 0),
        )
        for item in data.get("categoryPreferences", [])[:7]
    ]
    units = [
        HighlightUnit(
            unit_id=int(item.get("unitId") or 0),
            name=str(item.get("unitName") or item.get("unitId") or "Unknown"),
            category=_category_name_by_id(item.get("categoryType")),
            spawn_count=int(item.get("spawnCount") or 0),
            total_damage=float(item.get("totalDamage") or 0),
            total_cost=round(float(item.get("totalCost") or 0)),
            avg_roi=float(item.get("avgRoi") or 0),
        )
        for item in data.get("highlightUnits", [])[:10]
    ]
    play_style = data.get("playStyle") or {}
    trend_points = data.get("trend", {}).get("points", [])
    axes = [
        PlayStyleAxis(
            key=str(item.get("axis") or "unknown"),
            value=float(item.get("value") or 0),
            label=str(item.get("label") or ""),
        )
        for item in play_style.get("axes", [])
    ]
    return PlayerAnalysis(
        match_count=int(data.get("matchCount") or 0),
        category_preferences=categories,
        highlight_units=units,
        play_style_axes=axes,
        primary_style=str(play_style.get("primaryStyle") or ""),
        recent_win_rate=_recent_win_rate(trend_points),
        recent_avg_objectives=_recent_avg_objectives(trend_points),
        recent_avg_net_score=_recent_avg_net_score(trend_points),
        recent_rating_delta=_recent_rating_delta(trend_points),
    )


def _player_distribution_from_batrace(data: dict) -> PlayerDistribution:
    return PlayerDistribution(
        rating=_distribution_buckets(data.get("rating")),
        kd=_distribution_buckets(data.get("kd")),
        total_players=_optional_int(data.get("totalPlayers")),
    )


def _server_condition_from_batrace(data: dict) -> ServerCondition:
    online = data.get("online") if isinstance(data.get("online"), dict) else {}
    regions = [
        ServerRegionCondition(
            region=str(item.get("region") or "未知"),
            total=_optional_int(item.get("total")) or 0,
            active=_optional_int(item.get("active")) or 0,
            last_seen=_normalize_batrace_time(item.get("lastSeen")),
        )
        for item in data.get("serversByRegion", [])
        if isinstance(item, dict)
    ]
    return ServerCondition(
        online=_optional_int(online.get("online")) or 0,
        in_lobby=_optional_int(online.get("inLobby")) or 0,
        in_searching=_optional_int(online.get("inSearching")) or 0,
        in_battle=_optional_int(online.get("inBattle")) or 0,
        instances=_optional_int(online.get("instances")) or 0,
        timestamp=_normalize_batrace_time(online.get("timestamp")),
        regions=regions,
        source="BATrace",
        detail_available=True,
    )


def _server_condition_from_steam(data: dict) -> ServerCondition:
    response = data.get("response") if isinstance(data.get("response"), dict) else {}
    return ServerCondition(
        online=_optional_int(response.get("player_count")) or 0,
        in_lobby=None,
        in_searching=None,
        in_battle=None,
        instances=None,
        timestamp=datetime.now(timezone.utc).isoformat(),
        regions=[],
        source="Steam",
        detail_available=False,
    )


def _server_condition_is_fresh(condition: ServerCondition, max_age_seconds: int = 30 * 60) -> bool:
    if not condition.timestamp:
        return False
    try:
        timestamp = datetime.fromisoformat(condition.timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    age = datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
    return 0 <= age.total_seconds() <= max_age_seconds


def _normalize_batrace_time(value: object) -> str | None:
    if not value:
        return None
    raw = str(value)
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return raw
    if timestamp - datetime.now(timezone.utc) > timedelta(hours=1):
        timestamp -= timedelta(hours=8)
    return timestamp.isoformat()


def _distribution_buckets(items: object) -> list[DistributionBucket]:
    if not isinstance(items, list):
        return []
    buckets: list[DistributionBucket] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        bucket = _optional_float(item.get("bucket"))
        count = _optional_int(item.get("count"))
        if bucket is None or count is None:
            continue
        buckets.append(DistributionBucket(bucket, count))
    return buckets


def _category_name(key: str) -> str:
    return {
        "infantry": "步兵",
        "vehicles": "载具",
        "support": "支援",
        "helicopters": "直升机",
        "aircrafts": "战机",
        "recon": "侦察",
        "logistic": "后勤",
    }.get(key, key)


def _category_name_by_id(category_id: object) -> str:
    return {
        0: "侦察",
        1: "步兵",
        2: "载具",
        3: "支援",
        4: "后勤",
        5: "直升机",
        6: "战机",
    }.get(_optional_int(category_id), "未知")


def _recent_win_rate(points: list[dict]) -> float | None:
    if not points:
        return None
    wins = sum(1 for item in points if item.get("won") is True)
    return wins / len(points)


def _recent_avg_objectives(points: list[dict]) -> float | None:
    values = [float(item.get("objectivesCaptured") or 0) for item in points]
    return sum(values) / len(values) if values else None


def _recent_avg_net_score(points: list[dict]) -> float | None:
    values = [
        float(item.get("destructionScore") or 0) - float(item.get("lossesScore") or 0)
        for item in points
    ]
    return sum(values) / len(values) if values else None


def _recent_rating_delta(points: list[dict]) -> float | None:
    deltas = [
        float(item.get("ratingAfter") or 0) - float(item.get("ratingBefore") or 0)
        for item in points
        if item.get("ratingAfter") is not None and item.get("ratingBefore") is not None
    ]
    return sum(deltas) if deltas else None
