"""Generate the HozoorYar brand logo (royal purple + gold pin/clock) with Pillow.

Outputs:
    brand/logo.png            1024x1024 rounded app icon
    brand/icon-192.png        192x192
    brand/icon-512.png        512x512
    brand/icon-512-maskable.png 512x512 maskable (full-bleed, emblem in safe zone)
    brand/apple-touch-icon.png 180x180 full-bleed
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SS = 4  # supersampling factor for the shape layer

PURPLE_DARK = (0x3B, 0x07, 0x64)
PURPLE_MID = (0x4C, 0x1D, 0x95)
PURPLE = (0x7E, 0x22, 0xCE)
GOLD = (0xFB, 0xBF, 0x24)
GOLD_DEEP = (0xD4, 0xA0, 0x17)
WHITE = (255, 255, 255)


def diagonal_gradient(size: int) -> Image.Image:
    """Smooth dark-purple -> purple diagonal gradient (built small, upscaled)."""
    small = 256
    img = Image.new("RGB", (small, small))
    px = img.load()
    for y in range(small):
        for x in range(small):
            t = (x + y) / (2 * (small - 1))
            # ease the transition a little
            t = t * t * (3 - 2 * t)
            px[x, y] = (
                int(PURPLE_DARK[0] + (PURPLE[0] - PURPLE_DARK[0]) * t),
                int(PURPLE_DARK[1] + (PURPLE[1] - PURPLE_DARK[1]) * t),
                int(PURPLE_DARK[2] + (PURPLE[2] - PURPLE_DARK[2]) * t),
            )
    return img.resize((size, size), Image.BICUBIC)


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def draw_shapes(size: int) -> Image.Image:
    """Draw the gold pin + clock emblem on a transparent RGBA layer (supersampled)."""
    s = size * SS
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    cx = s / 2
    cy = s * 0.435
    r = s * 0.245

    # --- pin tail (triangle, union with the head in the same gold) ---
    tail = [
        (cx - r * 0.76, cy + r * 0.55),
        (cx + r * 0.76, cy + r * 0.55),
        (cx, cy + r * 1.82),
    ]
    d.polygon(tail, fill=GOLD)

    # --- pin head (circle) ---
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)

    # --- white clock face ---
    face_r = r * 0.665
    d.ellipse([cx - face_r, cy - face_r, cx + face_r, cy + face_r], fill=WHITE)

    # --- hour ticks (12, 3, 6, 9) ---
    tick_r_out = face_r * 0.92
    tick_r_in = face_r * 0.78
    tick_w = int(face_r * 0.10)
    for hour in range(12):
        import math

        ang = math.radians(hour * 30 - 90)
        x1 = cx + math.cos(ang) * tick_r_in
        y1 = cy + math.sin(ang) * tick_r_in
        x2 = cx + math.cos(ang) * tick_r_out
        y2 = cy + math.sin(ang) * tick_r_out
        color = PURPLE_MID if hour % 3 == 0 else (0xC4, 0xB5, 0xFD)
        d.line([x1, y1, x2, y2], fill=color, width=tick_w)

    # --- clock hands at 10:10 ---
    import math

    def hand(angle_deg: float, length: float, width: float) -> None:
        ang = math.radians(angle_deg - 90)
        x = cx + math.cos(ang) * length
        y = cy + math.sin(ang) * length
        d.line([cx, cy, x, y], fill=PURPLE_MID, width=int(width))
        # rounded cap
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2],
                  fill=PURPLE_MID)

    hand(-60, face_r * 0.50, face_r * 0.155)   # hour hand -> 10 o'clock
    hand(60, face_r * 0.74, face_r * 0.115)    # minute hand -> 2 o'clock

    # center dot
    dot = face_r * 0.105
    d.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=PURPLE_MID)

    # downscale for antialiasing
    return layer.resize((size, size), Image.LANCZOS)


def build_icon(size: int, *, rounded: bool, emblem_scale: float = 1.0) -> Image.Image:
    bg = diagonal_gradient(size)

    shapes = draw_shapes(size)
    if emblem_scale != 1.0:
        new = int(size * emblem_scale)
        shapes = shapes.resize((new, new), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        off = (size - new) // 2
        canvas.paste(shapes, (off, off))
        shapes = canvas

    icon = bg.convert("RGBA")
    icon.alpha_composite(shapes)

    if rounded:
        icon.putalpha(rounded_mask(size, int(size * 0.185)))
    return icon


def main() -> None:
    os.makedirs(HERE, exist_ok=True)

    build_icon(1024, rounded=True).save(os.path.join(HERE, "logo.png"))
    build_icon(512, rounded=True).save(os.path.join(HERE, "icon-512.png"))
    build_icon(192, rounded=True).save(os.path.join(HERE, "icon-192.png"))
    build_icon(180, rounded=False).save(os.path.join(HERE, "apple-touch-icon.png"))
    # maskable: full-bleed background, emblem inside the 80% safe zone
    build_icon(512, rounded=False, emblem_scale=0.78).save(
        os.path.join(HERE, "icon-512-maskable.png")
    )
    print("logo assets written to", HERE)


if __name__ == "__main__":
    main()
