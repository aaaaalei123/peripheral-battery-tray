from __future__ import annotations

from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

_ICON_SIZE = 64
_SUPERSAMPLE = 4
_CANVAS = _ICON_SIZE * _SUPERSAMPLE

_WARN_PERCENT = 30


def _ring_colors(
    percent: int,
    sleeping: bool,
    light_theme: bool,
    *,
    low_battery_percent: int = 15,
    warn_battery_percent: int = _WARN_PERCENT,
) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    """Return (track_rgba, fill_rgba) for the ring."""
    if sleeping:
        if light_theme:
            track = (180, 180, 180, 255)
            fill = (140, 140, 140, 255)
        else:
            track = (110, 110, 110, 255)
            fill = (150, 150, 150, 255)
        return track, fill

    low = max(0, min(100, int(low_battery_percent)))
    warn = max(low + 1, min(100, int(warn_battery_percent)))
    if percent <= low:
        fill = (220, 55, 55, 255) if not light_theme else (200, 40, 40, 255)
    elif percent < warn:
        fill = (235, 190, 45, 255) if not light_theme else (210, 150, 20, 255)
    else:
        fill = (75, 200, 95, 255) if not light_theme else (35, 140, 55, 255)

    track = (60, 60, 60, 200) if not light_theme else (210, 210, 210, 255)
    return track, fill


def _text_color(sleeping: bool, light_theme: bool) -> Tuple[int, int, int, int]:
    if sleeping:
        return (160, 160, 160, 255) if not light_theme else (120, 120, 120, 255)
    return (245, 245, 245, 255) if not light_theme else (30, 30, 30, 255)


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_lightning(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    points = [
        (cx, y0),
        (x0 + (x1 - x0) // 4, y0 + (y1 - y0) // 2),
        (cx, y0 + (y1 - y0) // 2),
        (cx, y1),
        (x1 - (x1 - x0) // 4, y0 + (y1 - y0) // 3),
        (cx, y0 + (y1 - y0) // 3),
    ]
    draw.polygon(points, fill=(255, 220, 60, 255))


def render_tray_icon(
    percent: int,
    *,
    charging: bool,
    sleeping: bool,
    light_theme: bool,
    low_battery_percent: int = 15,
    warn_battery_percent: int = _WARN_PERCENT,
) -> Image.Image:
    """Render a 64×64 RGBA tray icon: ring fill, centered percent, optional charge badge."""
    pct = max(0, min(100, int(percent)))

    img = Image.new("RGBA", (_CANVAS, _CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = _CANVAS * 6 // 64
    bbox = (margin, margin, _CANVAS - margin, _CANVAS - margin)
    track_w = max(2, _CANVAS // 10)

    track_color, fill_color = _ring_colors(
        pct,
        sleeping,
        light_theme,
        low_battery_percent=low_battery_percent,
        warn_battery_percent=warn_battery_percent,
    )
    draw.arc(bbox, start=0, end=359.9, fill=track_color, width=track_w)

    if pct > 0:
        sweep = 360.0 * pct / 100.0
        draw.arc(bbox, start=-90, end=-90 + sweep, fill=fill_color, width=track_w)

    label = str(pct)
    font_size = _CANVAS * 22 // 64
    font = _load_font(font_size)
    text_color = _text_color(sleeping, light_theme)
    tw, th = draw.textbbox((0, 0), label, font=font)[2:]
    tx = (_CANVAS - tw) // 2
    ty = (_CANVAS - th) // 2 - font_size // 8
    draw.text((tx, ty), label, fill=text_color, font=font)

    if charging and not sleeping:
        pad = _CANVAS // 16
        side = _CANVAS // 5
        bolt_box = (_CANVAS - side - pad, _CANVAS - side - pad, _CANVAS - pad, _CANVAS - pad)
        _draw_lightning(draw, bolt_box)

    return img.resize((_ICON_SIZE, _ICON_SIZE), Image.Resampling.LANCZOS)
