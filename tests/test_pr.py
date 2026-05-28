from ba_monitor.pr import calculate_player_rating, rating_label
from ba_monitor.providers import PlayerStats


def test_rating_labels() -> None:
    assert rating_label(20) == "蛆"
    assert rating_label(50) == "有点蛆"
    assert rating_label(60) == "平平无奇"
    assert rating_label(70) == "不错"
    assert rating_label(80) == "很不错"
    assert rating_label(90) == "神"
    assert rating_label(99) == "超神"


def test_calculate_player_rating_rewards_strong_stats() -> None:
    strong = PlayerStats("Kirisame", "76561198157609957", 2400, 20, 0.62, 1.35, 300, 1, 50)
    weak = PlayerStats("Cirno", "76561198157609958", 1000, None, 0.40, 0.65, 20, 4, 12)

    assert calculate_player_rating(strong).score > calculate_player_rating(weak).score
