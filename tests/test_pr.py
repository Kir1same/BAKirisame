from ba_monitor.pr import calculate_player_rating, rating_label
from ba_monitor.providers import PlayerAnalysis, PlayerStats


def test_rating_labels() -> None:
    assert rating_label(800) == "蛆"
    assert rating_label(1000) == "有点蛆"
    assert rating_label(1300) == "平平无奇"
    assert rating_label(1600) == "不错"
    assert rating_label(1900) == "很不错"
    assert rating_label(2300) == "神"
    assert rating_label(2600) == "超神"


def test_calculate_player_rating_rewards_strong_stats() -> None:
    strong = PlayerStats("Kirisame", "76561198157609957", 2400, 20, 0.62, 1.35, 300, 1, 50)
    weak = PlayerStats("Cirno", "76561198157609958", 1000, None, 0.40, 0.65, 20, 4, 12)

    assert calculate_player_rating(strong).score > calculate_player_rating(weak).score


def test_pr_prefers_winning_over_kd_farming() -> None:
    team_player = PlayerStats("Team", "76561198157609957", 1900, 2000, 0.58, 0.95, 300, 1, 45)
    kd_farmer = PlayerStats("Farmer", "76561198157609958", 1900, 2000, 0.48, 2.4, 300, 1, 45)

    assert calculate_player_rating(team_player).score > calculate_player_rating(kd_farmer).score


def test_pr_caps_extreme_kd_returns() -> None:
    good_kd = PlayerStats("Good", "76561198157609957", 1900, 2000, 0.53, 1.6, 300, 1, 45)
    extreme_kd = PlayerStats("Extreme", "76561198157609958", 1900, 2000, 0.53, 3.5, 300, 1, 45)

    assert calculate_player_rating(extreme_kd).score - calculate_player_rating(good_kd).score < 120


def test_pr_rewards_top_percentile_and_recent_winning() -> None:
    stats = PlayerStats(
        "Sample",
        "76561198379902699",
        2192,
        8774,
        0.5366,
        1.307,
        328,
        25,
        49,
        ranked_total=271_732,
    )
    analysis = PlayerAnalysis(
        match_count=50,
        category_preferences=[],
        highlight_units=[],
        play_style_axes=[],
        primary_style="",
        recent_win_rate=0.68,
        recent_avg_objectives=1.98,
        recent_avg_net_score=2498,
        recent_rating_delta=353,
    )

    rating = calculate_player_rating(stats, analysis)

    assert rating.score >= 1700
    assert rating.label == "很不错"


def test_pr_separates_strong_recent_from_rating_rebound() -> None:
    muon = PlayerStats(
        "Muon",
        "76561199111894291",
        2044,
        16098,
        0.5255,
        0.990,
        196,
        4,
        35,
    )
    muon_analysis = PlayerAnalysis(
        match_count=94,
        category_preferences=[],
        highlight_units=[],
        play_style_axes=[],
        primary_style="",
        recent_win_rate=0.5638,
        recent_avg_objectives=2.6,
        recent_avg_net_score=-360.2,
        recent_rating_delta=724.8,
    )
    stronger = PlayerStats(
        "Sample",
        "76561198379902699",
        2192,
        8774,
        0.5366,
        1.307,
        328,
        25,
        49,
    )
    stronger_analysis = PlayerAnalysis(
        match_count=50,
        category_preferences=[],
        highlight_units=[],
        play_style_axes=[],
        primary_style="",
        recent_win_rate=0.68,
        recent_avg_objectives=1.98,
        recent_avg_net_score=2498,
        recent_rating_delta=353,
    )

    assert calculate_player_rating(stronger, stronger_analysis).score > calculate_player_rating(muon, muon_analysis).score + 120
