from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ba_monitor.pr import PlayerRating, calculate_player_rating
from ba_monitor.providers import CategoryPreference, MatchSummary, PlayerAnalysis, PlayerStats, RecentMatch

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
RANKED_TOTAL_ESTIMATE = 200_000


def render_player_card(
    stats: PlayerStats,
    path: Path | None = None,
    rating: PlayerRating | None = None,
    analysis: PlayerAnalysis | None = None,
) -> Path:
    rating = rating or calculate_player_rating(stats, analysis)
    image, draw = new_player_canvas()
    pr_color = rating_color(rating.score)
    avg_kills = safe_rate(stats.kills, stats.matches)
    avg_minutes = safe_rate(stats.total_match_time_seconds, stats.matches) / 60

    draw.rectangle((48, 64, 1152, 274), fill="#eef1f5")
    draw.rectangle((64, 84, 72, 254), fill="#9aa1aa")
    draw_text(draw, (92, 92), truncate(stats.name, 22), 54, "#11151a", bold=True)
    draw_text(draw, (96, 154), f"STEAM -- {stats.steam_id}", 24, "#7a828d", bold=True)
    draw_text(draw, (96, 206), f"等级：{stats.level + 1}    全服排名：{format_rank_with_percent(stats.rank, stats.ranked_total)}", 26, "#373d45", bold=True)
    draw_text(draw, (620, 104), "BA Monitor Kirisame", 28, "#5fb4ff", bold=True)
    draw_text(draw, (620, 150), "BROKEN ARROW PLAYER REPORT", 22, "#6f7782")

    draw.rectangle((48, 306, 1152, 384), fill=pr_color)
    draw_text(draw, (74, 321), f"「{rating.label}」", 42, "#ffffff", bold=True)
    next_line = next_rating_delta(rating.score)
    draw_text(draw, (330, 340), f"距离下一评级：{next_line}", 22, "#ffffff", bold=True)
    draw_text(draw, (916, 324), f"PR: {rating.score:,}", 38, "#ffffff", bold=True)

    draw_performance_focus_panel(draw, 48, 408, stats, rating)
    draw_recent_effective_panel(draw, 48, 684, stats, rating, analysis)
    if analysis:
        draw_compact_analysis_panel(draw, 48, 970, analysis)
    else:
        draw_model_note_panel(draw, 48, 970)
    draw_pr_distribution(draw, 48, 1310, rating)

    draw_text(draw, (116, 1528), "Powered by BA Monitor Kirisame · data via BArmory STB", 24, "#9ca3ad", bold=True)
    note = "中部与辅助数据来自近期有效对局样本" if analysis else "近期有效对局暂不可用，已回退到基础战绩"
    draw_text(draw, (330 if analysis else 280, 1562), note, 22, "#a8afb8", bold=True)
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


def new_player_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1200, 1600), "#f5f6f8")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1200, 1600), fill="#f5f6f8")
    for y in range(0, 1600, 36):
        draw.line((48, y, 1152, y), fill="#edf0f3", width=1)
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


def draw_light_metric(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
    value: str,
    color: str,
) -> None:
    draw.rectangle((x, y, x + w, y + h), fill="#e5e8ec", outline="#d0d5da", width=2)
    draw.rectangle((x, y, x + w, y + 26), fill="#cfd4da")
    draw_text(draw, (x + 12, y + 5), label, 18, "#454b54", bold=True)
    draw_text(draw, (x + 18, y + 34), value, 34, color, bold=True)
    draw.line((x, y + h - 3, x + w, y + h - 3), fill="#66bde9", width=2)


def draw_section(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, label: str) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=PANEL_2, outline=LINE, width=2)
    draw_text(draw, (x + 28, y + 24), label, 22, BLUE, bold=True)
    draw.line((x + 28, y + 62, x + w - 28, y + 62), fill=LINE, width=2)


