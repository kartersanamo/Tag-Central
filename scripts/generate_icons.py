#!/usr/bin/env python3
"""Generate platform icon files from assets/logo-1024.png."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as error:
    raise SystemExit(
        "Pillow is required. Install with: pip install pillow"
    ) from error

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SOURCE = ASSETS / "logo-1024.png"
ICONSET = ASSETS / "icon.iconset"


def _load_source() -> Image.Image:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing source image: {SOURCE}")
    image = Image.open(SOURCE).convert("RGBA")
    return image


def _write_png_variants(image: Image.Image) -> None:
    sizes = (16, 32, 48, 64, 128, 256, 512)
    for size in sizes:
      resized = image.resize((size, size), Image.Resampling.LANCZOS)
      resized.save(ASSETS / f"icon-{size}.png", format="PNG")


def _write_ico(image: Image.Image) -> None:
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    frames = [image.resize(size, Image.Resampling.LANCZOS) for size in ico_sizes]
    frames[0].save(
        ASSETS / "icon.ico",
        format="ICO",
        sizes=ico_sizes,
        append_images=frames[1:],
    )


def _write_icns(image: Image.Image) -> None:
    if sys.platform != "darwin":
        print("Skipping .icns generation (requires macOS iconutil).")
        return

    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir(parents=True)

    mapping = {
        16: ["icon_16x16.png", "icon_16x16@2x.png"],
        32: ["icon_32x32.png", "icon_32x32@2x.png"],
        128: ["icon_128x128.png", "icon_128x128@2x.png"],
        256: ["icon_256x256.png", "icon_256x256@2x.png"],
        512: ["icon_512x512.png", "icon_512x512@2x.png"],
    }
    for base, names in mapping.items():
        image.resize((base, base), Image.Resampling.LANCZOS).save(
            ICONSET / names[0], format="PNG"
        )
        image.resize((base * 2, base * 2), Image.Resampling.LANCZOS).save(
            ICONSET / names[1], format="PNG"
        )

    output = ASSETS / "icon.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET), "-o", str(output)],
        check=True,
    )
    shutil.rmtree(ICONSET)
    print(f"Wrote {output}")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    image = _load_source()
    _write_png_variants(image)
    _write_ico(image)
    _write_icns(image)
    print(f"Icons generated in {ASSETS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
