#!/usr/bin/env python
"""Porta Pros site engine — one CLI for the whole build.

Usage:
  python engine.py build            # build every site in config/sites.json -> dist/
  python engine.py serve            # serve dist/ (portal :8000 + one port per site)
  python engine.py logos            # (re)crop brand logo marks -> logo_assets/
  python engine.py audit            # SEO / AEO / GEO audit of the built sites
  python engine.py new <domain> --city "X" --st ST --area 000 [--street "..."]
                                     [--zip 00000] [--theme name] [--tagline "..."]

Add a city: `new` registers it in config/sites.json; then clone its content repo
into ./<domain>/ (content branch) and run `logos` + `build`.  See README.md.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "config")
sys.path.insert(0, ROOT)


def cmd_build(a):
    # build.py is the garage-door renderer (JSON content under content/<slug>/).
    # This used to call build_site.build() -- the porta-potty markdown renderer --
    # which rmtree'd all of dist/ and then rebuilt nothing, because no domain has
    # the <domain>/content/**/*.md layout that renderer expects.
    import build
    build.build(getattr(a, "domains", None) or None)
    print("Built -> dist/")


def cmd_serve(_a):
    import serve
    serve.main()


def cmd_logos(_a):
    import logo_prep
    logo_prep.main()


def cmd_audit(_a):
    import audit_seo
    audit_seo.main()


# garage-door taxonomy: rotating layouts + default brand tagline
LAYOUTS = ["aurora", "meridian", "cobalt", "harbor", "summit", "monarch"]
GD_TAGLINE = "Repair · Install · Service"
GD_FONTS = "Urbanist:wght@600;700;800&family=Open+Sans:wght@400;500;600"


# ---- colour helpers (WCAG-contrast-safe theme from a single brand hex) ----
def _rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(x))) for x in c)

def _mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

def _lum(c):
    f = lambda x: (x / 255) / 12.92 if x / 255 <= 0.03928 else (((x / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])

def _contrast(a, b):
    L = sorted([_lum(a), _lum(b)], reverse=True)
    return (L[0] + 0.05) / (L[1] + 0.05)

def theme_from_color(hex_color):
    """Build a contrast-safe theme dict from one brand colour (white text sits on --p)."""
    import colorsys
    p = _rgb(hex_color)
    for _ in range(16):                        # darken until white text is readable on p
        if _contrast(p, (255, 255, 255)) >= 5.0:
            break
        p = _mix(p, (0, 0, 0), 0.10)
    pd = _mix(p, (0, 0, 0), 0.30)
    h, s, v = colorsys.rgb_to_hsv(*[c / 255 for c in p])
    accent = tuple(c * 255 for c in colorsys.hsv_to_rgb((h + 0.5) % 1.0, min(1, max(.5, s)), .62))
    for _ in range(16):                        # ensure white reads on the accent too
        if _contrast(accent, (255, 255, 255)) >= 3.4:
            break
        accent = _mix(accent, (0, 0, 0), 0.08)
    return {"p": _hex(p), "pd": _hex(pd), "accent": _hex(accent), "on_accent": "#ffffff",
            "display": "Urbanist", "body": "Open Sans", "fonts": GD_FONTS}


def _slug(t):
    import re
    return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")

def _sheet_row(sheet, domain):
    """Look up a domain in the CSV sheet (Domain/Business Name/City/State/Primary Color)."""
    import csv
    if not sheet or not os.path.exists(sheet):
        return {}
    for r in csv.DictReader(open(sheet, encoding="utf-8-sig")):
        if (r.get("Domain (Purchased)") or "").strip().lower() == domain.lower():
            return r
    return {}


def cmd_new(a):
    themes_path = os.path.join(CONFIG, "themes.json")
    sites_path = os.path.join(CONFIG, "sites.json")
    themes = json.load(open(themes_path, encoding="utf-8"))
    data = json.load(open(sites_path, encoding="utf-8"))
    sites = data["sites"]
    if any(s["domain"] == a.domain for s in sites):
        print(f"! {a.domain} already registered in sites.json"); return

    # auto-fill from the domain sheet when --city/--st/--brand/--color are omitted
    default_sheet = os.path.join(os.path.dirname(ROOT), "domains.csv")
    row = _sheet_row(a.sheet or default_sheet, a.domain)
    city = a.city or (row.get("City") or "").strip()
    st = (a.st or (row.get("State") or "").strip()).upper()
    if not city or not st:
        print(f"! need --city and --st (not found for {a.domain} in the sheet)"); return
    brand = a.brand or (row.get("Business Name") or "").strip() or f"{city} Garage Door"
    color = a.color or (row.get("Primary Color") or "").strip()

    content = a.content or f"{_slug(city)}-{st.lower()}"          # e.g. mesa-az
    layout = a.layout or LAYOUTS[len(sites) % len(LAYOUTS)]
    port = a.port or (max([s.get("port", 0) for s in sites] + [8200]) + 1)
    phone = a.phone or (f"({a.area}) 000-0000" if a.area else "")

    # theme: reuse --theme, else synthesise a colour-matched one from the brand hex
    if a.theme:
        theme = a.theme
    elif color:
        theme = _slug(a.domain.rsplit(".", 1)[0])                 # e.g. mesagaragedoorco
        themes[theme] = theme_from_color(color)
        json.dump(themes, open(themes_path, "w", encoding="utf-8"), indent=2)
    else:
        theme = [k for k in themes if not k.startswith("_")][len(sites) % len([k for k in themes if not k.startswith("_")])]

    entry = {
        "domain": a.domain, "city": city, "st": st, "content": content,
        "brand": brand, "tagline": a.tagline or GD_TAGLINE,
        "area": str(a.area or ""), "street": a.street or "", "zip": a.zip or "",
        "phone": phone, "theme": theme, "layout": layout, "port": port,
    }
    sites.append(entry)
    json.dump(data, open(sites_path, "w", encoding="utf-8"), indent=2)
    print(f"Added {a.domain}")
    print(f"  brand={brand!r}  city={city}, {st}  content={content}/  theme={theme}  layout={layout}  port={port}")
    print("Next:")
    print(f"  1) put this city's JSON content in  content/{content}/  (files like {content.split('-')[0]}-home.json, -svc-, -nb-, -sub-, -top-)")
    print(f"  2) python build.py         # build every site in config/sites.json -> dist/")
    print(f"  3) python engine.py serve  # preview on http://localhost:{port}/")


def cmd_bulk(a):
    """Register every domain in the sheet into sites.json (+ colour-matched themes).
    Idempotent: skips domains already registered. Content dirs are still added later.
    Auto-assigns layout variations to ensure each site looks unique."""
    import csv
    # layouts.py's get_layout_for_site() used to be called here and its result
    # appended to config/layouts.json under a "layouts" key. That key does not
    # exist in that file -- it is a flat {name: axes} map -- so the append raised
    # KeyError on the first genuinely new domain, and had it succeeded it would
    # have written a hybrid that build.py's layouts.get(site["layout"]) name
    # lookup cannot read, silently collapsing every site to DEFAULT_LAYOUT.
    # build.py never consumes per-domain layout assignments anyway; the layout is
    # the round-robin name stored on each site below. Integration removed.

    sheet = a.sheet or os.path.join(os.path.dirname(ROOT), "domains.csv")
    if not os.path.exists(sheet):
        print(f"! sheet not found: {sheet}"); return
    themes_path = os.path.join(CONFIG, "themes.json")
    sites_path = os.path.join(CONFIG, "sites.json")
    
    themes = json.load(open(themes_path, encoding="utf-8"))
    data = json.load(open(sites_path, encoding="utf-8"))
    sites = data["sites"]
    have = {s["domain"] for s in sites}
    port = max([s.get("port", 0) for s in sites] + [8200])
    
    rows = [r for r in csv.DictReader(open(sheet, encoding="utf-8-sig"))
            if (r.get("Domain (Purchased)") or "").strip()]
    added = skipped = 0
    for r in rows:
        domain = r["Domain (Purchased)"].strip()
        if domain in have:
            skipped += 1; continue
        city = (r.get("City") or "").strip()
        st = (r.get("State") or "").strip().upper()
        if not city or not st:
            print(f"  skip (no city/st): {domain}"); skipped += 1; continue
        brand = (r.get("Business Name") or "").strip() or f"{city} Garage Door"
        color = (r.get("Primary Color") or "").strip() or "#1D4ED8"
        theme = _slug(domain.rsplit(".", 1)[0])
        if theme not in themes:
            themes[theme] = theme_from_color(color)
        port += 1
        
        # Assign unique layout variation
        site_index = len(sites)
        
        sites.append({
            "domain": domain, "city": city, "st": st,
            "content": f"{_slug(city)}-{st.lower()}", "brand": brand,
            "tagline": a.tagline or GD_TAGLINE, "area": "", "street": "", "zip": "",
            "phone": "", "theme": theme, "layout": LAYOUTS[site_index % len(LAYOUTS)],
            "port": port,
        })

        have.add(domain); added += 1
    json.dump(themes, open(themes_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(data, open(sites_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"Registered {added} new sites (skipped {skipped} already-present); total now {len(sites)}.")
    print("Each site builds once content/<city>-<st>/ exists (build.py skips sites with no content).")


def main():
    ap = argparse.ArgumentParser(description="Porta Pros site engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("domains", nargs="*",
                   help="build only these domains (default: every domain with content)")
    b.set_defaults(fn=cmd_build)
    sub.add_parser("serve").set_defaults(fn=cmd_serve)
    sub.add_parser("logos").set_defaults(fn=cmd_logos)
    sub.add_parser("audit").set_defaults(fn=cmd_audit)
    b = sub.add_parser("bulk", help="register every domain from the sheet into sites.json (+ colour themes)")
    b.add_argument("--sheet", default="")
    b.add_argument("--tagline", default="")
    b.set_defaults(fn=cmd_bulk)
    n = sub.add_parser("new", help="register a garage-door site (auto-fills city/brand/colour from the sheet)")
    n.add_argument("domain")
    n.add_argument("--city", default="")       # optional: filled from the sheet if omitted
    n.add_argument("--st", default="")          # optional: filled from the sheet if omitted
    n.add_argument("--brand", default="")       # business name (else sheet, else "<City> Garage Door")
    n.add_argument("--content", default="")     # content folder (else "<city>-<st>")
    n.add_argument("--layout", default="")      # else round-robin aurora/meridian/cobalt/harbor/summit/monarch
    n.add_argument("--color", default="")       # brand hex (else sheet Primary Color) -> colour-matched theme
    n.add_argument("--theme", default="")       # use an existing named theme instead of deriving one
    n.add_argument("--tagline", default="")     # else "Repair · Install · Service"
    n.add_argument("--phone", default="")
    n.add_argument("--area", default="")
    n.add_argument("--street", default="")
    n.add_argument("--zip", default="")
    n.add_argument("--port", type=int, default=0)
    n.add_argument("--sheet", default="")       # path to domains.csv (defaults to ../domains.csv)
    n.set_defaults(fn=cmd_new)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
