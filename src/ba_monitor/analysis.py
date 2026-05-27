from datetime import datetime, timezone

from ba_monitor.commands import Command, CommandType, help_text
from ba_monitor.providers import (
    GameDataProvider,
    MatchSummary,
    MetaSnapshot,
    PlayerStats,
    RecentMatch,
    UnitStats,
)


async def handle_command(command: Command, provider: GameDataProvider) -> str:
    try:
        return await _handle_command(command, provider)
    except ValueError as exc:
        return str(exc)


async def _handle_command(command: Command, provider: GameDataProvider) -> str:
    if command.type == CommandType.HELP:
        return help_text()
    if command.type == CommandType.PLAYER:
        if not command.argument:
            return "请提供 SteamID64，例如：/player 76561198157609957"
        return format_player(await provider.get_player(command.argument))
    if command.type == CommandType.RECENT:
        if not command.argument:
            return "请提供 SteamID64，例如：/recent 76561198157609957"
        return format_recent_matches(await provider.get_recent_matches(command.argument))
    if command.type == CommandType.MATCH:
        if not command.argument:
            return "请提供对局 ID，例如：/match 5545812"
        return format_match(await provider.get_match(command.argument))
    if command.type == CommandType.UNIT:
        if not command.argument:
            return "请提供单位名，例如：/unit T-90M"
        return format_unit(await provider.get_unit(command.argument))
    if command.type == CommandType.META:
        return format_meta(await provider.get_meta())
    return "我还不认识这个指令。发送 /help 查看可用指令。"


def format_player(stats: PlayerStats) -> str:
    rank = f"#{stats.rank}" if stats.rank is not None and stats.rank >= 0 else "未上榜"
    leave_rate = stats.leaves / stats.matches if stats.matches else 0
    return "\n".join(
        [
            f"玩家：{stats.name}",
            f"SteamID：{stats.steam_id}",
            f"ELO：{stats.rating}，排名：{rank}，等级：{stats.level + 1}",
            f"排位：{stats.matches} 场，胜率：{stats.win_rate:.1%}，K/D：{stats.kd_ratio:.3f}",
            f"掉线/退局：{stats.leaves} 次（{leave_rate:.1%}）",
        ]
    )


def format_recent_matches(matches: list[RecentMatch]) -> str:
    if not matches:
        return "没有查到近期对局。"
    lines = ["最近对局："]
    for match in matches:
        delta = "无 ELO"
        if match.rating_delta is not None:
            sign = "+" if match.rating_delta >= 0 else ""
            delta = f"{sign}{match.rating_delta:.1f}"
        lines.append(
            f"#{match.match_id} 地图{match.map_id or '?'} {match.result} ELO {delta} "
            f"{_format_duration(match.duration_seconds)} {_format_time(match.ended_at)}"
        )
    return "\n".join(lines)


def format_match(match: MatchSummary) -> str:
    winner = f"Team {match.winner_team}" if match.winner_team is not None else "未知"
    return "\n".join(
        [
            f"对局：#{match.match_id}",
            f"地图：{match.map_id or '?'}，玩家数：{match.player_count}，胜方：{winner}",
            f"时长：{_format_duration(match.duration_seconds)}，结束：{_format_time(match.ended_at)}",
            f"最高歼灭：{match.top_destruction or '暂无'}",
            f"最高伤害：{match.top_damage or '暂无'}",
        ]
    )


def format_unit(stats: UnitStats) -> str:
    return "\n".join(
        [
            f"单位：{stats.name}",
            f"定位：{stats.role}",
            f"登场率：{stats.pick_rate:.1%}，胜率：{stats.win_rate:.1%}",
            f"简评：{stats.note}",
        ]
    )


def format_meta(snapshot: MetaSnapshot) -> str:
    units = "、".join(snapshot.trending_units)
    return "\n".join(
        [
            f"版本：{snapshot.patch}",
            f"当前强势阵营：{snapshot.strongest_faction}",
            f"热门单位：{units}",
            f"备注：{snapshot.note}",
        ]
    )


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "时长未知"
    minutes, sec = divmod(seconds, 60)
    return f"{minutes}分{sec:02d}秒"


def _format_time(epoch: int | None) -> str:
    if not epoch:
        return ""
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
