from dataclasses import dataclass
from enum import Enum


class CommandType(str, Enum):
    HELP = "help"
    BIND = "bind"
    UNBIND = "unbind"
    ME = "me"
    PLAYER = "player"
    RANK = "rank"
    RECENT = "recent"
    MATCH = "match"
    META = "meta"
    UNIT = "unit"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Command:
    type: CommandType
    argument: str = ""
    raw: str = ""


ALIASES = {
    "help": CommandType.HELP,
    "帮助": CommandType.HELP,
    "bind": CommandType.BIND,
    "绑定": CommandType.BIND,
    "unbind": CommandType.UNBIND,
    "解绑": CommandType.UNBIND,
    "me": CommandType.ME,
    "我": CommandType.ME,
    "player": CommandType.PLAYER,
    "玩家": CommandType.PLAYER,
    "rank": CommandType.RANK,
    "排名": CommandType.RANK,
    "recent": CommandType.RECENT,
    "近期": CommandType.RECENT,
    "近期战绩": CommandType.RECENT,
    "match": CommandType.MATCH,
    "对局": CommandType.MATCH,
    "meta": CommandType.META,
    "环境": CommandType.META,
    "unit": CommandType.UNIT,
    "单位": CommandType.UNIT,
}


def parse_command(text: str) -> Command:
    cleaned = strip_bot_mention(text).strip()
    if not cleaned:
        return Command(CommandType.HELP, raw=text)

    if cleaned.startswith("/"):
        cleaned = cleaned[1:]

    name, _, argument = cleaned.partition(" ")
    command_type = ALIASES.get(name.lower(), CommandType.UNKNOWN)
    return Command(command_type, argument.strip(), raw=text)


def strip_bot_mention(text: str) -> str:
    parts = text.replace("\u00a0", " ").split()
    while parts and (parts[0].startswith("<@") or parts[0].startswith("@")):
        parts.pop(0)
    return " ".join(parts)


def help_text() -> str:
    return "\n".join(
        [
            "BA Monitor Kirisame",
            "当前为测试版，仅列出已稳定指令：",
            "/bind <SteamID64|玩家ID|玩家名> - 绑定自己的断箭账号",
            "/unbind - 解除绑定",
            "/me - 查询已绑定账号的个人数据卡片",
            "/player <SteamID64|玩家ID|玩家名> - 查询其他玩家数据卡片",
            "/rank - 查询已绑定账号的全服排名位置",
            "/rank <SteamID64|玩家ID|玩家名> - 查询其他玩家全服排名位置",
            "/recent - 查询已绑定账号最近 1 天战绩",
            "/recent <天数> - 查询最近 N 天战绩，支持 1-30 天",
        ]
    )
