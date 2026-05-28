from ba_monitor.cards import render_match_card, render_player_card, render_recent_card
from ba_monitor.providers import MatchSummary, PlayerStats, RecentMatch


def test_render_player_card(tmp_path) -> None:
    path = render_player_card(
        PlayerStats(
            name="Kirisame",
            steam_id="76561198157609957",
            rating=2450,
            rank=42,
            win_rate=0.612,
            kd_ratio=1.337,
            matches=320,
            leaves=2,
            level=51,
            updated_at="2026-05-27T20:00:00Z",
        ),
        tmp_path / "player.png",
    )

    assert path.exists()
    assert path.stat().st_size > 10_000


def test_render_recent_card(tmp_path) -> None:
    player = PlayerStats("Kirisame", "76561198157609957", 2450, 42, 0.612, 1.337, 320, 2, 51)
    matches = [
        RecentMatch(5545812, 4, "win", 12.3, 2136, 1772992500),
        RecentMatch(5545813, 8, "loss", -8.1, 1902, 1772993500),
    ]
    path = render_recent_card(player, matches, tmp_path / "recent.png")

    assert path.exists()
    assert path.stat().st_size > 10_000


def test_render_match_card(tmp_path) -> None:
    path = render_match_card(
        MatchSummary(5545812, 4, 2136, 1772992500, 1, 10, "Kirisame (3200)", "Marisa (9000)"),
        tmp_path / "match.png",
    )

    assert path.exists()
    assert path.stat().st_size > 10_000
