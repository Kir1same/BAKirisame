from dataclasses import dataclass
from enum import Enum


class CommandType(str, Enum):
    HELP = "help"
    BIND = "bind"
    UNBIND = "unbind"
    ME = "me"
    PLAYER = "player"
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
            "/bind <SteamID> - 绑定自己的断箭账号",
            "/me - 查看已绑定账号概览",
            "/recent - 查询自己的近期战绩",
            "/player [SteamID] - 查询玩家；不填则查自己",
            "/recent [SteamID] - 查询近期战绩；不填则查自己",
            "/match <对局ID> - 查询单场对局简报",
            "/unit <单位名> - 查询单位表现（当前为示例数据）",
            "/meta - 查看环境摘要（当前为示例数据）",
            "/unbind - 解除绑定",
        ]
    )
