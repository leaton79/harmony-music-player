from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFilter


ICON_SIZES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}

STAR_POSITIONS = [
    (0.18, 0.18, 0.018),
    (0.31, 0.11, 0.012),
    (0.72, 0.17, 0.014),
    (0.82, 0.28, 0.017),
    (0.15, 0.72, 0.016),
    (0.28, 0.82, 0.012),
    (0.78, 0.77, 0.015),
    (0.64, 0.84, 0.011),
    (0.12, 0.42, 0.010),
    (0.87, 0.56, 0.013),
    (0.58, 0.14, 0.009),
    (0.39, 0.76, 0.010),
]


def render_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = image.load()

    top = (6, 14, 36)
    mid = (12, 25, 58)
    bottom = (22, 48, 92)

    for y in range(size):
        t = y / max(size - 1, 1)
        if t < 0.6:
            blend = t / 0.6
            color = tuple(int(top[i] + (mid[i] - top[i]) * blend) for i in range(3))
        else:
            blend = (t - 0.6) / 0.4
            color = tuple(int(mid[i] + (bottom[i] - mid[i]) * blend) for i in range(3))

        for x in range(size):
            pixels[x, y] = (*color, 255)

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_center_x = int(size * 0.62)
    glow_center_y = int(size * 0.34)
    glow_radius = int(size * 0.20)
    glow_draw.ellipse(
        (
            glow_center_x - glow_radius,
            glow_center_y - glow_radius,
            glow_center_x + glow_radius,
            glow_center_y + glow_radius,
        ),
        fill=(173, 216, 255, 70),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(1, size // 24)))
    image = Image.alpha_composite(image, glow)

    draw = ImageDraw.Draw(image)
    for star_x, star_y, star_radius in STAR_POSITIONS:
        x = star_x * size
        y = star_y * size
        radius = max(1, int(size * star_radius))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 247, 216, 255))
        if size >= 64:
            width = max(1, size // 256)
            draw.line((x - radius * 2, y, x + radius * 2, y), fill=(255, 247, 216, 160), width=width)
            draw.line((x, y - radius * 2, x, y + radius * 2), fill=(255, 247, 216, 160), width=width)

    border = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_width = max(1, size // 32)
    border_draw.rounded_rectangle(
        (border_width // 2, border_width // 2, size - border_width // 2 - 1, size - border_width // 2 - 1),
        radius=size * 0.23,
        outline=(255, 255, 255, 38),
        width=border_width,
    )
    image = Image.alpha_composite(image, border)
    draw = ImageDraw.Draw(image)

    note_color = (248, 242, 226, 255)
    shadow_color = (7, 10, 24, 110)
    shadow_offset = max(1, size // 64)
    head_radius = size * 0.135

    shadow_center = (size * 0.43 + shadow_offset, size * 0.70 + shadow_offset)
    draw.ellipse(
        (
            shadow_center[0] - head_radius,
            shadow_center[1] - head_radius * 0.86,
            shadow_center[0] + head_radius,
            shadow_center[1] + head_radius * 0.86,
        ),
        fill=shadow_color,
    )
    draw.rounded_rectangle(
        (size * 0.49 + shadow_offset, size * 0.24 + shadow_offset, size * 0.585 + shadow_offset, size * 0.70 + shadow_offset),
        radius=size * 0.045,
        fill=shadow_color,
    )
    draw.rounded_rectangle(
        (size * 0.54 + shadow_offset, size * 0.24 + shadow_offset, size * 0.78 + shadow_offset, size * 0.33 + shadow_offset),
        radius=size * 0.04,
        fill=shadow_color,
    )
    draw.polygon(
        [
            (size * 0.75 + shadow_offset, size * 0.28 + shadow_offset),
            (size * 0.84 + shadow_offset, size * 0.37 + shadow_offset),
            (size * 0.79 + shadow_offset, size * 0.43 + shadow_offset),
            (size * 0.71 + shadow_offset, size * 0.34 + shadow_offset),
        ],
        fill=shadow_color,
    )

    note_center = (size * 0.41, size * 0.68)
    draw.ellipse(
        (
            note_center[0] - head_radius,
            note_center[1] - head_radius * 0.86,
            note_center[0] + head_radius,
            note_center[1] + head_radius * 0.86,
        ),
        fill=note_color,
    )
    draw.rounded_rectangle(
        (size * 0.47, size * 0.22, size * 0.56, size * 0.68),
        radius=size * 0.045,
        fill=note_color,
    )
    draw.rounded_rectangle(
        (size * 0.52, size * 0.22, size * 0.77, size * 0.31),
        radius=size * 0.04,
        fill=note_color,
    )
    draw.polygon(
        [
            (size * 0.74, size * 0.26),
            (size * 0.84, size * 0.35),
            (size * 0.79, size * 0.41),
            (size * 0.70, size * 0.32),
        ],
        fill=note_color,
    )

    if size >= 64:
        draw.arc(
            (size * 0.29, size * 0.57, size * 0.50, size * 0.77),
            start=210,
            end=330,
            fill=(255, 255, 255, 110),
            width=max(1, size // 80),
        )

    return image


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit("Usage: generate_app_icon.py [output-dir]")

    output_dir = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parent.parent / "Assets" / "Harmony.iconset"
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, size in ICON_SIZES.items():
        render_icon(size).save(output_dir / filename)

    icns_path = output_dir.parent / "Harmony.icns"
    largest = Image.open(output_dir / "icon_512x512@2x.png")
    largest.save(icns_path, format="ICNS", sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])


if __name__ == "__main__":
    main()
