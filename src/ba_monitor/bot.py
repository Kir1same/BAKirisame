import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import botpy
from botpy.message import C2CMessage, GroupMessage, Message

from ba_monitor.analysis import handle_command, parse_recent_argument
from ba_monitor.bindings import BindingStore, UserContext
from ba_monitor.cards import render_player_card, render_recent_card
from ba_monitor.commands import CommandType, parse_command
from ba_monitor.config import get_settings
from ba_monitor.image_host import ImageHost, build_image_host
from ba_monitor.providers import GameDataProvider, build_provider

LOGGER = logging.getLogger(__name__)
LOG_DIR = Path("logs")
QQ_MESSAGE_LOG = LOG_DIR / "qq_messages.log"
RETENTION_SECONDS = 24 * 60 * 60


class BrokenArrowBot(botpy.Client):
    def __init__(self, provider: GameDataProvider, image_host: ImageHost, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.provider = provider
        self.image_host = image_host
        self.bindings = BindingStore()

    async def on_at_message_create(self, message: Message) -> None:
        log_qq_message("channel", message)
        await self._reply_channel(message)

    async def on_group_at_message_create(self, message: GroupMessage) -> None:
        log_qq_message("group", message)
        await self._reply_group(message)

    async def on_c2c_message_create(self, message: C2CMessage) -> None:
        log_qq_message("c2c", message)
        await self._reply_c2c(message)

    async def _render(self, content: str, context: UserContext) -> str:
        command = parse_command(content)
        try:
            return await handle_command(command, self.provider, context, self.bindings)
        except Exception:
            LOGGER.exception("failed to handle command")
            return "查询失败了。可能是数据接口暂时不可用，请稍后再试。"

    async def _reply_channel(self, message: Message) -> None:
        content = await self._render(message.content, build_user_context(message))
        log_bot_reply("channel", message, content)
        await message.reply(content=content)

    async def _reply_group(self, message: GroupMessage) -> None:
        if await self._reply_group_card(message):
            return

        content = await self._render(message.content, build_user_context(message))
        log_bot_reply("group", message, content)
        await message._api.post_group_message(
            group_openid=message.group_openid,
            msg_type=0,
            msg_id=message.id,
            content=content,
        )

    async def _reply_c2c(self, message: C2CMessage) -> None:
        if await self._reply_c2c_card(message):
            return

        content = await self._render(message.content, build_user_context(message))
        log_bot_reply("c2c", message, content)
        await message._api.post_c2c_message(
            openid=message.author.user_openid,
            msg_type=0,
            msg_id=message.id,
            content=content,
        )

    async def _reply_group_card(self, message: GroupMessage) -> bool:
        command = parse_command(message.content)
        if command.type == CommandType.RECENT:
            return await self._reply_group_recent_card(message)
        if command.type != CommandType.ME:
            return False
        context = build_user_context(message)
        steam_id = self.bindings.get_steam_id(context.user_key)
        if not steam_id:
            return False
        try:
            stats = await self.provider.get_player(steam_id)
            analysis = await self._get_player_analysis(steam_id)
            image_url = await self.image_host.upload(render_player_card(stats, analysis=analysis))
            media = await message._api.post_group_file(
                group_openid=message.group_openid,
                file_type=1,
                url=image_url,
            )
            log_bot_reply("group", message, f"[image] {image_url}")
            await message._api.post_group_message(
                group_openid=message.group_openid,
                msg_type=7,
                msg_id=message.id,
                media=media,
            )
            return True
        except Exception:
            LOGGER.exception("failed to send group player card")
            return False

    async def _reply_c2c_card(self, message: C2CMessage) -> bool:
        command = parse_command(message.content)
        if command.type == CommandType.RECENT:
            return await self._reply_c2c_recent_card(message)
        if command.type != CommandType.ME:
            return False
        context = build_user_context(message)
        steam_id = self.bindings.get_steam_id(context.user_key)
        if not steam_id:
            return False
        try:
            stats = await self.provider.get_player(steam_id)
            analysis = await self._get_player_analysis(steam_id)
            image_url = await self.image_host.upload(render_player_card(stats, analysis=analysis))
            media = await message._api.post_c2c_file(
                openid=message.author.user_openid,
                file_type=1,
                url=image_url,
            )
            log_bot_reply("c2c", message, f"[image] {image_url}")
            await message._api.post_c2c_message(
                openid=message.author.user_openid,
                msg_type=7,
                msg_id=message.id,
                media=media,
            )
            return True
        except Exception:
            LOGGER.exception("failed to send c2c player card")
            return False

    async def _get_player_analysis(self, steam_id: str):
        try:
            return await self.provider.get_player_analysis(steam_id)
        except Exception:
            LOGGER.exception("failed to fetch player analysis")
            return None

    async def _reply_group_recent_card(self, message: GroupMessage) -> bool:
        command = parse_command(message.content)
        context = build_user_context(message)
        try:
            steam_id, days = parse_recent_argument(command.argument, context, self.bindings)
            player = await self.provider.get_player(steam_id)
            matches = await self.provider.get_recent_matches(steam_id, days=days)
            image_url = await self.image_host.upload(render_recent_card(player, matches))
            media = await message._api.post_group_file(
                group_openid=message.group_openid,
                file_type=1,
                url=image_url,
            )
            log_bot_reply("group", message, f"[image] {image_url}")
            await message._api.post_group_message(
                group_openid=message.group_openid,
                msg_type=7,
                msg_id=message.id,
                media=media,
            )
            return True
        except ValueError:
            return False
        except Exception:
            LOGGER.exception("failed to send group recent card")
            return False

    async def _reply_c2c_recent_card(self, message: C2CMessage) -> bool:
        command = parse_command(message.content)
        context = build_user_context(message)
        try:
            steam_id, days = parse_recent_argument(command.argument, context, self.bindings)
            player = await self.provider.get_player(steam_id)
            matches = await self.provider.get_recent_matches(steam_id, days=days)
            image_url = await self.image_host.upload(render_recent_card(player, matches))
            media = await message._api.post_c2c_file(
                openid=message.author.user_openid,
                file_type=1,
                url=image_url,
            )
            log_bot_reply("c2c", message, f"[image] {image_url}")
            await message._api.post_c2c_message(
                openid=message.author.user_openid,
                msg_type=7,
                msg_id=message.id,
                media=media,
            )
            return True
        except ValueError:
            return False
        except Exception:
            LOGGER.exception("failed to send c2c recent card")
            return False


def build_intents() -> botpy.Intents:
    return botpy.Intents(public_guild_messages=True, public_messages=True)


def configure_logging(level: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    prune_logs()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
    ]
    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(level=level.upper(), handlers=handlers, force=True)
    logging.getLogger("botpy").setLevel(logging.WARNING)
    LOGGER.info("logging configured; app_log=%s qq_message_log=%s", LOG_DIR / "app.log", QQ_MESSAGE_LOG)
    start_log_pruner()


def log_qq_message(scene: str, message: Any) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": "incoming",
        "scene": scene,
        "message_id": getattr(message, "id", None),
        "content": getattr(message, "content", ""),
        "author": extract_author(message),
        "group_openid": getattr(message, "group_openid", None),
        "guild_id": getattr(message, "guild_id", None),
        "channel_id": getattr(message, "channel_id", None),
    }
    append_jsonl(QQ_MESSAGE_LOG, record)
    LOGGER.info("qq message scene=%s id=%s content=%r", scene, record["message_id"], record["content"])


