#!/usr/bin/env python3
"""Loss-minimising responsive WebP versions of existing approved MADHOUSE artwork.

Always generated from original tracked PNGs; does not alter those originals,
logos or social previews. Prevents shipping enormous PNG hero files to phones.
"""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
IMAGES = {
    "hero": "JohnnyDaJoker_YouTube_Banner_2560x1440.png",
    "nfsu2": "file_000000007d00821198a25c70975fa763.png",
    "carbon": "file_0000000034dc8211871698b8baa78445.png",
}
SIZES = {"desktop": 1920, "mobile": 960}

def build():
    ASSETS.mkdir(parents=True, exist_ok=True)
    for label, name in IMAGES.items():
        source = ROOT / name
        with Image.open(source) as img:
            base = ImageOps.exif_transpose(img)
            base = base.convert("RGBA" if "A" in base.getbands() else "RGB")
            for variant, maximum in SIZES.items():
                output = ASSETS / (label + "-" + variant + ".webp")
                resized = base.copy()
                resized.thumbnail((maximum, maximum * 4), Image.Resampling.LANCZOS)
                resized.save(output, format="WEBP", quality=87, method=6)
                size = output.stat().st_size
                if size <= 0 or size >= source.stat().st_size:
                    raise RuntimeError(f"Unexpected WebP size for {output}: {size}")
                print(f"{label} {variant}: {base.width}×{base.height} → "
                      f"{resized.width}×{resized.height}, {source.stat().st_size//1024} KiB PNG"
                      f" → {size//1024} KiB WebP")
if __name__ == "__main__":
    build()
