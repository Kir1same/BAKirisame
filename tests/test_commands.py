import pytest

from ba_monitor.analysis import handle_command
from ba_monitor.bindings import BindingStore, UserContext
from ba_monitor.commands import CommandType, parse_command
from ba_monitor.providers import MockGameDataProvider


def test_parse_slash_command() -> None:
    command = parse_command("/player 76561198157609957")

    assert command.type == CommandType.PLAYER
    assert command.argument == "76561198157609957"


def test_parse_chinese_alias() -> None:
    command = parse_command("玩家 76561198157609957")

    assert command.type == CommandType.PLAYER
    assert command.argument == "76561198157609957"


def test_parse_recent_command() -> None:
    command = parse_command("<@12345> /近期战绩")

    assert command.type == CommandType.RECENT
    assert command.argument == ""


@pytest.mark.asyncio
async def test_handle_player_command() -> None:
    command = parse_command("/player 76561198157609957")
    response = await handle_command(command, MockGameDataProvider())

    assert "76561198157609957" in response
    assert "ELO" in response


@pytest.mark.asyncio
async def test_recent_requires_binding_when_no_argument(tmp_path) -> None:
    command = parse_command("/recent")
    response = await handle_command(
        command,
        MockGameDataProvider(),
        UserContext(user_key="qq-user"),
        BindingStore(tmp_path / "bindings.json"),
    )

    assert "还没有绑定账号" in response


@pytest.mark.asyncio
async def test_bind_then_recent_uses_bound_steam_id(tmp_path) -> None:
    bindings = BindingStore(tmp_path / "bindings.json")
    context = UserContext(user_key="qq-user")

    bind_response = await handle_command(
        parse_command("/bind 76561198157609957"),
        MockGameDataProvider(),
        context,
        bindings,
    )
    recent_response = await handle_command(parse_command("/recent"), MockGameDataProvider(), context, bindings)

    assert "绑定成功" in bind_response
    assert "最近 1 天对局" in recent_response
    assert "#5545812" in recent_response


@pytest.mark.asyncio
async def test_recent_accepts_days_argument(tmp_path) -> None:
    bindings = BindingStore(tmp_path / "bindings.json")
    context = UserContext(user_key="qq-user")
    bindings.bind("qq-user", "76561198157609957")

    response = await handle_command(parse_command("/recent 3"), MockGameDataProvider(), context, bindings)

    assert "最近 3 天对局" in response


@pytest.mark.asyncio
async def test_recent_rejects_out_of_range_days(tmp_path) -> None:
    bindings = BindingStore(tmp_path / "bindings.json")
    context = UserContext(user_key="qq-user")
    bindings.bind("qq-user", "76561198157609957")

    response = await handle_command(parse_command("/recent 31"), MockGameDataProvider(), context, bindings)

    assert "1-30 天" in response


@pytest.mark.asyncio
async def test_unknown_command() -> None:
    command = parse_command("/deck")
    response = await handle_command(command, MockGameDataProvider())

    assert "/help" in response