def draw_progress(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, value: float, color: str, label: str) -> None:
    value = max(0.0, min(1.0, value))
    draw_text(draw, (x, y - 34), f"{label}  {value:.0%}", 22, MUTED)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill="#0a1018", outline="#203047")
    draw.rounded_rectangle((x, y, x + math.floor(w * value), y + h), radius=8, fill=color)


def draw_light_section_header(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, label: str) -> None:
    draw.rectangle((x, y, x + w, y + 56), fill="#e3e6ea")
    draw.rectangle((x + 16, y + 16, x + 23, y + 44), fill="#8b929b")
    draw.rectangle((x + 31, y + 18, x + 214, y + 42), fill="#c5c9ce")
    draw_text(draw, (x + 48, y + 10), label, 34, "#161a20", bold=True)
    draw.line((x + 270, y + 39, x + w - 26, y + 39), fill="#b8bdc4", width=2)


def draw_table_header(draw: ImageDraw.ImageDraw, x: int, y: int, headers: list[tuple[str, int]]) -> None:
    cursor = x
    for label, width in headers:
        draw_text(draw, (cursor + 12, y + 10), label, 24, "#4e555e", bold=True)
        cursor += width


def draw_overall_table(draw: ImageDraw.ImageDraw, x: int, y: int, stats: PlayerStats, rating: PlayerRating) -> None:
    draw_light_section_header(draw, x, y, 1104, "总体数据")
    headers = [("总览", 180), ("场数", 128), ("评分(PR)", 190), ("胜率", 148), ("击杀", 150), ("K/D", 132), ("退局", 132)]
    draw_table_header(draw, x + 28, y + 62, headers)
    row_y = y + 112
    draw.rectangle((x, row_y, x + 1104, row_y + 52), fill="#e8eaee")
    values = [
        ("全部对局", 180, "#343a42"),
        (f"{stats.matches:,}", 128, "#11151a"),
        (f"{rating.label}({rating.score:,})", 190, rating_color(rating.score)),
        (f"{stats.win_rate:.2%}", 148, rating_color(round(stats.win_rate * 3000))),
        (f"{stats.kills:,}", 150, "#30acc4"),
        (f"{stats.kd_ratio:.3f}", 132, rating_color(round(min(stats.kd_ratio / 1.8, 1) * 3000))),
        (f"{stats.leaves}", 132, "#d64949" if stats.leaves else "#2f9e44"),
    ]
    cursor = x + 28
    for value, width, color in values:
        draw_text(draw, (cursor + 12, row_y + 10), value, 26, color, bold=True)
        cursor += width
    draw.rectangle((x, row_y + 54, x + 1104, row_y + 106), fill="#eef0f3")
    avg_kills = safe_rate(stats.kills, stats.matches)
    avg_deaths = safe_rate(stats.deaths, stats.matches)
    draw_text(
        draw,
        (x + 40, row_y + 68),
        f"累计死亡 {stats.deaths:,}    场均击杀 {avg_kills:.1f}    场均死亡 {avg_deaths:.1f}    退局率 {safe_rate(stats.leaves, stats.matches):.1%}",
        24,
        "#555d67",
        bold=True,
    )


