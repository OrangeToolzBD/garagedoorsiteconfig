#!/usr/bin/env python
"""Map the pre-made brand/logos/<row#>_<business-slug>.png lockups to the
per-domain filenames build.py actually looks for, knocked out and tight-cropped.

brand/logos/ ships 200 hand-made 200x200 PNGs named by their row number in
domains.csv (e.g. "02_mesa_garage_door_co.png" == row 2 == mesagaragedoorco.com),
each with a near-white (~253-254) background baked into the pixels. build.py looks
up assets by *domain*: "<domain>-emblem.png" (header + footer) and
"<domain>-favicon.png" in that same folder. Nothing previously bridged the two, so
every built site fell back to the generated SVG door mark (ENGINE_GUIDE.md §8.1).

For each domain this writes:

  <domain>-emblem.png   knocked out, tight-cropped to the artwork, natural aspect
  <domain>-favicon.png  the same artwork centred on a square canvas
  _logo_manifest.json   {domain: {kind, w, h}} -- read by build.py

Three things matter downstream and all three come from here:

1. **Knockout.** The white background is removed on a soft alpha ramp (not a hard
   cutoff) so anti-aliased edges stay clean and the mark can sit directly on the
   dark footer without a visible white box.

2. **Tight crop.** These arrive as artwork floating in a 200x200 field of white.
   Cropping to the alpha bounding box is what lets the header size a logo by its
   real ink rather than by its padding -- otherwise every mark renders small and
   swimming in space, at a different apparent size per file.

3. **`kind`.** All 200 of these are *lockups*: the business name is drawn into the
   artwork. The header must not then print the name again beside it. Marks made by
   logo_gen.py are symbol-only and are not listed here, so build.py's default of
   "mark" (emblem + separate text) stays correct for them.

Source files are never modified.

Usage:
  python logo_prep.py [--sheet ../domains.csv] [--logos ../brand/logos]
"""
import argparse
import csv
import json
import os
import re

from PIL import Image, ImageChops

ROOT = os.path.dirname(os.path.abspath(__file__))

# alpha ramp: pixels whiter than LO start fading out; fully transparent by HI
WHITE_LO, WHITE_HI = 225, 250
MANIFEST = "_logo_manifest.json"
PAD = 0.03          # breathing room kept around the cropped artwork, as a fraction
FAVICON = 256       # square favicon canvas


def knockout(im):
    """White background -> transparent, on a soft ramp. Vectorised over channels:
    the per-pixel Python loop this replaces ran 40k iterations per file."""
    im = im.convert("RGBA")
    r, g, b, a = im.split()
    # "whiteness" is the darkest channel -- a pixel is only white if all three are
    mn = ImageChops.darker(ImageChops.darker(r, g), b)
    ramp = mn.point(lambda v: 255 if v <= WHITE_LO else
                    (0 if v >= WHITE_HI else round(255 * (1 - (v - WHITE_LO) / (WHITE_HI - WHITE_LO)))))
    im.putalpha(ImageChops.multiply(a, ramp))
    return im


def tight_crop(im):
    """Crop to the visible artwork plus a small even margin."""
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im                                   # fully transparent -- leave it alone
    im = im.crop(bbox)
    pad = round(max(im.size) * PAD)
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    out.paste(im, (pad, pad))
    return out


def square(im, size=FAVICON):
    """Centre the artwork on a transparent square. A 3.4:1 wordmark makes a poor
    favicon either way, but letterboxing it beats stretching it out of shape."""
    fit = im.copy()
    fit.thumbnail((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(fit, ((size - fit.width) // 2, (size - fit.height) // 2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=os.path.join(os.path.dirname(ROOT), "domains.csv"))
    ap.add_argument("--logos", default=os.path.join(os.path.dirname(ROOT), "brand", "logos"))
    a = ap.parse_args()

    if not os.path.exists(a.sheet):
        print(f"! sheet not found: {a.sheet}"); return
    if not os.path.isdir(a.logos):
        print(f"! logos dir not found: {a.logos}"); return

    # index existing files by their leading row number ("02_..." / "141_..._logo.png" -> 2 / 141)
    by_row = {}
    for fn in os.listdir(a.logos):
        m = re.match(r"^0*(\d+)_", fn)
        if m and fn.lower().endswith(".png"):
            by_row[int(m.group(1))] = fn

    manifest_path = os.path.join(a.logos, MANIFEST)
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            manifest = json.load(open(manifest_path, encoding="utf-8"))
        except Exception:
            manifest = {}

    rows = list(csv.DictReader(open(a.sheet, encoding="utf-8-sig")))
    mapped = skipped = 0
    for r in rows:
        domain = (r.get("Domain (Purchased)") or "").strip()
        num = (r.get("#") or "").strip()
        if not domain or not num.isdigit():
            continue
        src_fn = by_row.get(int(num))
        if not src_fn:
            skipped += 1
            continue
        art = tight_crop(knockout(Image.open(os.path.join(a.logos, src_fn))))
        art.save(os.path.join(a.logos, f"{domain}-emblem.png"))
        square(art).save(os.path.join(a.logos, f"{domain}-favicon.png"))
        # every hand-made file in this set draws the business name into the artwork
        manifest[domain] = {"kind": "lockup", "w": art.width, "h": art.height}
        mapped += 1

    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), indent=1, sort_keys=True)
    print(f"Mapped {mapped} domains to cropped, transparent emblem/favicon PNGs "
          f"({skipped} rows have no logo file yet).")
    print(f"Total source emblems available: {len(by_row)} / {len(rows)} domains.")
    print(f"Manifest -> {manifest_path} ({len(manifest)} domains)")


if __name__ == "__main__":
    main()
