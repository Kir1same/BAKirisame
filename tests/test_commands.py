import pytest

from ba_monitor.analysis import handle_command
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
    command = parse_command("<@12345> /recent 76561198157609957")

    assert command.type == CommandType.RECENT
    assert command.argument == "76561198157609957"


@pytest.mark.asyncio
async def test_handle_player_command() -> None:
    command = parse_command("/player 76561198157609957")
    response = await handle_command(command, MockGameDataProvider())

    assert "76561198157609957" in response
    assert "ELO" in response


@pytest.mark.asyncio
async def test_handle_recent_command() -> None:
    command = parse_command("/recent 76561198157609957")
    response = await handle_command(command, MockGameDataProvider())

    assert "最近对局" in response
    assert "#5545812" in response


@pytest.mark.asyncio
async def test_unknown_command() -> None:
    command = parse_command("/deck")
    response = await handle_command(command, MockGameDataProvider())

    assert "/help" in response
