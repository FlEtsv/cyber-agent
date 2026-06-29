"""Genera assets/cyberagent.ico (rayo sobre círculo cian) para el acceso directo."""
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "cyberagent.ico")


def main() -> None:
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((24, 24, 232, 232), fill=(0, 217, 255, 255))
    glyph, size = "⚡", 150  # ⚡
    font = None
    for name in ("seguiemj.ttf", "segoeui.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(name, size)
            break
        except Exception:
            continue
    if font is None:
        glyph, font = "CA", ImageFont.load_default()
    try:
        d.text((128, 122), glyph, font=font, anchor="mm", fill=(8, 12, 15, 255))
    except Exception:
        d.text((90, 70), "CA", font=ImageFont.load_default(), fill=(8, 12, 15, 255))
    img.save(OUT, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icono OK:", OUT)


if __name__ == "__main__":
    main()
