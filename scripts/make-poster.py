"""Crop the house renders to the drawing's bounding box for use as hero posters.

The generator draws on a 2400x1800 transparent canvas with wide empty margins.
The site wants the house itself, so we trim to the alpha bbox plus a small pad.
Usage: python3 scripts/make-poster.py  (reads design/assets/house, writes src/assets/house)
"""
from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "design/assets/house"
OUT = ROOT / "src/assets/house"
PAD = 24  # px of breathing room around the outline

OUT.mkdir(parents=True, exist_ok=True)
crops = {}
for name in ("house_lit", "house_dim", "house_studio"):
    im = Image.open(SRC / f"{name}.png").convert("RGBA")
    l, t, r, b = im.getchannel("A").getbbox()
    box = (max(l - PAD, 0), max(t - PAD, 0), min(r + PAD, im.width), min(b + PAD, im.height))
    im.crop(box).save(OUT / f"{name}.png", optimize=True)
    crops[name] = {"source": [im.width, im.height], "box": box}
    print(name, im.size, "->", box)

# Record the crop so hotspot anchors (in % of the full image) can be remapped later.
(OUT / "crop.json").write_text(json.dumps(crops, indent=1))
