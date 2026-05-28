from ba_monitor.cards import rank_percent_text, rank_tier_color, render_match_card, render_player_card, render_recent_card
from ba_monitor.providers import (
    CategoryPreference,
    HighlightUnit,
    MatchSummary,
    PlayerAnalysis,
    PlayerStats,
    PlayStyleAxis,
    RecentMatch,
)


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


def test_render_player_card_with_analysis(tmp_path) -> None:
    analysis = PlayerAnalysis(
        match_count=50,
        category_preferences=[
            CategoryPreference("vehicles", "载具", 76000, 24.0),
            CategoryPreference("support", "支援", 66000, 21.0),
            CategoryPreference("infantry", "步兵", 52000, 16.5),
        ],
        highlight_units=[
            HighlightUnit(63, "Assaultmen SMAW", "步兵", 59, 2657.0, 4130, 0.64),
            HighlightUnit(11, "M142 HIMARS", "支援", 18, 4200.0, 3600, 1.17),
        ],
        play_style_axes=[
            PlayStyleAxis("aggression", 65, "aggressive"),
            PlayStyleAxis("economy", 79, "efficient"),
            PlayStyleAxis("teamplay", 88, "team_player"),
        ],
        primary_style="team_player",
    )
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
            kills=428,
            deaths=320,
            total_match_time_seconds=672000,
        ),
        tmp_path / "player-analysis.png",
        analysis=analysis,
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


def test_rank_percentile_uses_estimated_total_when_missing() -> None:
    assert rank_percent_text(10_000, None) == "前5.0%估算"
    assert rank_tier_color(10_000, None) == "#63b33d"