def draw_performance_focus_panel(draw: ImageDraw.ImageDraw, x: int, y: int, stats: PlayerStats, rating: PlayerRating) -> None:
    draw_light_section_header(draw, x, y, 1104, "水平评估")
    avg_kills = safe_rate(stats.kills, stats.matches)
    avg_deaths = safe_rate(stats.deaths, stats.matches)
    avg_minutes = safe_rate(stats.total_match_time_seconds, stats.matches) / 60
    rank_color = rank_tier_color(stats.rank, stats.ranked_total)
    elo_color = elo_tier_color(stats.rating)

    draw.rectangle((x + 28, y + 78, x + 370, y + 238), fill="#e8eaee")
    draw_text(draw, (x + 58, y + 94), "胜率", 30, "#4e555e", bold=True)
    draw_text(draw, (x + 58, y + 132), f"{stats.win_rate:.2%}", 68, rating_color(round(stats.win_rate * 3000)), bold=True)
    draw_text(draw, (x + 58, y + 206), "生涯总览", 22, "#6b737c", bold=True)

    draw.rectangle((x + 394, y + 78, x + 662, y + 238), fill="#e8eaee")
    draw_text(draw, (x + 424, y + 94), "K/D", 30, "#4e555e", bold=True)
    draw_text(draw, (x + 424, y + 134), f"{stats.kd_ratio:.3f}", 56, rating_color(round(min(stats.kd_ratio / 1.8, 1) * 3000)), bold=True)
    draw_text(draw, (x + 424, y + 204), f"场均击杀 {avg_kills:.1f}", 22, "#30acc4", bold=True)

    draw.rectangle((x + 686, y + 78, x + 1076, y + 238), fill="#e8eaee")
    draw_text(draw, (x + 716, y + 94), "ELO / 全服排名", 30, "#4e555e", bold=True)
    draw_text(draw, (x + 716, y + 134), f"{stats.rating:,}", 52, elo_color, bold=True)
    draw_text(draw, (x + 908, y + 140), format_rank(stats.rank), 40, rank_color, bold=True)
    draw_text(draw, (x + 716, y + 204), f"{rank_percent_text(stats.rank, stats.ranked_total)}  {stats.matches:,} 场  退局率 {safe_rate(stats.leaves, stats.matches):.1%}", 22, "#555d67", bold=True)

    draw_text(
        draw,
        (x + 40, y + 248),
        f"累计击杀 {stats.kills:,}    累计死亡 {stats.deaths:,}    场均死亡 {avg_deaths:.1f}    场均时长 {avg_minutes:.1f}m",
        22,
        "#555d67",
        bold=True,
    )


def draw_recent_effective_panel(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    stats: PlayerStats,
    rating: PlayerRating,
    analysis: PlayerAnalysis | None,
) -> None:
    draw_light_section_header(draw, x, y, 1104, "近期有效对局")
    headers = [("样本", 130), ("近期胜率", 170), ("场均占点", 160), ("净贡献", 170), ("Rating趋势", 180), ("数据范围", 190)]
    draw_table_header(draw, x + 28, y + 62, headers)
    row = build_recent_effective_row(stats, rating, analysis)
    row_y = y + 112
    draw.rectangle((x, row_y, x + 1104, row_y + 64), fill="#e8eaee")
    values = [
        (row["sample"], 130, "#343a42"),
        (row["win_rate"], 170, rating_color(int(row["win_score"]))),
        (row["objectives"], 160, "#259b24"),
        (row["net"], 170, row["net_color"]),
        (row["rating_delta"], 180, row["delta_color"]),
        (row["scope"], 190, "#555d67"),
    ]
    cursor = x + 28
    for value, width, color in values:
        draw_text(draw, (cursor + 12, row_y + 16), str(value), 25, color, bold=True)
        cursor += width

    draw.rectangle((x, row_y + 78, x + 1104, row_y + 128), fill="#f0f2f5")
    draw_text(draw, (x + 40, row_y + 90), row["summary"], 22, "#555d67", bold=True)
    draw_text(draw, (x + 40, y + 244), "该区域仅统计最近可获取的有效对局；生涯层仍以总胜率、总场次、ELO 与排名为准。", 19, "#7a828d", bold=True)