def log_bot_reply(scene: str, message: Any, content: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": "outgoing",
        "scene": scene,
        "reply_to_message_id": getattr(message, "id", None),
        "content": content,
        "group_openid": getattr(message, "group_openid", None),
        "guild_id": getattr(message, "guild_id", None),
        "channel_id": getattr(message, "channel_id", None),
    }
    append_jsonl(QQ_MESSAGE_LOG, record)
    LOGGER.info("qq reply scene=%s reply_to=%s content=%r", scene, record["reply_to_message_id"], content)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_author(message: Any) -> dict[str, Any]:
    author = getattr(message, "author", None)
    if author is None:
        return {}
    return {
        "id": getattr(author, "id", None),
        "username": getattr(author, "username", None),
        "user_openid": getattr(author, "user_openid", None),
        "member_openid": getattr(author, "member_openid", None),
    }


def build_user_context(message: Any) -> UserContext:
    author = getattr(message, "author", None)
    if author is None:
        return UserContext()
    user_key = (
        getattr(author, "user_openid", None)
        or getattr(author, "member_openid", None)
        or getattr(author, "id", None)
    )
    return UserContext(user_key=str(user_key)) if user_key else UserContext()


def start_log_pruner() -> None:
    def run() -> None:
        while True:
            time.sleep(60 * 60)
            try:
                prune_logs()
            except Exception:
                LOGGER.exception("failed to prune logs")

    thread = threading.Thread(target=run, name="log-pruner", daemon=True)
    thread.start()


def prune_logs() -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - RETENTION_SECONDS
    prune_jsonl_by_timestamp(QQ_MESSAGE_LOG, cutoff)
    prune_text_by_prefix_timestamp(LOG_DIR / "app.log", cutoff)
    prune_text_by_prefix_timestamp(LOG_DIR / "stdout.log", cutoff)
    prune_text_by_prefix_timestamp(LOG_DIR / "stderr.log", cutoff)


def prune_jsonl_by_timestamp(path: Path, cutoff: float) -> None:
    if not path.exists():
        return
    kept: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            timestamp = json.loads(line).get("timestamp")
            if timestamp is None or datetime.fromisoformat(timestamp).timestamp() >= cutoff:
                kept.append(line)
        except Exception:
            kept.append(line)
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def prune_text_by_prefix_timestamp(path: Path, cutoff: float) -> None:
    if not path.exists():
        return
    kept: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            timestamp = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if timestamp.timestamp() >= cutoff:
                kept.append(line)
        except ValueError:
            kept.append(line)
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    provider = build_provider(settings.ba_api_base_url, settings.ba_api_key, settings.data_source)
    image_host = build_image_host(settings.image_public_base_url, settings.image_public_dir)
    client = BrokenArrowBot(provider=provider, image_host=image_host, intents=build_intents())
    client.run(appid=settings.qq_app_id, secret=settings.qq_app_secret)
