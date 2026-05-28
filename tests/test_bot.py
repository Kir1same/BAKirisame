import pytest

from ba_monitor.bindings import BindingStore, UserContext
from ba_monitor.bot import parse_optional_player_steam_id, parse_player_card_steam_id
from ba_monitor.commands import parse_command


def test_player_card_uses_explicit_steam_id(tmp_path) -> None:
    bindings = BindingStore(tmp_path / "bindings.json")
    command = parse_command("/player 76561198157609957")

    steam_id = parse_player_card_steam_id(command, UserContext(user_key="qq-user"), bindings)

    assert steam_id == "76561198157609957"


def test_player_card_without_argument_uses_binding(tmp_path) -> None:
    bindings = BindingStore(tmp_path / "bindings.json")
    bindings.bind("qq-user", "76561198157609957")
    command = parse_command("/player")

    steam_id = parse_player_card_steam_id(command, UserContext(user_key="qq-user"), bindings)

    assert steam_id == "76561198157609957"


def test_player_card_without_argument_requires_binding(tmp_path) -> None:
    bindings = BindingStore(tmp_path / "bindings.json")

    with pytest.raises(ValueError):
        parse_player_card_steam_id(parse_command("/player"), UserContext(user_key="qq-user"), bindings)


def test_rank_card_uses_explicit_steam_id(tmp_path) -> None:
    bindings = BindingStore(tmp_path / "bindings.json")

    steam_id = parse_optional_player_steam_id(parse_command("/rank 76561198157609957"), UserContext(user_key="qq-user"), bindings)

    assert steam_id == "76561198157609957"


def test_rank_card_without_argument_uses_binding(tmp_path) -> None:
    bindings = BindingStore(tmp_path / "bindings.json")
    bindings.bind("qq-user", "76561198157609957")

    steam_id = parse_optional_player_steam_id(parse_command("/rank"), UserContext(user_key="qq-user"), bindings)

    assert steam_id == "76561198157609957"
