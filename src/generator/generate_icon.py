#!/usr/bin/env python3
"""
Generate the WebTAPP Mac 1024x1024 master icon and .icns / studio_icon.png.
Combines the WebTPDF Mac outer squircle card style with the user's reference
web-window + 6 app-tiles motif (offset cyan fill, thick dark-navy rounded-cap strokes,
header divider, two window dots, and 3x2 app grid).
"""

from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw

def draw_round_line(draw: ImageDraw.ImageDraw, p1: tuple[float, float], p2: tuple[float, float], width: int, fill: tuple[int, int, int, int]) -> None:
    draw.line([p1, p2], fill=fill, width=width)
    r = width / 2.0
    for px, py in (p1, p2):
        draw.ellipse([px - r, py - r, px + r, py + r], fill=fill)

def draw_round_arc(
    draw: ImageDraw.ImageDraw,
    bbox: list[float],
    start_deg: float,
    end_deg: float,
    width: int,
    fill: tuple[int, int, int, int],
) -> None:
    """Draw a smooth thick circular arc with rounded line caps using dense circle stamping."""
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    rx = (bbox[2] - bbox[0]) / 2.0 - width / 2.0
    ry = (bbox[3] - bbox[1]) / 2.0 - width / 2.0
    r = width / 2.0

    steps = 120
    for i in range(steps + 1):
        deg = start_deg + (end_deg - start_deg) * (i / steps)
        rad = math.radians(deg)
        px = cx + rx * math.cos(rad)
        py = cy + ry * math.sin(rad)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=fill)

def render_master_icon(size: int = 1024) -> Image.Image:
    # Supersample at 2x (2048x2048) for ultra-crisp anti-aliased edges
    ss = 2
    W = size * ss
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Outer macOS squircle card (Exact WebTPDF Mac card dimensions & clean off-white canvas)
    pad = 72 * ss
    card_rect = [pad, pad, W - pad, W - pad]
    draw.rounded_rectangle(
        card_rect,
        radius=196 * ss,
        fill=(248, 250, 252, 255),
        outline=(212, 220, 230, 255),
        width=12 * ss,
    )

    # Colors from reference image
    navy = (25, 25, 64, 255)          # Deep navy ink (#191940)
    cyan_fill = (130, 236, 248, 255)  # Bright aqua/cyan (#82ECF8)
    stroke = 46 * ss                  # Bold clean stroke weight

    # 2. Offset Cyan Rounded-Square Backing (shifted down-right per reference image)
    cyan_left = 290 * ss
    cyan_top = 305 * ss
    cyan_right = 825 * ss
    cyan_bottom = 815 * ss
    cyan_radius = 90 * ss
    draw.rounded_rectangle(
        [cyan_left, cyan_top, cyan_right, cyan_bottom],
        radius=cyan_radius,
        fill=cyan_fill,
    )

    # 3. Main Browser Window Frame with Signature Top-Left & Bottom-Right Breaks
    win_left = 195 * ss
    win_top = 215 * ss
    win_right = 785 * ss
    win_bottom = 775 * ss
    win_r = 92 * ss
    half_s = stroke / 2.0

    # Inner centerline coordinates of the frame
    c_left = win_left + half_s
    c_top = win_top + half_s
    c_right = win_right - half_s
    c_bottom = win_bottom - half_s
    arc_r = win_r - half_s

    # Top-Left Corner Arc (180° -> 270°) + short top stub before the gap
    draw_round_arc(
        draw,
        [win_left, win_top, win_left + 2 * win_r, win_top + 2 * win_r],
        180,
        270,
        stroke,
        navy,
    )
    draw_round_line(draw, (c_left + arc_r, c_top), (332 * ss, c_top), stroke, navy)

    # Top Edge after the gap -> Top-Right Corner Arc (270° -> 360°)
    draw_round_line(draw, (425 * ss, c_top), (c_right - arc_r, c_top), stroke, navy)
    draw_round_arc(
        draw,
        [win_right - 2 * win_r, win_top, win_right, win_top + 2 * win_r],
        270,
        360,
        stroke,
        navy,
    )

    # Right Edge -> Bottom-Right Corner Arc (0° -> 90°) + short bottom stub after the gap
    draw_round_line(draw, (c_right, c_top + arc_r), (c_right, c_bottom - arc_r), stroke, navy)
    draw_round_arc(
        draw,
        [win_right - 2 * win_r, win_bottom - 2 * win_r, win_right, win_bottom],
        0,
        90,
        stroke,
        navy,
    )
    draw_round_line(draw, (678 * ss, c_bottom), (c_right - arc_r, c_bottom), stroke, navy)

    # Bottom Edge before the gap <- Bottom-Left Corner Arc (90° -> 180°) <- Left Edge
    draw_round_line(draw, (c_left + arc_r, c_bottom), (562 * ss, c_bottom), stroke, navy)
    draw_round_arc(
        draw,
        [win_left, win_bottom - 2 * win_r, win_left + 2 * win_r, win_bottom],
        90,
        180,
        stroke,
        navy,
    )
    draw_round_line(draw, (c_left, c_top + arc_r), (c_left, c_bottom - arc_r), stroke, navy)

    # 4. Horizontal Browser Header Bar (starts inside left edge and connects to right border)
    header_y = 382 * ss
    draw_round_line(draw, (302 * ss, header_y), (c_right, header_y), stroke, navy)

    # 5. Two Window Control Dots in Top-Right of Titlebar
    dot_r = 25 * ss
    dot_y = 308 * ss
    for dot_x in (606 * ss, 686 * ss):
        draw.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=navy)

    # 6. 3x2 Grid of App Icon Squircle Tiles Inside the Window
    tile_size = 84 * ss
    tile_radius = 26 * ss
    col_centers = [378 * ss, 496 * ss, 614 * ss]
    row_centers = [505 * ss, 622 * ss]

    for ry in row_centers:
        for cx in col_centers:
            half_t = tile_size / 2.0
            draw.rounded_rectangle(
                [cx - half_t, ry - half_t, cx + half_t, ry + half_t],
                radius=tile_radius,
                fill=navy,
            )

    return img.resize((size, size), Image.Resampling.LANCZOS)

def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent.parent
    master = render_master_icon(1024)
    out_png = base_dir / "studio_icon.png"
    master.save(out_png, "PNG")
    print(f"[+] Saved master studio_icon.png to {out_png}")

if __name__ == "__main__":
    main()
