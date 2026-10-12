#!/usr/bin/env python3
"""Stack the Marketing Tune-Up layers into site assets.

Uses only the supplied transparent layers. Characters are a same-canvas
stack (body, arm, head, eyes, mouth). The scene is scaled with nearest
neighbor so the pixels stay crisp. Requires Pillow. The site build does not.
"""
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required for this script only: pip install pillow")

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "art" / "layers"
OUT = ROOT / "assets"

# Scene is the 960x540 set. These positions are the source of the CSS
# sign box in assets/style.css (percentages of the 960x450 crop).
DAN_XY = (28, 72)
KATE_XY = (672, 72)
ON_XY = (410, 28)
CROP = (0, 0, 960, 450)  # x, y, w, h of the hero strip
SCALE = 2


def character(who):
    canvas = Image.new("RGBA", (260, 300), (0, 0, 0, 0))
    for part in ("body", "arm", "head", "eyes_open", "mouth_closed"):
        layer = Image.open(LAYERS / f"{who}_{part}.png").convert("RGBA")
        canvas.alpha_composite(layer, (0, 0))
    return canvas


def head(im, box):
    cropped = im.crop(box)
    bounds = cropped.getbbox()
    cropped = cropped.crop(bounds)
    return cropped.resize((cropped.width * 4, cropped.height * 4), Image.Resampling.NEAREST)


def main():
    bg = Image.open(LAYERS / "set2_bg_wide.png").convert("RGBA")
    desk = Image.open(LAYERS / "set2_desk_wide.png").convert("RGBA")
    on = Image.open(LAYERS / "set2_onair_on.png").convert("RGBA")
    off = Image.open(LAYERS / "set2_onair_off.png").convert("RGBA")
    dan, kate = character("dan"), character("kate")

    scene = bg.copy()
    scene.alpha_composite(dan, DAN_XY)
    scene.alpha_composite(kate, KATE_XY)
    scene.alpha_composite(desk, (0, 0))
    scene.alpha_composite(on, ON_XY)
    x, y, w, h = CROP
    hero = scene.crop((x, y, x + w, y + h)).resize((w * SCALE, h * SCALE), Image.Resampling.NEAREST)

    OUT.mkdir(exist_ok=True)
    hero.convert("RGB").save(OUT / "hero-studio.png", optimize=True)
    on.resize((on.width * SCALE, on.height * SCALE), Image.Resampling.NEAREST).save(OUT / "onair-on.png", optimize=True)
    off.resize((off.width * SCALE, off.height * SCALE), Image.Resampling.NEAREST).save(OUT / "onair-off.png", optimize=True)
    head(dan, (8, 0, 250, 188)).save(OUT / "avatar-dan.png", optimize=True)
    head(kate, (36, 12, 224, 200)).save(OUT / "avatar-kate.png", optimize=True)

    print(f"sign box: left {ON_XY[0] / w * 100:.6f}% top {(ON_XY[1] - y) / h * 100:.6f}% "
          f"width {on.width / w * 100:.6f}% height {on.height / h * 100:.6f}%")
    for name in ("hero-studio.png", "onair-on.png", "onair-off.png", "avatar-dan.png", "avatar-kate.png"):
        im = Image.open(OUT / name)
        print(f"{name} {im.size} {im.mode} {(OUT / name).stat().st_size} bytes")


if __name__ == "__main__":
    main()
