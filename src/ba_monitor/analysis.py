from datetime import datetime, timezone

from ba_monitor.bindings import BindingStore, UserContext
from ba_monitor.commands import Command, CommandType, help_text
from ba_monitor.providers import (
    GameDataProvider,
    MatchSummary,
    MetaSnapshot,
    PlayerStats,
    RecentMatch,
    UnitStats,
)


async def handle_command(
    command: Command,
    provider: GameDataProvider,
    context: UserContext | None = None,
    bindings: BindingStore | None = None,
) -> str:
    try:
        return await _handle_command(command, provider, context or UserContext(), bindings or BindingStore())
    except ValueError as exc:
        return str(exc)


async def _handle_command(
    command: Command,
    provider: GameDataProvider,
    context: UserContext,
    bindings: BindingStore,
) -> str:
    if command.type == CommandType.HELP:
        return help_text()
    if command.type == CommandType.BIND:
        return await handle_bind(command.argument, context, bindings, provider)
    if command.type == CommandType.UNBIND:
        return handle_unbind(context, bindings)
    if command.type == CommandType.ME:
        steam_id = require_bound_steam_id(context, bindings)
        return format_player(await provider.get_player(steam_id))
    if command.type == CommandType.PLAYER:
        steam_id = command.argument.strip() or require_bound_steam_id(context, bindings)
        return format_player(await provider.get_player(steam_id))
    if command.type == CommandType.RANK:
        steam_id = command.argument.strip() or require_bound_steam_id(context, bindings)
        return format_rank_position(await provider.get_player(steam_id))
    if command.type == CommandType.RECENT:
        steam_id, days = parse_recent_argument(command.argument, context, bindings)
        return format_recent_matches(await provider.get_recent_matches(steam_id, days=days), days)
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


async def handle_bind(argument: str, context: UserContext, bindings: BindingStore, provider: GameDataProvider) -> str:
    if not context.user_key:
        return "当前 QQ 场景没有可用用户标识，暂时不能绑定。"
    if not argument.strip():
        return "请提供 SteamID64、玩家 ID 或玩家名，例如：/bind 山雾谷雨"
    stats = await provider.get_player(argument.strip())
    steam_id = stats.steam_id
    bindings.bind(context.user_key, steam_id)
    return f"绑定成功：{stats.name}（SteamID：{steam_id}）。以后发送 /me、/recent、/rank 会默认查询这个账号。"


def handle_unbind(context: UserContext, bindings: BindingStore) -> str:
    if not context.user_key:
        return "当前 QQ 场景没有可用用户标识，暂时不能解绑。"
    if bindings.unbind(context.user_key):
        return "已解除绑定。"
    return "你还没有绑定账号。"


def require_bound_steam_id(context: UserContext, bindings: BindingStore) -> str:
    steam_id = bindings.get_steam_id(context.user_key)
    if not steam_id:
        raise ValueError("你还没有绑定账号。先发送 /bind <SteamID64>，例如：/bind 76561198157609957")
    return steam_id


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


def format_rank_position(stats: PlayerStats) -> str:
    rank = f"#{stats.rank}" if stats.rank is not None and stats.rank >= 0 else "未上榜"
    total = stats.ranked_total or 0
    percent = stats.rank / total if stats.rank is not None and stats.rank >= 0 and total else None
    percent_text = f"前{percent:.1%}" if percent is not None else "百分位未知"
    return "\n".join(
        [
            f"玩家：{stats.name}",
            f"ELO：{stats.rating}",
            f"全服排名：{rank}（{percent_text}）",
            f"总玩家数：{total:,}" if total else "总玩家数：暂不可用",
        ]
    )


def parse_recent_argument(argument: str, context: UserContext, bindings: BindingStore) -> tuple[str, int]:
    parts = argument.split()
    steam_id = ""
    days = 1
    for part in parts:
        if part.isdigit() and len(part) < 16:
            days = parse_recent_days(part)
        else:
            steam_id = part
    return steam_id or require_bound_steam_id(context, bindings), days


def parse_recent_days(value: str) -> int:
    try:
        days = int(value)
    except ValueError as exc:
        raise ValueError("天数必须是数字，例如：/recent 3") from exc
    if days < 1 or days > 30:
        raise ValueError("近期战绩天数支持 1-30 天，例如：/recent 7")
    return days


def format_recent_matches(matches: list[RecentMatch], days: int = 1) -> str:
    if not matches:
        return f"最近 {days} 天没有查到可用对局。"
    lines = [f"最近 {days} 天对局："]
    for match in matches:
        delta = "无 ELO"
        if match.rating_delta is not None:
            sign = "+" if match.rating_delta >= 0 else ""
            delta = f"{sign}{match.rating_delta:.1f}"
        lines.append(
            f"#{match.match_id} 地图{match.map_id or '?'} {format_result(match.result)} ELO {delta} "
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


def format_result(result: str) -> str:
    return {
        "win": "胜利",
        "loss": "失败",
        "unknown": "未知",
    }.get(result, result or "未知")


def _format_time(epoch: int | None) -> str:
    if not epoch:
        return ""
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
