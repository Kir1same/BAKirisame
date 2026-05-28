from __future__ import annotations

from dataclasses import dataclass

from ba_monitor.providers import PlayerAnalysis, PlayerStats

RANKED_TOTAL_ESTIMATE = 200_000


@dataclass(frozen=True)
class PlayerRating:
    score: int
    label: str


def calculate_player_rating(stats: PlayerStats, analysis: PlayerAnalysis | None = None) -> PlayerRating:
    # PR should reward winning and team-positive play first. K/D is intentionally
    # capped with diminishing returns so farming kills cannot dominate the score.
    base = (
        _win_rate_score(stats.win_rate) * 0.46
        + _elo_score(stats.rating) * 0.18
        + _rank_score(stats.rank, stats.ranked_total) * 0.18
        + _kd_score(stats.kd_ratio) * 0.05
        + _sample_score(stats.matches) * 0.07
        + _recent_adjustment(analysis)
        - _leave_penalty(stats.leaves, stats.matches)
        + 10
    )
    normalized = max(0, min(3000, round(base * 30)))
    return PlayerRating(score=normalized, label=rating_label(normalized))


def rating_label(score: int) -> str:
    if score < 900:
        return "蛆"
    if score < 1150:
        return "有点蛆"
    if score < 1400:
        return "平平无奇"
    if score < 1700:
        return "不错"
    if score < 2050:
        return "很不错"
    if score < 2450:
        return "神"
    return "超神"


def _elo_score(rating: int) -> float:
    return _clamp((rating - 900) / 18)


def _rank_score(rank: int | None, total: int | None) -> float:
    if rank is None or rank < 0:
        return 35
    denominator = total or RANKED_TOTAL_ESTIMATE
    if denominator <= 0:
        return 35
    percentile = max(0.0, min(1.0, rank / denominator))
    if percentile <= 0.001:
        return 100
    if percentile <= 0.005:
        return 94
    if percentile <= 0.02:
        return 86
    if percentile <= 0.05:
        return 78
    if percentile <= 0.10:
        return 68
    if percentile <= 0.20:
        return 55
    if percentile <= 0.40:
        return 40
    return 25


def _win_rate_score(win_rate: float) -> float:
    return _clamp((win_rate - 0.38) / 0.0032)


def _kd_score(kd_ratio: float) -> float:
    if kd_ratio <= 0.6:
        return 0
    capped = min(kd_ratio, 2.0)
    return _clamp(((capped - 0.6) / 1.4) ** 0.65 * 100)


def _sample_score(matches: int) -> float:
    return _clamp(matches / 3)


def _leave_penalty(leaves: int, matches: int) -> float:
    if not matches:
        return 0
    return min(8, leaves / matches * 120)


def _recent_adjustment(analysis: PlayerAnalysis | None) -> float:
    if analysis is None or analysis.match_count < 10:
        return 0
    adjustment = 0.0
    if analysis.recent_win_rate is not None:
        adjustment += max(-3.0, min(3.5, (analysis.recent_win_rate - 0.52) * 35))
    if analysis.recent_avg_objectives is not None:
        adjustment += max(0.0, min(1.2, (analysis.recent_avg_objectives - 1.0) * 0.55))
    if analysis.recent_avg_net_score is not None:
        adjustment += max(-3.0, min(2.5, analysis.recent_avg_net_score / 900))
    if analysis.recent_rating_delta is not None:
        adjustment += max(-1.5, min(1.5, analysis.recent_rating_delta / 350))
    return max(-7.0, min(5.8, adjustment))


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
