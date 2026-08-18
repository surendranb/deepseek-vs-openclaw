#!/usr/bin/env python3
"""
generate_chart.py — 🐋 vs 🦞 Star Growth Tracker

- Fetches live GitHub star metrics
- Updates data.json and stars.csv
- Generates chart.svg with weekly vertical lines
- Generates high-res 1200x630 og-image.png for LinkedIn/X rich social cards
- Updates index.html OpenGraph and Twitter metadata tags dynamically
"""

import json
import math
import os
import re
import urllib.request
from datetime import datetime, timezone, date, timedelta
from PIL import Image, ImageDraw, ImageFont

REPOS = {
    "deepseek_harness": {
        "repo": "deepseek-ai/deepseek-harness",
        "name": "deepseek-ai/deepseek-harness",
        "label": "🐋 deepseek-ai/deepseek-harness",
        "emoji": "🐋",
        "start_date": date(2026, 8, 13),
        "color": "#0284c7",
        "stroke_width": 3.5
    },
    "openclaw": {
        "repo": "openclaw/openclaw",
        "name": "openclaw/openclaw",
        "label": "🦞 openclaw/openclaw",
        "emoji": "🦞",
        "start_date": date(2025, 11, 24),
        "color": "#e11d48",
        "stroke_width": 3.0
    }
}

DATA_PATH = "data.json"
CSV_PATH = "stars.csv"
SVG_PATH = "chart.svg"
OG_IMAGE_PATH = "og-image.png"
HTML_PATH = "index.html"
HISTORY_PATH = "projection_history.json"


def fetch_stars(repo_full_name: str) -> int | None:
    """Fetch live stargazer count from GitHub REST API."""
    url = f"https://api.github.com/repos/{repo_full_name}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "WhaleVsLobster/1.0",
        "Accept": "application/vnd.github.v3+json"
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("stargazers_count")
    except Exception as e:
        print(f"[WARN] Failed to fetch stars for {repo_full_name}: {e}")
        return None


def update_data() -> dict:
    """Update data.json and stars.csv with current day's live star counts."""
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = date.today()

    for key, cfg in REPOS.items():
        stars = fetch_stars(cfg["repo"])
        if stars is None:
            continue

        cfg_data = data["repositories"][key]
        cfg_data["current_stars"] = stars

        day_num = (today - cfg["start_date"]).days + 1
        daily_list = cfg_data.get("daily_stars", [])

        while len(daily_list) < day_num:
            daily_list.append(stars)

        daily_list[day_num - 1] = stars
        cfg_data["daily_stars"] = daily_list

    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Sync stars.csv
    try:
        dsh_list = data["repositories"]["deepseek_harness"]["daily_stars"]
        claw_list = data["repositories"]["openclaw"]["daily_stars"]
        max_len = max(len(dsh_list), len(claw_list))

        with open(CSV_PATH, "w", encoding="utf-8") as f:
            f.write("day,whale_deepseek_stars,lobster_openclaw_stars\n")
            for i in range(max_len):
                dsh_val = dsh_list[i] if i < len(dsh_list) else ""
                claw_val = claw_list[i] if i < len(claw_list) else ""
                f.write(f"{i + 1},{dsh_val},{claw_val}\n")
    except Exception as e:
        print(f"[WARN] Failed to sync CSV: {e}")

    return data


