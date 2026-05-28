from __future__ import annotations

from dataclasses import dataclass

from ba_monitor.providers import PlayerStats


@dataclass(frozen=True)
class PlayerRating:
    score: int
    label: str


def calculate_player_rating(stats: PlayerStats) -> PlayerRating:
    score = (
        _elo_score(stats.rating) * 0.38
        + _win_rate_score(stats.win_rate) * 0.28
        + _kd_score(stats.kd_ratio) * 0.22
        + _sample_score(stats.matches) * 0.08
        - _leave_penalty(stats.leaves, stats.matches)
        + 4
    )
    normalized = max(0, min(100, round(score)))
    return PlayerRating(score=normalized, label=rating_label(normalized))


def rating_label(score: int) -> str:
    if score < 45:
        return "蛆"
    if score < 55:
        return "有点蛆"
    if score < 65:
        return "平平无奇"
    if score < 75:
        return "不错"
    if score < 85:
        return "很不错"
    if score < 95:
        return "神"
    return "超神"


def _elo_score(rating: int) -> float:
    return _clamp((rating - 900) / 18)


def _win_rate_score(win_rate: float) -> float:
    return _clamp((win_rate - 0.38) / 0.0032)


def _kd_score(kd_ratio: float) -> float:
    return _clamp((kd_ratio - 0.55) / 0.012)


def _sample_score(matches: int) -> float:
    return _clamp(matches / 3)


def _leave_penalty(leaves: int, matches: int) -> float:
    if not matches:
        return 0
    return min(18, leaves / matches * 220)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