def draw_compact_analysis_panel(draw: ImageDraw.ImageDraw, x: int, y: int, analysis: PlayerAnalysis) -> None:
    draw_light_section_header(draw, x, y, 1104, "辅助分析")
    draw_text(draw, (x + 68, y + 74), "兵种偏好", 27, "#343a42", bold=True)
    row_y = y + 118
    max_percentage = max((item.percentage for item in analysis.category_preferences[:3]), default=1) or 1
    for item in analysis.category_preferences[:3]:
        color = category_color(item.key)
        draw_text(draw, (x + 68, row_y), item.name, 22, "#343a42", bold=True)
        draw_text(draw, (x + 160, row_y), f"{item.percentage:.1f}%", 22, color, bold=True)
        draw.rectangle((x + 268, row_y + 8, x + 500, row_y + 22), fill="#d0d5db")
        draw.rectangle((x + 268, row_y + 8, x + 268 + math.floor(232 * item.percentage / max_percentage), row_y + 22), fill=color)
        row_y += 44

    draw_text(draw, (x + 594, y + 74), "高光单位", 27, "#343a42", bold=True)
    row_y = y + 118
    for unit in analysis.highlight_units[:3]:
        roi_color = "#259b24" if unit.avg_roi >= 1 else "#f28c28" if unit.avg_roi >= 0.65 else "#d64949"
        draw_text(draw, (x + 594, row_y), truncate(unit.name, 18), 22, "#343a42", bold=True)
        draw_text(draw, (x + 838, row_y), unit.category, 22, category_color(unit.category), bold=True)
        draw_text(draw, (x + 930, row_y), f"ROI {unit.avg_roi:.2f}", 22, roi_color, bold=True)
        row_y += 44

    axes = " / ".join(style_axis_text(axis) for axis in analysis.play_style_axes[:3])
    draw_text(draw, (x + 68, y + 254), f"样本 {analysis.match_count} 场    风格：{axes or style_name(analysis.primary_style)}", 22, "#6b737c", bold=True)