def generate_og_image(data: dict) -> None:
    """Render the exact pixel-perfect snapshot card for og-image.png (1200x630)."""
    dsh = data["repositories"]["deepseek_harness"]["daily_stars"]
    claw = data["repositories"]["openclaw"]["daily_stars"]
    dsh_stars = dsh[-1]
    claw_stars = claw[-1]
    dsh_day = len(dsh)
    claw_day = len(claw)

    w, h = 1200, 630
    img = Image.new('RGBA', (w, h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_title = font_sub = font_pill = font_stars = font_small = font_emoji = None
    for p in ['/System/Library/Fonts/SFNS.ttf', '/System/Library/Fonts/HelveticaNeue.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if os.path.exists(p):
            try:
                font_title = ImageFont.truetype(p, 32)
                font_sub = ImageFont.truetype(p, 15)
                font_pill = ImageFont.truetype(p, 13)
                font_stars = ImageFont.truetype(p, 15)
                font_small = ImageFont.truetype(p, 11)
                break
            except:
                pass

    for ep in ['/System/Library/Fonts/Apple Color Emoji.ttc', '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf']:
        if os.path.exists(ep):
            try:
                font_emoji = ImageFont.truetype(ep, 64)
                break
            except:
                pass

    if not font_title:
        font_title = font_sub = font_pill = font_stars = font_small = ImageFont.load_default()

    def draw_emoji(text, x, y, target_size=28):
        if font_emoji:
            temp = Image.new('RGBA', (96, 96), (255, 255, 255, 0))
            d = ImageDraw.Draw(temp)
            try:
                d.text((10, 10), text, font=font_emoji, embedded_color=True)
                resized = temp.resize((target_size, target_size), Image.Resampling.LANCZOS)
                img.paste(resized, (int(x), int(y)), resized)
                return target_size
            except:
                pass
        return 0

    def dashed_line(draw, pts, fill, width, dash=(4, 4)):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            dx, dy = x2 - x1, y2 - y1
            length = (dx * dx + dy * dy) ** 0.5
            if length == 0:
                continue
            ux, uy = dx / length, dy / length
            pos = 0.0
            on = True
            while pos < length:
                seg = dash[0] if on else dash[1]
                end = min(pos + seg, length)
                draw.line([(x1 + ux * pos, y1 + uy * pos), (x1 + ux * end, y1 + uy * end)], fill=fill, width=width)
                pos = end
                on = not on

    # 1. Header Title & Subtitle
    draw_emoji('🐋', 48, 30, 36)
    draw.text((92, 32), 'vs', fill='#09090b', font=font_title)
    draw_emoji('🦞', 132, 30, 36)

    draw.text((48, 76), '📈 The battle is on. Bring the 🍿 · Updated hourly', fill='#71717a', font=font_sub)

    # 2. Scoreboard Pills
    # Pill 1: Whale
    p1_x, p1_y, p1_w, p1_h = 48, 112, 450, 42
    draw.rounded_rectangle([p1_x, p1_y, p1_x + p1_w, p1_y + p1_h], radius=10, fill='#fafafa', outline='#e4e4e7', width=1)
    draw.ellipse([p1_x + 14, p1_y + 16, p1_x + 24, p1_y + 26], fill='#0284c7')
    draw_emoji('🐋', p1_x + 32, p1_y + 11, 20)
    draw.text((p1_x + 58, p1_y + 13), 'deepseek-ai/deepseek-harness', fill='#09090b', font=font_pill)
    draw.line([(p1_x + 280, p1_y + 8), (p1_x + 280, p1_y + 34)], fill='#e4e4e7', width=1)
    draw.text((p1_x + 292, p1_y + 12), f'{dsh_stars:,} ★', fill='#0284c7', font=font_stars)
    draw.text((p1_x + 395, p1_y + 14), f'Day {dsh_day}', fill='#71717a', font=font_small)

    # VS
    draw.text((512, 124), 'VS', fill='#a1a1aa', font=font_pill)

    # Pill 2: Lobster
    p2_x, p2_y, p2_w, p2_h = 548, 112, 410, 42
    draw.rounded_rectangle([p2_x, p2_y, p2_x + p2_w, p2_y + p2_h], radius=10, fill='#fafafa', outline='#e4e4e7', width=1)
    draw.ellipse([p2_x + 14, p2_y + 16, p2_x + 24, p2_y + 26], fill='#e11d48')
    draw_emoji('🦞', p2_x + 32, p2_y + 11, 20)
    draw.text((p2_x + 58, p2_y + 13), 'openclaw/openclaw', fill='#09090b', font=font_pill)
    draw.line([(p2_x + 215, p2_y + 8), (p2_x + 215, p2_y + 34)], fill='#e4e4e7', width=1)
    draw.text((p2_x + 227, p2_y + 12), f'{claw_stars:,} ★', fill='#e11d48', font=font_stars)
    draw.text((p2_x + 335, p2_y + 14), f'Day {claw_day}', fill='#71717a', font=font_small)

    # 3. Chart Arena
    cx, cy, cw, ch = 65, 178, 1085, 395
    max_stars = 450000
    max_days = max(len(dsh), len(claw))

    # Horizontal Guidelines & Labels
    for stars_val in range(0, max_stars + 1, 90000):
        y = cy + ch - (stars_val / max_stars) * ch
        draw.line([(cx, y), (cx + cw, y)], fill='#f1f1f4', width=1)
        lbl = '0' if stars_val == 0 else f'{stars_val//1000}k'
        draw.text((cx - 36, y - 7), lbl, fill='#71717a', font=font_small)

    # Vertical Weekly Grid & Labels
    for w_idx in range(1, 39):
        x = cx + ((w_idx * 7 - 1) / (max_days - 1)) * cw
        draw.line([(x, cy), (x, cy + ch)], fill='#f1f1f4', width=1)
        if w_idx in [1, 4, 8, 12, 16, 20, 24, 28, 32, 38]:
            lbl = 'Day 1' if w_idx == 1 else f'W{w_idx}'
            draw.text((x - 12, cy + ch + 8), lbl, fill='#71717a', font=font_small)

    # Plot Lines
    def get_pts(series):
        pts = []
        for i, v in enumerate(series):
            x = cx + (i / (max_days - 1)) * cw
            y = cy + ch - (v / max_stars) * ch
            pts.append((x, y))
        return pts

    claw_pts = get_pts(claw)
    dsh_pts = get_pts(dsh)

    draw.line(claw_pts, fill='#e11d48', width=4)
    draw.line(dsh_pts, fill='#0284c7', width=5)

    # Endpoints with Emojis
    claw_last = claw_pts[-1]
    dsh_last = dsh_pts[-1]

    draw_emoji('🐋', dsh_last[0] + 6, dsh_last[1] - 12, 26)
    draw_emoji('🦞', claw_last[0] - 28, claw_last[1] - 24, 26)

    # Whale reference line (today's level)
    ref_y = cy + ch - (dsh[-1] / max_stars) * ch
    dashed_line(draw, [(cx, ref_y), (cx + cw, ref_y)], '#a1a1aa', 2, (4, 4))
    today_lbl = f'today · {dsh[-1]:,}★'
    lbl_w = draw.textlength(today_lbl, font=font_small)
    draw_emoji('🐋', cx + cw - 22, ref_y - 15, 12)
    draw.text((cx + cw - 22 - 12 - lbl_w - 4, ref_y - 8), today_lbl, fill='#71717a', font=font_small)

    # Projection fan: current / average / slowing pace (same math as chart.svg)
    fan = projection(dsh, claw, data["repositories"]["deepseek_harness"]["created_at"])
    best_slope, best_cross = fan["best_slope"], fan["best_cross"]
    log_a, log_b = fan["log_a"], fan["log_b"]
    exp_cross, sat_cap, sat_k, sat_cross = fan["exp_cross"], fan["sat_cap"], fan["sat_k"], fan["sat_cross"]
    cross_date = fan["cross_date"]

    def fan_pt(day_1based: int, val: float):
        x = cx + ((day_1based - 1) / (max_days - 1)) * cw
        y = cy + ch - (val / max_stars) * ch
        return (min(x, cx + cw), y)

    def draw_fan_label(x, y, text, color):
        draw.text((x, y), text, fill=color, font=font_small, anchor='mm',
                  stroke_width=3, stroke_fill=(255, 255, 255, 255))

    red_y = cy + ch - (claw_stars / max_stars) * ch
    dashed_line(draw, [fan_pt(d, dsh[-1] + best_slope * (d - len(dsh))) for d in range(len(dsh), int(math.ceil(best_cross)) + 1)], '#0ea5e9', 2, (2, 3))
    bx, by = fan_pt(int(math.ceil(best_cross)), claw_stars)
    draw.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill='#0ea5e9')
    draw_fan_label(bx, by - 8, f'current pace ≈ {cross_date(best_cross)}', '#0ea5e9')

    dashed_line(draw, [fan_pt(d, log_a + log_b * math.log(d)) for d in range(len(dsh), int(math.ceil(exp_cross)) + 1)], '#0284c7', 2, (7, 5))
    lx, ly = fan_pt(int(math.ceil(exp_cross)), claw_stars)
    draw.ellipse([lx - 4, ly - 4, lx + 4, ly + 4], fill='#0284c7')
    draw_fan_label(lx, ly - 8, f'average pace ≈ {cross_date(exp_cross)}', '#0284c7')

    sat_y = cy + ch - (sat_cap / max_stars) * ch
    dashed_line(draw, [fan_pt(d, sat_cap * (1 - math.exp(-sat_k * d))) for d in range(len(dsh), max_days + 1)], '#a1a1aa', 2, (4, 4))
    sat_lbl = f'slowing pace ≈ {cross_date(sat_cross)}' if sat_cross else f'slowing pace: plateaus ~{sat_cap // 1000}k★ — no catch-up'
    draw.text((cx + cw, sat_y - 6), sat_lbl, fill='#a1a1aa', font=font_small, anchor='rm',
              stroke_width=3, stroke_fill=(255, 255, 255, 255))

    # Watermark
    draw.text((48, 602), 'surendranb.github.io/deepseek-vs-openclaw 🍿', fill='#a1a1aa', font=font_small)

    final_img = img.convert('RGB')
    final_img.save(OG_IMAGE_PATH, 'PNG')
    print(f"[SUCCESS] Updated pixel-perfect {OG_IMAGE_PATH} (1200x630)")


def update_html_meta(data: dict) -> None:
    """Update index.html OpenGraph description & title with live hourly numbers (Option B)."""
    dsh = data["repositories"]["deepseek_harness"]["daily_stars"]
    claw = data["repositories"]["openclaw"]["daily_stars"]
    dsh_stars, claw_stars = dsh[-1], claw[-1]
    dsh_day = len(dsh)
    claw_day = len(claw)
    created = data["repositories"]["deepseek_harness"]["created_at"]

    og_title = "🐋 vs 🦞 · The Battle for GitHub's Fastest-Growing Repo"
    fan = projection(dsh, claw, created)
    og_desc = (f"OpenClaw got {claw_stars // 1000}K ★ in {round(claw_day / 30.44)} months. "
               f"DeepSeek Harness crossed {dsh_stars // 1000}K ★ in {dsh_day} days. "
               f"🐋 is projected to overtake 🦞 by {fan['cross_date'](fan['best_cross'])}. "
               f"Watch the race live 🍿")

    if not os.path.exists(HTML_PATH):
        return

    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    html = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{og_title}">', html)
    html = re.sub(r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{og_title}">', html)
    html = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{og_desc}">', html)
    html = re.sub(r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{og_desc}">', html)

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[SUCCESS] Updated {HTML_PATH} dynamic social metadata tags")


def projection(dsh: list[int], claw: list[int], created: str) -> dict:
    """Shared fan math: current pace (linear, last 2 deltas), average pace (log fit), slowing pace (saturation)."""
    days = len(dsh)
    red_target = claw[-1]

    def ls_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        return my - b * mx, b

    best_slope = (dsh[-1] - dsh[-3]) / 2.0
    best_cross = days + (red_target - dsh[-1]) / best_slope

    log_a, log_b = ls_fit([math.log(d) for d in range(2, days + 1)], dsh[1:])
    exp_cross = math.exp((red_target - log_a) / log_b)

    best_sat = None
    for cap in range(150000, 600000, 5000):
        for k in [x / 100 for x in range(3, 80)]:
            ss = sum((y - cap * (1 - math.exp(-k * d))) ** 2 for d, y in zip(range(1, days + 1), dsh))
            if best_sat is None or ss < best_sat[0]:
                best_sat = (ss, cap, k)
    _, sat_cap, sat_k = best_sat
    sat_cross = -math.log(1 - red_target / sat_cap) / sat_k if sat_cap > red_target else None

    def cross_date(cross: float) -> str:
        return (date.fromisoformat(created) + timedelta(days=round(cross))).strftime("%b %-d, %Y")

    return dict(best_slope=best_slope, best_cross=best_cross, log_a=log_a, log_b=log_b,
                exp_cross=exp_cross, sat_cap=sat_cap, sat_k=sat_k, sat_cross=sat_cross,
                cross_date=cross_date)


def build_svg(data: dict) -> None:
    """Generate high-contrast SVG chart with weekly vertical grid lines."""
    dsh = data["repositories"]["deepseek_harness"]["daily_stars"]
    claw = data["repositories"]["openclaw"]["daily_stars"]
    created = data["repositories"]["deepseek_harness"]["created_at"]

    fan = projection(dsh, claw, created)
    best_slope, best_cross = fan["best_slope"], fan["best_cross"]
    log_a, log_b = fan["log_a"], fan["log_b"]
    exp_cross, sat_cap, sat_k, sat_cross = fan["exp_cross"], fan["sat_cap"], fan["sat_k"], fan["sat_cross"]
    cross_date = fan["cross_date"]

    max_days = max(len(dsh), len(claw))
    max_stars = 450000

    width, height = 960, 500
    pad_left, pad_right, pad_top, pad_bottom = 65, 45, 55, 50
    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bottom

    def x_coord(day_idx: int) -> float:
        if max_days <= 1:
            return pad_left
        return pad_left + (day_idx / (max_days - 1)) * chart_w

    def y_coord(val: int) -> float:
        return pad_top + chart_h - (val / max_stars) * chart_h

    def points_to_path(vals: list[int]) -> str:
        pts = [f"{x_coord(i):.1f},{y_coord(v):.1f}" for i, v in enumerate(vals)]
        return "M " + " L ".join(pts)

    def day_path(func, from_day: int, to_day: int) -> str:
        pts = [f"{x_coord(d - 1):.1f},{y_coord(func(d)):.1f}" for d in range(from_day, to_day + 1)]
        return "M " + " L ".join(pts)

    days = len(dsh)
    red_target = claw[-1]

    dsh_path = points_to_path(dsh)
    claw_path = points_to_path(claw)

    dsh_path = points_to_path(dsh)
    claw_path = points_to_path(claw)

    dsh_tip_x = x_coord(len(dsh) - 1)
    dsh_tip_y = y_coord(dsh[-1])
    claw_tip_x = x_coord(len(claw) - 1)
    claw_tip_y = y_coord(claw[-1])

    y_ticks_svg = []
    for val in range(0, max_stars + 1, 90000):
        y = y_coord(val)
        lbl = "0" if val == 0 else f"{val//1000}k"
        y_ticks_svg.append(f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width - pad_right}" y2="{y:.1f}" stroke="#f4f4f5" stroke-width="1"/>')
        y_ticks_svg.append(f'<text x="{pad_left - 10}" y="{y + 4:.1f}" font-size="11.5" fill="#71717a" text-anchor="end" font-family="-apple-system, BlinkMacSystemFont, sans-serif">{lbl}</text>')

    x_ticks_svg = []
    total_weeks = max_days // 7

    for w in range(1, total_weeks + 1):
        day = w * 7
        x = x_coord(day - 1)
        x_ticks_svg.append(f'<line x1="{x:.1f}" y1="{pad_top}" x2="{x:.1f}" y2="{pad_top + chart_h}" stroke="#f4f4f5" stroke-width="1"/>')
        if w in [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, total_weeks]:
            lbl = f"W{w}"
            x_ticks_svg.append(f'<text x="{x:.1f}" y="{height - pad_bottom + 16}" font-size="11" fill="#71717a" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif">{lbl}</text>')

    x1 = x_coord(0)
    x_ticks_svg.append(f'<text x="{x1:.1f}" y="{height - pad_bottom + 16}" font-size="11" fill="#71717a" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif">Day 1</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="background:#ffffff;border:1px solid #e4e4e7;border-radius:14px;">
  <!-- Header / Scoreboard -->
  <g transform="translate({pad_left}, 28)">
    <text x="0" y="4" font-size="16" font-weight="900" fill="#09090b" font-family="-apple-system, BlinkMacSystemFont, sans-serif">🐋 vs 🦞</text>
    <text x="75" y="4" font-size="12" fill="#71717a" font-family="-apple-system, BlinkMacSystemFont, sans-serif">📈 The battle is on · Bring the 🍿</text>
    
    <g transform="translate(320, 0)">
      <circle cx="6" cy="0" r="4.5" fill="#0284c7"/>
      <text x="16" y="4" font-size="12" font-weight="700" fill="#0284c7" font-family="-apple-system, BlinkMacSystemFont, sans-serif">🐋 deepseek-ai/deepseek-harness</text>
    </g>

    <g transform="translate(600, 0)">
      <circle cx="6" cy="0" r="4.5" fill="#e11d48"/>
      <text x="16" y="4" font-size="12" font-weight="700" fill="#e11d48" font-family="-apple-system, BlinkMacSystemFont, sans-serif">🦞 openclaw/openclaw</text>
    </g>
  </g>

  <!-- Grid Lines -->
  {''.join(y_ticks_svg)}
  {''.join(x_ticks_svg)}

  <!-- Trajectory Lines -->
  <path d="{claw_path}" fill="none" stroke="#e11d48" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="{dsh_path}" fill="none" stroke="#0284c7" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>

  <!-- Live Mascot Emojis on Tips -->
  <text x="{dsh_tip_x + 6:.1f}" y="{dsh_tip_y + 6:.1f}" font-size="20">🐋</text>
  <text x="{claw_tip_x - 20:.1f}" y="{claw_tip_y - 8:.1f}" font-size="20">🦞</text>

  <!-- Whale reference line (today's level) -->
  <line x1="{pad_left}" y1="{dsh_tip_y:.1f}" x2="{width - pad_right}" y2="{dsh_tip_y:.1f}" stroke="#a1a1aa" stroke-width="1.5" stroke-dasharray="4 4"/>
  <text x="{width - pad_right}" y="{dsh_tip_y - 6:.1f}" font-size="11" fill="#71717a" text-anchor="end" font-family="-apple-system, BlinkMacSystemFont, sans-serif">🐋 today · {dsh[-1]:,}★</text>

  <!-- Projection fan: current / average / slowing pace -->
  <path d="{day_path(lambda d: dsh[-1] + best_slope * (d - days), days, int(math.ceil(best_cross)))}" fill="none" stroke="#0ea5e9" stroke-width="2" stroke-dasharray="2 3" stroke-linecap="round"/>
  <circle cx="{x_coord(int(math.ceil(best_cross)) - 1):.1f}" cy="{y_coord(red_target):.1f}" r="4" fill="#0ea5e9"/>
  <text x="{x_coord(int(math.ceil(best_cross)) - 1):.1f}" y="{y_coord(red_target) - 8:.1f}" font-size="11" font-weight="700" fill="#0ea5e9" text-anchor="middle" paint-order="stroke" stroke="#ffffff" stroke-width="3" font-family="-apple-system, BlinkMacSystemFont, sans-serif">current pace ≈ {cross_date(best_cross)}</text>

  <path d="{day_path(lambda d: log_a + log_b * math.log(d), days, int(math.ceil(exp_cross)))}" fill="none" stroke="#0284c7" stroke-width="2" stroke-dasharray="7 5" stroke-linecap="round"/>
  <circle cx="{x_coord(int(math.ceil(exp_cross)) - 1):.1f}" cy="{y_coord(red_target):.1f}" r="4" fill="#0284c7"/>
  <text x="{x_coord(int(math.ceil(exp_cross)) - 1):.1f}" y="{y_coord(red_target) - 8:.1f}" font-size="11" font-weight="700" fill="#0284c7" text-anchor="middle" paint-order="stroke" stroke="#ffffff" stroke-width="3" font-family="-apple-system, BlinkMacSystemFont, sans-serif">average pace ≈ {cross_date(exp_cross)}</text>

  <path d="{day_path(lambda d: sat_cap * (1 - math.exp(-sat_k * d)), days, max_days)}" fill="none" stroke="#a1a1aa" stroke-width="2" stroke-dasharray="4 4" stroke-linecap="round"/>
  <text x="{width - pad_right}" y="{y_coord(sat_cap) - 6:.1f}" font-size="11" font-weight="700" fill="#a1a1aa" text-anchor="end" paint-order="stroke" stroke="#ffffff" stroke-width="3" font-family="-apple-system, BlinkMacSystemFont, sans-serif">{'slowing pace ≈ %s' % cross_date(sat_cross) if sat_cross else 'slowing pace: plateaus ~%dk★ — no catch-up' % (sat_cap // 1000)}</text>

  <!-- X-Axis Label -->
  <text x="{width / 2}" y="{height - 8}" font-size="11.5" font-weight="700" fill="#71717a" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif">Weeks since Day 1 inception (each vertical line = 1 week)</text>
</svg>"""

    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"[SUCCESS] Updated {SVG_PATH}")


def update_projection_history(data: dict, fan: dict) -> None:
    """Append (run_at, projected date) per run; one point per hour, capped at 200."""
    dsh = data["repositories"]["deepseek_harness"]["daily_stars"]
    created = data["repositories"]["deepseek_harness"]["created_at"]
    projected_iso = (date.fromisoformat(created) + timedelta(days=round(fan["best_cross"]))).isoformat()
    entry = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "data_day": len(dsh),
        "projected": projected_iso,
        "cross_day": round(fan["best_cross"], 1),
    }
    history = []
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    if history and history[-1]["run_at"][:13] == entry["run_at"][:13]:
        history[-1] = entry
    else:
        history.append(entry)
    history = history[-200:]
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    print(f"[SUCCESS] Updated {HISTORY_PATH} ({len(history)} points)")


if __name__ == "__main__":
    updated_data = update_data()
    build_svg(updated_data)
    generate_og_image(updated_data)
    update_html_meta(updated_data)
    dsh = updated_data["repositories"]["deepseek_harness"]["daily_stars"]
    claw = updated_data["repositories"]["openclaw"]["daily_stars"]
    created = updated_data["repositories"]["deepseek_harness"]["created_at"]
    update_projection_history(updated_data, projection(dsh, claw, created))
