from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ba_monitor.pr import PlayerRating, calculate_player_rating
from ba_monitor.providers import MatchSummary, PlayerStats, RecentMatch

CARD_DIR = Path("artifacts/cards")
WIDTH = 1200
HEIGHT = 720

BG = "#080b12"
PANEL = "#101723"
PANEL_2 = "#162131"
LINE = "#28374a"
TEXT = "#f3f7fb"
MUTED = "#9ba8b7"
BLUE = "#5fb4ff"
GREEN = "#58d68d"
RED = "#ff6b6b"
AMBER = "#ffd166"


def render_player_card(stats: PlayerStats, path: Path | None = None, rating: PlayerRating | None = None) -> Path:
    rating = rating or calculate_player_rating(stats)
    image, draw = new_canvas()
    title(draw, "BROKEN ARROW", "PLAYER INTEL", stats.name)
    badge(draw, 910, 58, f"PR {rating.score}", rating_color(rating.score))

    draw_metric(draw, 64, 178, 250, 128, "ELO", str(stats.rating), BLUE)
    draw_metric(draw, 336, 178, 250, 128, "WIN RATE", f"{stats.win_rate:.1%}", GREEN)
    draw_metric(draw, 608, 178, 250, 128, "K/D", f"{stats.kd_ratio:.3f}", AMBER)
    draw_metric(draw, 880, 178, 250, 128, "EVALUATION", rating.label, rating_color(rating.score))

    draw_section(draw, 64, 352, 1066, 228, "CAREER SUMMARY")
    draw_text(draw, (96, 408), f"SteamID  {stats.steam_id}", 28, TEXT)
    draw_text(draw, (96, 456), f"Rank     {format_rank(stats.rank)}", 28, TEXT)
    draw_text(draw, (96, 504), f"Matches  {stats.matches}  |  Leaves {stats.leaves} ({safe_rate(stats.leaves, stats.matches):.1%})", 28, TEXT)
    if stats.updated_at:
        draw_text(draw, (96, 552), f"Updated  {stats.updated_at}", 24, MUTED)

    draw_progress(draw, 610, 420, 440, 22, stats.win_rate, GREEN, "Win Rate")
    draw_progress(draw, 610, 496, 440, 22, min(stats.kd_ratio / 2.0, 1.0), AMBER, "K/D Pressure")

    footer(draw)
    return save(image, path or default_path("player", stats.steam_id))


def render_recent_card(player: PlayerStats, matches: list[RecentMatch], path: Path | None = None) -> Path:
    image, draw = new_canvas()
    title(draw, "BROKEN ARROW", "RECENT FORM", player.name)
    badge(draw, 930, 58, f"ELO {player.rating}", BLUE)

    wins = sum(1 for item in matches if normalize_result(item.result) == "win")
    losses = sum(1 for item in matches if normalize_result(item.result) == "loss")
    total_delta = sum(item.rating_delta or 0 for item in matches)
    draw_metric(draw, 64, 162, 250, 112, "RECENT", f"{wins}-{losses}", GREEN if wins >= losses else RED)
    draw_metric(draw, 336, 162, 250, 112, "ELO DELTA", signed(total_delta), GREEN if total_delta >= 0 else RED)
    draw_metric(draw, 608, 162, 250, 112, "WIN RATE", f"{safe_rate(wins, len(matches)):.1%}", GREEN)
    draw_metric(draw, 880, 162, 250, 112, "SAMPLE", str(len(matches)), TEXT)

    draw_section(draw, 64, 316, 1066, 304, "MATCH HISTORY")
    y = 372
    for item in matches[:5]:
        result = normalize_result(item.result)
        color = GREEN if result == "win" else RED if result == "loss" else MUTED
        draw.rounded_rectangle((96, y, 1098, y + 42), radius=8, fill="#0c121b", outline="#1d2a3a")
        draw_text(draw, (116, y + 8), f"#{item.match_id}", 22, TEXT)
        draw_text(draw, (288, y + 8), f"地图 {item.map_id or '?'}", 22, MUTED)
        draw_text(draw, (430, y + 8), format_result_badge(result), 22, color)
        draw_text(draw, (590, y + 8), f"ELO {signed(item.rating_delta)}", 22, color)
        draw_text(draw, (750, y + 8), format_duration(item.duration_seconds), 22, MUTED)
        draw_text(draw, (940, y + 8), format_time(item.ended_at), 22, MUTED)
        y += 52

    footer(draw)
    return save(image, path or default_path("recent", player.steam_id))