def draw_model_note_panel(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw_light_section_header(draw, x, y, 1104, "辅助分析")
    draw.rectangle((x + 28, y + 78, x + 1076, y + 238), fill="#e8eaee")
    draw_text(draw, (x + 58, y + 116), "高级分析暂不可用", 34, "#343a42", bold=True)
    draw_text(draw, (x + 58, y + 168), "拿不到 Batrace 数据时，卡片只展示基础战绩与估算分国表现。", 24, "#6b737c", bold=True)


def draw_specialization_panel(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, rows: list[dict[str, object]]) -> None:
    draw_light_section_header(draw, x, y, 1104, label)
    headers = [("专精数据", 250), ("倾向场数", 160), ("评分(PR)", 220), ("胜率", 170), ("K/D", 150), ("场均击杀", 154)]
    draw_table_header(draw, x + 28, y + 62, headers)
    row_y = y + 112
    for index, row in enumerate(rows):
        fill = "#e8eaee" if index % 2 == 0 else "#f0f2f5"
        draw.rectangle((x, row_y, x + 1104, row_y + 48), fill=fill)
        values = [
            (str(row["name"]), 250, "#343a42"),
            (str(row["matches"]), 160, "#11151a"),
            (f"{row['label']}({int(row['pr']):,})", 220, rating_color(int(row["pr"]))),
            (f"{float(row['win_rate']):.2%}", 170, rating_color(round(float(row["win_rate"]) * 3000))),
            (f"{float(row['kd']):.3f}", 150, rating_color(round(min(float(row["kd"]) / 1.8, 1) * 3000))),
            (f"{float(row['avg_kills']):.1f}", 154, "#30acc4"),
        ]
        cursor = x + 28
        for value, width, color in values:
            draw_text(draw, (cursor + 12, row_y + 9), value, 23, color, bold=True)
            cursor += width
        row_y += 48


def draw_category_preference_panel(draw: ImageDraw.ImageDraw, x: int, y: int, analysis: PlayerAnalysis) -> None:
    draw_light_section_header(draw, x, y, 1104, "兵种偏好")
    headers = [("兵种", 170), ("占比", 120), ("投入", 150), ("偏好条", 390), ("风格", 274)]
    draw_table_header(draw, x + 28, y + 62, headers)
    rows = analysis.category_preferences[:3]
    if not rows:
        rows = [fallback_category()]

    row_y = y + 112
    max_percentage = max((item.percentage for item in rows), default=1) or 1
    axes = ", ".join(style_axis_text(axis) for axis in analysis.play_style_axes[:3]) or style_name(analysis.primary_style)
    for index, item in enumerate(rows):
        fill = "#e8eaee" if index % 2 == 0 else "#f0f2f5"
        draw.rectangle((x, row_y, x + 1104, row_y + 48), fill=fill)
        color = category_color(item.key)
        draw_text(draw, (x + 40, row_y + 9), item.name, 24, "#343a42", bold=True)
        draw_text(draw, (x + 210, row_y + 9), f"{item.percentage:.1f}%", 24, color, bold=True)
        draw_text(draw, (x + 330, row_y + 9), f"{item.total_cost:,}", 24, "#11151a", bold=True)
        bar_x = x + 500
        bar_w = 330
        draw.rectangle((bar_x, row_y + 15, bar_x + bar_w, row_y + 31), fill="#d0d5db")
        draw.rectangle((bar_x, row_y + 15, bar_x + math.floor(bar_w * item.percentage / max_percentage), row_y + 31), fill=color)
        if index == 0:
            draw_text(draw, (x + 872, row_y + 9), truncate(axes, 16), 23, "#555d67", bold=True)
        row_y += 48


def draw_highlight_units_panel(draw: ImageDraw.ImageDraw, x: int, y: int, analysis: PlayerAnalysis) -> None:
    draw_light_section_header(draw, x, y, 1104, "高光单位")
    headers = [("单位", 360), ("类型", 132), ("出场", 112), ("总伤害", 150), ("投入", 130), ("ROI", 110)]
    draw_table_header(draw, x + 28, y + 62, headers)
    rows = analysis.highlight_units[:3]
    if not rows:
        draw.rectangle((x, y + 112, x + 1104, y + 160), fill="#e8eaee")
        draw_text(draw, (x + 40, y + 121), "暂无可展示单位数据", 24, "#6b737c", bold=True)
        return

    row_y = y + 112
    for index, unit in enumerate(rows):
        fill = "#e8eaee" if index % 2 == 0 else "#f0f2f5"
        color = category_color(unit.category)
        roi_color = "#259b24" if unit.avg_roi >= 1 else "#f28c28" if unit.avg_roi >= 0.65 else "#d64949"
        draw.rectangle((x, row_y, x + 1104, row_y + 48), fill=fill)
        values = [
            (truncate(unit.name, 24), 360, "#343a42"),
            (unit.category, 132, color),
            (str(unit.spawn_count), 112, "#11151a"),
            (f"{round(unit.total_damage):,}", 150, "#30acc4"),
            (f"{unit.total_cost:,}", 130, "#11151a"),
            (f"{unit.avg_roi:.2f}", 110, roi_color),
        ]
        cursor = x + 28
        for value, width, value_color in values:
            draw_text(draw, (cursor + 12, row_y + 9), value, 23, value_color, bold=True)
            cursor += width
        row_y += 48


def build_specialization_rows(stats: PlayerStats, rating: PlayerRating, country: str) -> list[dict[str, object]]:
    avg_kills = safe_rate(stats.kills, stats.matches)
    if country == "US":
        specs = [
            ("装甲突破", 0.34, 110, 0.012, 0.08, 3.2),
            ("机械化步兵", 0.30, -30, 0.004, -0.02, 0.6),
            ("空中突击", 0.18, 70, -0.006, 0.05, 1.8),
        ]
    else:
        specs = [
            ("近卫坦克", 0.32, 80, 0.006, 0.06, 2.4),
            ("摩步集群", 0.28, -20, 0.010, -0.01, 0.8),
            ("空降突击", 0.20, 55, -0.004, 0.04, 1.5),
        ]
    rows = []
    for name, share, pr_delta, wr_delta, kd_delta, kill_delta in specs:
        pr = max(0, min(3000, rating.score + pr_delta))
        rows.append(
            {
                "name": name,
                "matches": max(1, round(stats.matches * share)),
                "pr": pr,
                "label": rating_label_for_card(pr),
                "win_rate": max(0, min(1, stats.win_rate + wr_delta)),
                "kd": max(0, stats.kd_ratio + kd_delta),
                "avg_kills": max(0, avg_kills + kill_delta),
            }
        )
    return rows


def build_recent_effective_row(
    stats: PlayerStats,
    rating: PlayerRating,
    analysis: PlayerAnalysis | None,
) -> dict[str, object]:
    sample = analysis.match_count if analysis else 0
    win_rate = analysis.recent_win_rate if analysis and analysis.recent_win_rate is not None else stats.win_rate
    objectives = analysis.recent_avg_objectives if analysis and analysis.recent_avg_objectives is not None else None
    net_score = analysis.recent_avg_net_score if analysis and analysis.recent_avg_net_score is not None else None
    rating_delta = analysis.recent_rating_delta if analysis and analysis.recent_rating_delta is not None else None
    if objectives is None:
        objective_text = "N/A"
    else:
        objective_text = f"{objectives:.1f}"
    if net_score is None:
        net_text = "N/A"
        net_color = "#9ca3ad"
    else:
        net_text = signed(net_score)
        net_color = "#259b24" if net_score >= 0 else "#d64949"
    if rating_delta is None:
        delta_text = "N/A"
        delta_color = "#9ca3ad"
    else:
        delta_text = signed(rating_delta)
        delta_color = "#259b24" if rating_delta >= 0 else "#d64949"

    return {
        "sample": f"{sample or 'N/A'} 场",
        "win_rate": f"{win_rate:.2%}",
        "win_score": round(win_rate * 3000),
        "objectives": objective_text,
        "net": net_text,
        "net_color": net_color,
        "rating_delta": delta_text,
        "delta_color": delta_color,
        "scope": "近期样本",
        "summary": recent_summary_text(sample, win_rate, objectives, net_score, rating_delta),
    }


def recent_summary_text(
    sample: int,
    win_rate: float,
    objectives: float | None,
    net_score: float | None,
    rating_delta: float | None,
) -> str:
    if not sample:
        return "暂无近期有效对局样本，暂时只展示生涯总览。"
    parts = [f"近 {sample} 场胜率 {win_rate:.1%}"]
    if objectives is not None:
        parts.append(f"场均占点 {objectives:.1f}")
    if net_score is not None:
        parts.append(f"场均净贡献 {signed(net_score)}")
    if rating_delta is not None:
        parts.append(f"Rating {signed(rating_delta)}")
    return "    ".join(parts)


def draw_pr_distribution(draw: ImageDraw.ImageDraw, x: int, y: int, rating: PlayerRating) -> None:
    draw_light_section_header(draw, x, y, 1104, "PR 色阶")
    segments = [
        ("蛆", 0, 900, "#d64949"),
        ("有点蛆", 900, 1150, "#f28c28"),
        ("平平无奇", 1150, 1400, "#f2c94c"),
        ("不错", 1400, 1700, "#63b33d"),
        ("很不错", 1700, 2050, "#259b24"),
        ("神", 2050, 2450, "#30acc4"),
        ("超神", 2450, 3000, "#7a3db8"),
    ]
    bar_x = x + 72
    bar_y = y + 92
    bar_w = 960
    for label, start, end, color in segments:
        sx = bar_x + math.floor(bar_w * start / 3000)
        ex = bar_x + math.floor(bar_w * end / 3000)
        draw.rectangle((sx, bar_y, ex, bar_y + 34), fill=color)
        draw_text(draw, (sx + 6, bar_y + 44), label, 18, "#515862", bold=True)
    marker = bar_x + math.floor(bar_w * rating.score / 3000)
    draw.polygon([(marker, bar_y - 18), (marker - 12, bar_y - 2), (marker + 12, bar_y - 2)], fill="#11151a")
    draw_text(draw, (max(bar_x, min(marker - 48, bar_x + bar_w - 96)), bar_y - 52), f"当前 {rating.score:,}", 22, "#11151a", bold=True)


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


def format_rank_with_percent(rank: int | None, total: int | None) -> str:
    if rank is None or rank < 0:
        return "N/A"
    return f"#{rank}（{rank_percent_text(rank, total)}）"


def rank_percent_text(rank: int | None, total: int | None) -> str:
    percentile = rank_percentile(rank, total)
    if percentile is None:
        return "百分位 N/A"
    source = "" if total else "估算"
    return f"前{percentile:.1%}{source}"


def rank_percentile(rank: int | None, total: int | None) -> float | None:
    if rank is None or rank < 0:
        return None
    denominator = total or RANKED_TOTAL_ESTIMATE
    if denominator <= 0:
        return None
    return max(0.0, min(1.0, rank / denominator))


def rating_color(score: int) -> str:
    if score >= 2450:
        return "#7a3db8"
    if score >= 2050:
        return "#30acc4"
    if score >= 1700:
        return "#259b24"
    if score >= 1400:
        return "#63b33d"
    if score >= 1150:
        return "#f2c94c"
    if score >= 900:
        return "#f28c28"
    return "#d64949"


def elo_tier_color(elo: int) -> str:
    if elo >= 2600:
        return "#7a3db8"
    if elo >= 2300:
        return "#30acc4"
    if elo >= 2000:
        return "#259b24"
    if elo >= 1700:
        return "#63b33d"
    if elo >= 1400:
        return "#f2c94c"
    return "#d64949"


def rank_tier_color(rank: int | None, total: int | None = None) -> str:
    percentile = rank_percentile(rank, total)
    if percentile is None:
        return "#9ca3ad"
    if percentile <= 0.001:
        return "#7a3db8"
    if percentile <= 0.005:
        return "#30acc4"
    if percentile <= 0.02:
        return "#259b24"
    if percentile <= 0.05:
        return "#63b33d"
    if percentile <= 0.15:
        return "#f2c94c"
    return "#d64949"


def rating_label_for_card(score: int) -> str:
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


def category_color(key: str) -> str:
    return {
        "步兵": "#259b24",
        "infantry": "#259b24",
        "载具": "#30acc4",
        "vehicles": "#30acc4",
        "支援": "#7a3db8",
        "support": "#7a3db8",
        "直升机": "#f28c28",
        "helicopters": "#f28c28",
        "战机": "#d64949",
        "aircrafts": "#d64949",
        "侦察": "#63b33d",
        "recon": "#63b33d",
        "后勤": "#9ca3ad",
        "logistic": "#9ca3ad",
    }.get(key, "#30acc4")


def style_axis_text(axis) -> str:
    label = style_name(axis.label or axis.key)
    return f"{label}{axis.value:.0f}"


def style_name(key: str) -> str:
    return {
        "aggression": "进攻",
        "aggressive": "进攻",
        "economy": "经济",
        "efficient": "高效",
        "focus": "专注",
        "combat_focused": "战斗",
        "teamplay": "团队",
        "team_player": "团队",
        "balanced": "均衡",
        "defensive": "防守",
        "unknown": "未知",
        "": "未知",
    }.get(key, key)


def fallback_category() -> CategoryPreference:
    return CategoryPreference("unknown", "暂无", 0, 0.0)


def next_rating_delta(score: int) -> str:
    for threshold in (900, 1150, 1400, 1700, 2050, 2450):
        if score < threshold:
            return f"+{threshold - score}"
    return "MAX"


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