def render_match_card(match: MatchSummary, path: Path | None = None) -> Path:
    image, draw = new_canvas()
    title(draw, "BROKEN ARROW", "MATCH REPORT", f"#{match.match_id}")
    badge(draw, 920, 58, f"TEAM {match.winner_team or '?'} WON", GREEN)

    draw_metric(draw, 64, 178, 250, 128, "MAP", str(match.map_id or "?"), BLUE)
    draw_metric(draw, 336, 178, 250, 128, "PLAYERS", str(match.player_count), TEXT)
    draw_metric(draw, 608, 178, 250, 128, "DURATION", format_duration(match.duration_seconds), AMBER)
    draw_metric(draw, 880, 178, 250, 128, "ENDED", format_time(match.ended_at) or "N/A", MUTED)

    draw_section(draw, 64, 352, 1066, 228, "TOP PERFORMERS")
    draw_text(draw, (96, 426), f"最高歼灭  {match.top_destruction or '暂无'}", 34, TEXT)
    draw_text(draw, (96, 500), f"最高伤害  {match.top_damage or '暂无'}", 34, TEXT)

    footer(draw)
    return save(image, path or default_path("match", str(match.match_id)))


def new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        shade = int(10 + y / HEIGHT * 18)
        draw.line((0, y, WIDTH, y), fill=(shade, shade + 3, shade + 8))
    draw.rectangle((0, 0, WIDTH, HEIGHT), outline="#1b2738", width=3)
    draw.line((0, 132, WIDTH, 132), fill="#203047", width=2)
    return image, draw


def title(draw: ImageDraw.ImageDraw, eyebrow: str, label: str, main: str) -> None:
    draw_text(draw, (64, 42), eyebrow, 22, BLUE)
    draw_text(draw, (64, 76), label, 18, MUTED)
    draw_text(draw, (244, 54), truncate(main, 30), 48, TEXT, bold=True)


def badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, color: str) -> None:
    draw.rounded_rectangle((x, y, x + 220, y + 44), radius=8, fill="#0d141f", outline=color, width=2)
    draw_text(draw, (x + 18, y + 10), text, 22, color, bold=True)


def draw_metric(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, label: str, value: str, color: str) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=PANEL, outline=LINE, width=2)
    draw_text(draw, (x + 22, y + 22), label, 19, MUTED)
    draw_text(draw, (x + 22, y + 62), truncate(value, 12), 38, color, bold=True)


def draw_section(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, label: str) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=PANEL_2, outline=LINE, width=2)
    draw_text(draw, (x + 28, y + 24), label, 22, BLUE, bold=True)
    draw.line((x + 28, y + 62, x + w - 28, y + 62), fill=LINE, width=2)


def draw_progress(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, value: float, color: str, label: str) -> None:
    value = max(0.0, min(1.0, value))
    draw_text(draw, (x, y - 34), f"{label}  {value:.0%}", 22, MUTED)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill="#0a1018", outline="#203047")
    draw.rounded_rectangle((x, y, x + math.floor(w * value), y + h), radius=8, fill=color)


def footer(draw: ImageDraw.ImageDraw) -> None:
    draw_text(draw, (64, 660), "BA Monitor Kirisame · data via BArmory STB", 20, MUTED)
    draw_text(draw, (920, 660), datetime.now().strftime("%Y-%m-%d %H:%M"), 20, MUTED)


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    fill: str,
    bold: bool = False,
) -> None:
    draw.text(xy, text, font=get_font(size, bold), fill=fill)


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def save(image: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
    return path


def default_path(kind: str, key: str) -> Path:
    safe_key = "".join(ch for ch in key if ch.isalnum() or ch in ("-", "_"))[:40]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return CARD_DIR / f"{kind}_{safe_key}_{stamp}.png"


def signed(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"+{value:.1f}" if value >= 0 else f"{value:.1f}"


def safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def format_rank(rank: int | None) -> str:
    return f"#{rank}" if rank is not None and rank >= 0 else "N/A"


def rating_color(score: int) -> str:
    if score >= 85:
        return AMBER
    if score >= 65:
        return GREEN
    if score >= 55:
        return BLUE
    return RED


def normalize_result(result: str) -> str:
    return {
        "win": "win",
        "victory": "win",
        "胜利": "win",
        "loss": "loss",
        "defeat": "loss",
        "失败": "loss",
    }.get(result.lower() if result else "", "unknown")


def format_result_badge(result: str) -> str:
    return {
        "win": "WIN",
        "loss": "LOSS",
        "unknown": "UNKNOWN",
    }.get(result, "UNKNOWN")


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return "N/A"
    minutes, sec = divmod(seconds, 60)
    return f"{minutes}m {sec:02d}s"


def format_time(epoch: int | None) -> str:
    if not epoch:
        return ""
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%m-%d %H:%M")


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
