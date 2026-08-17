#!/usr/bin/env python
"""Garage-door site generator.

Reads structured JSON content (title / meta / h1 / sections[{h2,body}] / faq[{q,a}] /
schema_facts) for a city and renders a polished static site. Reuses the porta-potty
design system's CSS, nav JS and icon set (imported from build_site.py) but all copy,
taxonomy, routing and schema are garage-door specific.

Page types (by filename): <city>-home / -svc- / -nb- / -sub- / -top-.
  svc  -> /services/<slug>/        (garage door repair / installation / service)
  nb   -> /service-areas/<slug>/   (neighborhoods)
  sub  -> /service-areas/<slug>/   (suburbs)
  top  -> /guides/<slug>/          (topic guides)
"""
import os, re, json, html, shutil
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "config")
CONTENT = os.path.join(ROOT, "content")
DIST = os.path.join(ROOT, "dist")
LOGOS = os.path.join(os.path.dirname(ROOT), "brand", "logos")   # per-domain brand logos (logo_gen.py)
BUILD_DATE = date.today().isoformat()

# Reuse the niche-agnostic design system (CSS template, theme wrapper, mobile nav JS, icons).
from build_site import CSS_TMPL, NAVJS, css, icon  # noqa: E402

DEFAULT_LAYOUT = {"hero": "banner", "nav": "left", "shape": "round", "bands": "alt",
                  "footer": "dark", "cards": "classic", "feats": "tiles", "steps": "cards"}

# garage-door service catalogue for the homepage grid + footer (icon, title, blurb, page-slug or None)
SERVICE_TILES = [
    ("shield", "Garage Door Repair", "Off-track doors, snapped cables, bent panels and grinding openers — diagnosed and fixed.", "garage-door-repair"),
    ("calendar", "New Door Installation", "Insulated steel and composite doors sized to your opening and the local heat load.", "garage-door-installation"),
    ("check", "Service &amp; Tune-Ups", "Spring tension, roller and track service that keeps an older door running quiet.", "garage-door-service"),
    ("clock", "Spring Replacement", "Torsion and extension springs replaced safely — the job you should never DIY.", None),
    ("sparkle", "Opener Repair", "Chain, belt and screw-drive openers, safety sensors and rolling-code remotes.", None),
    ("arrow", "Off-Track &amp; Cable", "Doors jumped off the track or with frayed cables re-set and re-tensioned.", None),
]

# license-free garage-door photos (Pexels), pooled in assets_shared/photos and copied per site
# -- last-resort fallback only; brand/photos/ (below) is the real photo source now.
PHOTO_POOL = [f"gd-{i}.jpg" for i in range(1, 10)]
HERO_IMG = "gd-4.jpg"
CARD_IMGS = ["gd-2.jpg", "gd-3.jpg", "gd-5.jpg", "gd-6.jpg", "gd-7.jpg", "gd-9.jpg"]
INNER_IMGS = ["gd-1.jpg", "gd-8.jpg", "gd-2.jpg", "gd-5.jpg", "gd-6.jpg"]

def _stable_idx(s, n):
    return (sum(ord(c) for c in s) % n) if n else 0

# ---------------------------------------------------------------- brand/photos
# 30 city hero shots ("<city>_garage_door.webp") + 4 per-service category pools
# (30 photos each) + 5 per-guide-topic pools (~10 photos each). Real, on-topic
# photography for every one of the 1000 registered domains -- not just the 10
# that currently build. assets_shared/photos/gd-*.jpg is now only a fallback for
# the rare gap (e.g. a city with no hero shot).
BRAND_PHOTOS = os.path.join(os.path.dirname(ROOT), "brand", "photos")

def _brand_list(subdir=""):
    d = os.path.join(BRAND_PHOTOS, subdir)
    try:
        return sorted(f for f in os.listdir(d) if f.lower().endswith(".webp"))
    except FileNotFoundError:
        return []

# city hero photos, keyed by city slug (filenames are mostly "<slug>_garage_door.webp",
# with a couple of one-off variants -- "dallas_door.webp", "wheaton_garage_doo.webp").
_CITY_HERO = {}
for _fn in _brand_list():
    _base = re.sub(r"_garage_door$|_garage_doo$|_door$|_doo$", "", os.path.splitext(_fn)[0])
    _CITY_HERO[_base] = _fn

SVC_PHOTO_DIRS = {
    "garage-door-repair": "GD REPAIR",
    "garage-door-installation": "GD INSTALLATION",
    "garage-door-service": "GD SERVICE",
}
GENERAL_PHOTO_DIRS = ["GD REPAIR", "GD INSTALLATION", "GD SERVICE", "GD MAINTENNANCE"]  # sic: source folder is misspelled
GUIDE_PHOTO_DIRS = {
    "why-a-door-goes-off-track": "Door Goes Off Track",
    "doors-on-houses-built-before-insulation-rules": "Doors on Houses Built Before Insulation Rules",
    "noises-that-mean-something": "Noises",
    "what-an-older-door-is-worth-fixing": "Older Door Worth Fixing",
    "when-a-spring-goes-in-cold-weather": "Spring Goes Cold Weather",
}

def _guide_dir_for(slug):
    """Exact match against the 5 known guide topics; best word-overlap otherwise
    (so a guide topic outside today's fixed taxonomy still gets a themed photo)."""
    if slug in GUIDE_PHOTO_DIRS:
        return GUIDE_PHOTO_DIRS[slug]
    words = set((slug or "").split("-"))
    best, best_score = None, 0
    for gslug, dirname in GUIDE_PHOTO_DIRS.items():
        score = len(words & set(gslug.split("-")))
        if score > best_score:
            best, best_score = dirname, score
    return best

def select_photos(t, pages, photos_dir):
    """Choose brand/photos/ images for this site's hero + service tiles + every
    inner page, copy the chosen files into <site>/assets/photos/, and return
    (hero_filename, card_imgs[6], inner_imgs{url: filename}) for the renderers.
    Falls back to assets_shared/photos/gd-*.jpg wherever brand/photos has no match."""
    to_copy = {}  # dest filename -> source abs path
    fallback_pool = os.path.join(ROOT, "assets_shared", "photos")

    hero_src = _CITY_HERO.get(slugify(t["city"]))
    if hero_src:
        hero_fn = "hero.webp"
        to_copy[hero_fn] = os.path.join(BRAND_PHOTOS, hero_src)
    else:
        hero_fn = HERO_IMG
        to_copy[hero_fn] = os.path.join(fallback_pool, HERO_IMG)

    card_imgs = []
    for i, (_, title, _, slug) in enumerate(SERVICE_TILES):
        dirname = SVC_PHOTO_DIRS.get(slug) or GENERAL_PHOTO_DIRS[i % len(GENERAL_PHOTO_DIRS)]
        files = _brand_list(dirname)
        if files:
            fn = files[_stable_idx(t["domain"] + title, len(files))]
            dest = f"svc-{i}.webp"
            to_copy[dest] = os.path.join(BRAND_PHOTOS, dirname, fn)
        else:
            dest = CARD_IMGS[i % len(CARD_IMGS)]
            to_copy[dest] = os.path.join(fallback_pool, dest)
        card_imgs.append(dest)

    inner_imgs = {}
    for url, p in pages.items():
        if p["cat"] == "home":
            continue
        dirname = None
        if p["cat"] == "service":
            dirname = SVC_PHOTO_DIRS.get(p["slug"])
        elif p["cat"] == "guide":
            dirname = _guide_dir_for(p["slug"])
        if not dirname:
            dirname = GENERAL_PHOTO_DIRS[_stable_idx(p["slug"] or url, len(GENERAL_PHOTO_DIRS))]
        files = _brand_list(dirname)
        if files:
            fn = files[_stable_idx(t["domain"] + (p["slug"] or url), len(files))]
            safe = re.sub(r"[^a-z0-9]+", "-", (p["slug"] or "page").lower()).strip("-")
            dest = f"inner-{safe}.webp"
            to_copy[dest] = os.path.join(BRAND_PHOTOS, dirname, fn)
        else:
            dest = INNER_IMGS[_stable_idx(p["slug"] or url, len(INNER_IMGS))]
            to_copy[dest] = os.path.join(fallback_pool, dest)
        inner_imgs[url] = dest

    for dest, src in to_copy.items():
        try:
            shutil.copy(src, os.path.join(photos_dir, dest))
        except FileNotFoundError:
            pass

    return hero_fn, card_imgs, inner_imgs

# garage-door-specific CSS (appended after the shared design system; leaves porta-potty untouched)
GD_CSS = """
/* ===== garage-door overrides ===== */
/* What We Do — image-overlay service cards with an icon chip */
.svc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.svc-card{position:relative;min-height:322px;border-radius:var(--radius);overflow:hidden;display:flex;align-items:flex-end;box-shadow:var(--shadow);text-decoration:none;isolation:isolate;transition:transform .2s,box-shadow .2s}
.svc-card img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:-2;transition:transform .5s ease}
.svc-card::after{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,rgba(12,17,24,0) 28%,rgba(12,17,24,.55) 62%,rgba(12,17,24,.93) 100%)}
.svc-card:hover{transform:translateY(-4px);box-shadow:var(--shadow-lg)}
.svc-card:hover img{transform:scale(1.07)}
.svc-card__ic{position:absolute;top:16px;left:16px;width:46px;height:46px;border-radius:13px;background:var(--accent);color:var(--on-accent);display:flex;align-items:center;justify-content:center;box-shadow:0 6px 16px rgba(0,0,0,.28)}
.svc-card__ic svg{width:24px;height:24px}
.svc-card__b{position:relative;padding:22px 22px 24px}
.svc-card__b h3{margin:0 0 6px;font-size:1.24rem;color:#fff;font-family:var(--disp)}
.svc-card__b p{margin:0 0 12px;color:rgba(255,255,255,.87);font-size:.93rem;line-height:1.5}
.svc-card__b .more{display:inline-flex;align-items:center;gap:7px;font-family:var(--disp);font-weight:700;font-size:.9rem;color:#fff}
.svc-card__b .more svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;transition:transform .2s}
.svc-card:hover .more svg{transform:translateX(4px)}
@media(max-width:900px){.svc-grid{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.svc-grid{grid-template-columns:1fr}.svc-card{min-height:250px}}

/* "View all areas" pill — inline arrow icon instead of literal text */
.areas__all{display:inline-flex;align-items:center;gap:7px}
.areas__all svg{width:16px;height:16px}
.areas__all:hover svg{transform:translateX(3px);transition:transform .2s}

/* Footer — CTA strip + columns + trust row + legal */
.gfooter{background:#0e141b;color:#aeb9c5;margin-top:0}
.gf-cta{background:linear-gradient(135deg,var(--p),var(--pd))}
.gf-cta__in{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;padding:34px 0}
.gf-cta h3{color:#fff;margin:0;font-size:clamp(1.3rem,2.5vw,1.75rem);font-family:var(--disp)}
.gf-cta p{color:rgba(255,255,255,.85);margin:5px 0 0;font-size:.98rem}
.gf-cta__btns{display:flex;gap:13px;flex-wrap:wrap}
.gfooter .gf-cta .btn--ghost{color:#fff;border:1px solid rgba(255,255,255,.55);background:transparent}
.gfooter .gf-cta .btn--ghost:hover{background:rgba(255,255,255,.14)}
.gf-main{padding:56px 0 24px}
.gf-cols{display:grid;grid-template-columns:1.7fr 1fr 1fr 1.25fr;gap:34px;padding-bottom:32px;border-bottom:1px solid rgba(255,255,255,.1)}
.gf-cols h4{color:#fff;font-size:.82rem;letter-spacing:.09em;text-transform:uppercase;margin:0 0 14px}
.gf-cols a{color:#b9c3ce;display:block;padding:5px 0;font-size:.94rem;text-decoration:none}
.gf-cols a:hover{color:#fff}
.gf-logo{display:flex;align-items:center;gap:11px;color:#fff;font-family:var(--disp);font-weight:800;font-size:1.2rem;margin-bottom:14px;text-decoration:none}
.gf-mark{width:42px;height:42px;border-radius:11px;background:#fff;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.gf-logo-img{height:128px;width:auto;max-width:320px;display:block}
.gf-brand p{font-size:.95rem;max-width:34ch;line-height:1.6;color:#9aa6b2;margin:0}
.gf-addr{font-style:normal;line-height:1.7;font-size:.94rem;margin-top:12px;color:#9aa6b2}
.gf-addr a{color:#fff;font-weight:700;text-decoration:none}
.gf-trust{display:flex;flex-wrap:wrap;gap:14px 30px;padding:22px 0;border-bottom:1px solid rgba(255,255,255,.1)}
.gf-trust div{display:flex;align-items:center;gap:10px;font-size:.9rem;color:#c9d2dc}
.gf-trust svg{width:20px;height:20px;color:var(--accent);flex:0 0 auto}
.gf-legal{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;padding-top:20px;font-size:.85rem;color:#7d8894}
.gf-legal a{color:#aeb9c5;text-decoration:none}
@media(max-width:820px){.gf-cols{grid-template-columns:1fr 1fr}.gf-brand{grid-column:1/-1}}
@media(max-width:520px){.gf-cols{grid-template-columns:1fr}.gf-cta__in{flex-direction:column;align-items:flex-start}}

/* trust bar sits on the dark --p background: a coloured --accent highlight can't hit
   4.5:1 on many themes, so highlights go white (emphasis via weight), regular text is
   dimmed so the bold still pops, and only the decorative icons keep a lightened accent */
.trust span{color:rgba(255,255,255,.80)}
.trust b{color:#fff}
.trust svg{stroke:color-mix(in srgb, var(--accent) 30%, #fff);color:color-mix(in srgb, var(--accent) 30%, #fff)}

/* ===== showcase homepage variant ===== */
/* split "why us": copy + checklist beside an image with an optional review badge */
.whyx{display:grid;grid-template-columns:1.05fr .95fr;gap:46px;align-items:center}
.whyx h2{margin:.3rem 0 .9rem}
.whyx__img{position:relative;border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow-lg);min-height:340px}
.whyx__img img{width:100%;height:100%;object-fit:cover;display:block}
.rev-badge{position:absolute;left:18px;bottom:18px;background:#fff;border-radius:14px;padding:11px 15px;box-shadow:var(--shadow-lg);display:flex;align-items:center;gap:11px}
.rev-badge .stars{display:flex;gap:1px}
.rev-badge .stars svg{width:13px;height:13px;color:var(--accent)}
.rev-badge b{display:block;font-family:var(--disp);font-size:1.15rem;color:var(--ink);line-height:1.05}
.rev-badge span{font-size:.78rem;color:var(--muted)}
.checklist{list-style:none;padding:0;margin:20px 0 0;display:grid;gap:13px}
.checklist li{display:flex;align-items:flex-start;gap:11px;font-weight:600;color:var(--ink)}
.checklist svg{width:22px;height:22px;color:var(--accent);flex:0 0 auto;margin-top:1px}
@media(max-width:820px){.whyx{grid-template-columns:1fr;gap:28px}.whyx__img{min-height:250px}}

/* stat / credibility row */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-top:38px}
.stat{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:22px 18px;text-align:center}
.stat b{display:block;font-family:var(--disp);font-size:1.85rem;color:var(--p);line-height:1}
.stat span{display:block;margin-top:7px;font-size:.85rem;color:var(--muted)}
@media(max-width:700px){.stats{grid-template-columns:1fr 1fr}}

/* homepage contact block — its own tinted background, distinct from the gradient CTA band */
.sec--contact{background:color-mix(in srgb, var(--accent) 9%, #fff);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.contact{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.contact__c{display:flex;flex-direction:column;gap:6px}
.contact__c .lbl{display:flex;align-items:center;gap:8px;font-family:var(--disp);font-weight:700;color:var(--ink);font-size:.92rem}
.contact__c .lbl svg{width:18px;height:18px;color:var(--accent);flex:0 0 auto}
.contact__c a,.contact__c .v{color:var(--muted);font-size:.95rem;word-break:break-word;text-decoration:none}
.contact__c a:hover{color:var(--p)}
.contact__cta{display:flex;gap:13px;justify-content:center;flex-wrap:wrap;margin-top:28px}
@media(max-width:700px){.contact{grid-template-columns:1fr 1fr;gap:22px 16px}}
@media(max-width:430px){.contact{grid-template-columns:1fr}}
"""

# ---------------------------------------------------------------- config
def load_config():
    themes = json.load(open(os.path.join(CONFIG, "themes.json"), encoding="utf-8"))
    sdata = json.load(open(os.path.join(CONFIG, "sites.json"), encoding="utf-8"))
    lpath = os.path.join(CONFIG, "layouts.json")
    layouts = json.load(open(lpath, encoding="utf-8")) if os.path.exists(lpath) else {}
    sites = {}
    for s in sdata["sites"]:
        th = themes[s["theme"]]
        t = {k: v for k, v in th.items() if not k.startswith("_")}
        lay = layouts.get(s.get("layout", ""), {})
        t["layout"] = {**DEFAULT_LAYOUT, **{k: v for k, v in lay.items() if not k.startswith("_")}}
        phone = s.get("phone", "")
        t.update({
            "domain": s["domain"], "city": s["city"], "st": s["st"],
            "brand": s.get("brand", f'{s["city"]} Garage Door'),
            "tagline": s.get("tagline", "Garage Door Repair & Installation"),
            "area": str(s.get("area", "")), "street": s.get("street", ""), "zip": s.get("zip", ""),
            "phone": phone, "tel": "+1" + re.sub(r"\D", "", phone),
            "content": s.get("content", s["city"].lower()),
            "ghl_form_id": s.get("ghl_form_id", ""),
            "port": s.get("port"),
            # design template ("garage" default; ironclad/volt/nimbus are full alt designs)
            "template": s.get("template", "garage"),
            # showcase homepage variant + its optional, business-supplied trust data
            "home": s.get("home", "classic"),
            "stats": s.get("stats", []), "hours": s.get("hours", ""),
            "email": s.get("email", ""), "rating": s.get("rating", ""), "reviews": s.get("reviews", ""),
        })
        sites[s["domain"]] = t
    return sites

SITES = load_config()

# ---------------------------------------------------------------- helpers
def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")

# Garbled / typographic characters that show up in content -> plain ASCII equivalents.
_CHAR_MAP = {
    "—": "-", "–": "-", "―": "-",             # em / en / horizontal-bar dashes
    "…": "...",                                          # ellipsis
    "‘": "'", "’": "'", "‚": "'", "‛": "'",  # curly single quotes
    "“": '"', "”": '"', "„": '"',             # curly double quotes
    "‹": "<", "›": ">",                            # single angle quotes
    "«": "<<", "»": ">>",                          # double angle quotes
    "→": "->", "←": "<-",                          # arrows
    " ": " ", "​": "",                             # non-breaking / zero-width space
    "�": "",                                            # replacement char
}
_CHAR_RE = re.compile("|".join(map(re.escape, _CHAR_MAP)))

def clean_text(t):
    """Normalize garbled/typographic characters (em dash, ellipsis, curly quotes...) to ASCII."""
    return _CHAR_RE.sub(lambda m: _CHAR_MAP[m.group()], t or "")

# Words kept lowercase when Title-Casing a heading (unless first/last word).
_MINOR = {"a", "an", "the", "and", "or", "but", "nor", "for", "of", "to", "in", "on", "at",
          "by", "up", "as", "is", "if", "per", "via", "vs", "with", "from"}

def humanize_heading(h):
    """Turn a snake_case heading ('what_most_people_get_wrong') into readable
    Title Case ('What Most People Get Wrong'). Non-underscore headings pass through."""
    h = clean_text(h or "")
    if "_" not in h:
        return h
    words = h.replace("_", " ").split()
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i not in (0, len(words) - 1) and lw in _MINOR:
            out.append(lw)
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)

def esc(t):
    return html.escape(clean_text(t or ""))

def render_body(text):
    """JSON body text (\\n\\n paragraphs, '- ' bullet blocks) -> HTML."""
    out = []
    for blk in re.split(r"\n\s*\n", (text or "").strip()):
        blk = blk.strip()
        if not blk:
            continue
        lines = [l for l in blk.split("\n") if l.strip()]
        if lines and all(l.strip().startswith("- ") for l in lines):
            items = "".join(f"<li>{esc(l.strip()[2:])}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{esc(' '.join(lines))}</p>")
    return "".join(out)

def faq_accordion(faqs):
    return "".join(
        f'<details{" open" if i == 0 else ""}><summary>{esc(q)}</summary>'
        f'<div class="a"><p>{esc(a)}</p></div></details>'
        for i, (q, a) in enumerate(faqs))

def seo_title(raw):
    raw = (raw or "").strip()
    return raw if len(raw) <= 60 else (raw.split(" | ")[0].strip()[:57].rstrip() + "…")

# ---------------------------------------------------------------- content loading
def load_content(t):
    """Return dict url -> page{cat,h1,title,meta,sections,faq,area_served,slug}."""
    d = os.path.join(CONTENT, t["content"])
    city_slug = slugify(t["city"])
    suffix = f"-{city_slug}-{t['st'].lower()}"
    pages = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or fn == "_run.json":
            continue
        try:
            data = json.load(open(os.path.join(d, fn), encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or "sections" not in data:
            continue
        stem = fn[:-5]
        parts = stem.split("-")
        ptype = parts[1] if len(parts) > 1 else "home"
        slug = "-".join(parts[2:])
        if ptype == "svc":
            slug = slug[:-len(suffix)] if slug.endswith(suffix.lstrip("-")) else slug
            slug = re.sub(re.escape(suffix) + "$", "", "-" + slug).lstrip("-")
            url = f"/services/{slug}/"
            cat = "service"
        elif ptype in ("nb", "sub"):
            url = f"/service-areas/{slug}/"
            cat = "area"
        elif ptype == "top":
            url = f"/guides/{slug}/"
            cat = "guide"
        elif ptype == "home":
            url = "/"
            cat = "home"
        else:
            continue
        faqs = [(f.get("q", ""), f.get("a", "")) for f in data.get("faq", []) if f.get("q")]
        pages[url] = {
            "cat": cat, "slug": slug, "url": url,
            "h1": data.get("h1", ""), "title": data.get("title", ""),
            "meta": data.get("meta", ""), "sections": data.get("sections", []),
            "faq": faqs, "area_served": data.get("schema_facts", {}).get("areaServed", t["city"]),
        }
    return pages

# ---------------------------------------------------------------- schema / head
def org_schema(t):
    addr = {"@type": "PostalAddress", "streetAddress": t["street"] or t["city"],
            "addressLocality": t["city"], "addressRegion": t["st"]}
    if t["zip"]:
        addr["postalCode"] = t["zip"]
    return {"@type": ["LocalBusiness", "HomeAndConstructionBusiness"],
            "@id": f"https://{t['domain']}/#business", "name": t["brand"],
            "url": f"https://{t['domain']}/", "telephone": t["phone"], "priceRange": "$$",
            "address": addr, "areaServed": {"@type": "City", "name": f"{t['city']}, {t['st']}"}}

def service_schema(t, h1, url):
    return {"@type": "Service", "name": h1, "serviceType": h1,
            "provider": {"@id": f"https://{t['domain']}/#business"},
            "areaServed": {"@type": "City", "name": f"{t['city']}, {t['st']}"},
            "url": f"https://{t['domain']}{url}"}

def breadcrumb_schema(t, trail):
    b = f"https://{t['domain']}"
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": b + u}
        for i, (n, u) in enumerate(trail)]}

def faq_schema(faqs):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q,
         "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}

def head_html(t, title, desc, url, schemas, og_image=HERO_IMG):
    lay = t["layout"]
    bodycls = f'lay-nav-{lay["nav"]} lay-bands-{lay["bands"]} shape-{lay["shape"]}'
    graph = {"@context": "https://schema.org", "@graph": schemas}
    og = f"https://{t['domain']}/assets/photos/{og_image}" if og_image else ""
    ogtags = (f'<meta property="og:image" content="{og}">\n<meta name="twitter:image" content="{og}">' if og else "")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<script>document.documentElement.classList.add('anim')</script>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="https://{t['domain']}{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(t['brand'])}">
<meta property="og:url" content="https://{t['domain']}{url}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
{ogtags}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="{'image/png' if t.get('has_logo') else 'image/svg+xml'}" href="{'/assets/favicon.png' if t.get('has_logo') else '/assets/favicon.svg'}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={t['fonts']}&display=swap">
<link rel="stylesheet" href="/assets/site.css">
<script type="application/ld+json">{json.dumps(graph)}</script>
</head><body class="{bodycls}">"""

# ---------------------------------------------------------------- brand / chrome
def gdoor_svg(w=40):
    return (f'<svg viewBox="0 0 44 44" width="{w}" height="{w}" aria-hidden="true">'
            f'<rect x="5" y="7" width="34" height="30" rx="3" fill="var(--p)"/>'
            f'<rect x="9" y="13" width="26" height="20" rx="1.5" fill="#fff"/>'
            f'<path d="M9 18h26M9 23h26M9 28h26" stroke="var(--p)" stroke-width="1.6"/>'
            f'<rect x="9" y="11" width="26" height="3" rx="1.5" fill="var(--accent)"/></svg>')

def brand_chip(t, px=40):
    """Brand emblem: the per-domain logo PNG when present, else the generated SVG mark."""
    if t.get("has_logo"):
        return (f'<img src="/assets/logo-emblem.png" alt="{esc(t["brand"])} logo" '
                f'width="{px}" height="{px}" loading="eager">')
    return gdoor_svg(px)

def header(t, pages):
    svc = [p for u, p in pages.items() if p["cat"] == "service"]
    areas = [p for u, p in pages.items() if p["cat"] == "area"]
    guides = [p for u, p in pages.items() if p["cat"] == "guide"]

    def mega(items, all_url=None, all_label=None, cls=""):
        links = "".join(f'<a href="{p["url"]}">{esc(area_label(p))}</a>' for p in items)
        allx = f'<a class="mega-all" href="{all_url}">{all_label}</a>' if all_url else ""
        return f'<div class="mega{cls}">{allx}{links}</div>'

    # Only surface service pages whose label reads like a menu item (short, no "?");
    # the odd marketing-headline page is still reachable via the /services/ index.
    nav_svc = [p for p in svc if "?" not in area_label(p) and len(area_label(p)) <= 32]
    nav = ""
    if nav_svc:
        nav += f'<div class="nav-item"><button type="button">Services</button>{mega(nav_svc, "/services/", "All Services")}</div>'
    if areas:
        nav += f'<div class="nav-item"><button type="button">Service Areas</button>{mega(areas[:18], "/service-areas/", "All Service Areas", " mega--areas")}</div>'
    if guides:
        nav += f'<div class="nav-item"><button type="button">Guides</button>{mega(guides, "/guides/", "All Guides")}</div>'
    # About / Contact promoted to real navbar links (visible on desktop and in the mobile menu)
    nav += '<a href="/about/">About</a><a href="/contact/">Contact</a>'
    nav += '<a class="nav-quote" href="/request-a-quote/">Request a Quote</a>'

    return f"""<div class="top"><div class="wrap"><span>Serving {esc(t['city'])} &amp; the surrounding metro</span><span class="dot">&bull;</span><span>Same-day service available</span><span class="tsp"></span><a href="tel:{t['tel']}">{icon('phone')}{esc(t['phone'])}</a></div></div>
<header class="site"><div class="wrap hd">
<a class="brand" href="/"><span class="brand__chip">{brand_chip(t, 40)}</span><span>{esc(t['brand'])}<small>{esc(t['tagline'])}</small></span></a>
<button class="burger" aria-label="Menu"><span></span><span></span><span></span></button>
<nav class="main">{nav}</nav>
<a class="btn btn--primary" href="/request-a-quote/">Free Quote</a>
</div></header>"""

def footer(t, pages):
    svc = [p for u, p in pages.items() if p["cat"] == "service"][:5]
    areas = [p for u, p in pages.items() if p["cat"] == "area"][:8]
    services = "".join(f'<a href="{p["url"]}">{esc(area_label(p))}</a>' for p in svc)
    services += '<a href="/services/">All Services</a>'
    company = ('<a href="/about/">About Us</a><a href="/contact/">Contact</a>'
               '<a href="/service-areas/">Service Areas</a><a href="/guides/">Guides</a>'
               '<a href="/request-a-quote/">Request a Quote</a>')
    area_links = "".join(f'<a href="{p["url"]}">{esc(area_label(p))}</a>' for p in areas)
    addr = f"{t['city']}, {t['st']}" + (f" {t['zip']}" if t["zip"] else "")
    blurb = f"Garage door repair, spring and opener service, and new-door installation across {esc(t['city'])} and the surrounding metro."
    if t.get("has_logo"):
        # real per-domain logo already reads as a full lockup (mark + name) on its
        # own -- no white chip box, no redundant brand-name text next to it.
        logo = f'<img class="gf-logo-img" src="/assets/logo-emblem.png" alt="{esc(t["brand"])}" loading="lazy">'
    else:
        logo = f'<span class="gf-mark">{brand_chip(t, 30)}</span><span>{esc(t["brand"])}</span>'
    brand_block = (f'<div class="gf-brand"><a class="gf-logo" href="/">{logo}</a><p>{blurb}</p>'
                   f'<address class="gf-addr">{addr}<br><a href="tel:{t["tel"]}">{esc(t["phone"])}</a></address></div>')
    cols = (f'<div><h4>Services</h4>{services}</div><div><h4>Company</h4>{company}</div>'
            f'<div><h4>Service Areas</h4>{area_links}</div>')
    trust = (f'<div class="gf-trust">'
             f'<div>{icon("shield")}<span>Licensed &amp; fully insured</span></div>'
             f'<div>{icon("clock")}<span>Same-day service available</span></div>'
             f'<div>{icon("tag")}<span>Upfront, written pricing</span></div>'
             f'<div>{icon("star")}<span>Local crew, real reviews</span></div></div>')
    legal = (f'<div class="gf-legal"><span>&copy; {date.today().year} {esc(t["brand"])}. All rights reserved.</span>'
             f'<span>{addr} &middot; <a href="tel:{t["tel"]}">{esc(t["phone"])}</a></span></div>')
    js = '<script src="/assets/nav.js" defer></script>'
    return (f'<footer class="gfooter"><div class="gf-main"><div class="wrap">'
            f'<div class="gf-cols">{brand_block}{cols}</div>{trust}{legal}</div></div></footer>{js}')

def area_label(p):
    """Short label for a page from its H1/slug."""
    h1 = re.sub(r"\s+(in|for)\s+.*$", "", p["h1"]).strip()
    h1 = h1.split(" | ")[0].split(",")[0].strip()
    if p["cat"] == "area":
        # neighborhood/suburb name from the slug
        return p["slug"].replace("-", " ").title()
    if p["cat"] == "service":
        return h1 or p["slug"].replace("-", " ").title()
    return h1 or p["slug"].replace("-", " ").title()

# ---------------------------------------------------------------- sections
def hero(t, h1, lead, img=HERO_IMG):
    """Distinct hero markup per site layout (split-right/left, stacked, center, banner,
    overlap) -- the shared design system (build_site.py's css()) already ships CSS for
    every one of these variants; this was previously hardcoded to "banner" always."""
    variant = t.get("layout", {}).get("hero", "banner")
    call = f'<a class="btn btn--primary" href="tel:{t["tel"]}">{icon("phone")}Call {esc(t["phone"])}</a>'
    quote = '<a class="btn btn--ghost" href="/request-a-quote/">Get a Free Quote</a>'
    eyebrow = f'<p class="eyebrow">{esc(t["city"])}, {esc(t["st"])} &middot; Garage Door Service</p>'
    leadh = f'<p class="lead">{esc(lead)}</p>'
    chips = ('<ul class="chips">'
             f'<li>{icon("check")}Same-day service</li><li>{icon("check")}Licensed &amp; insured</li>'
             f'<li>{icon("check")}Upfront pricing</li><li>{icon("check")}Local crew</li></ul>')
    copy = f'<div class="hero__copy">{eyebrow}<h1>{esc(h1)}</h1>{leadh}<div class="cta">{call}{quote}</div>{chips}</div>'
    src = f'/assets/photos/{img}'
    alt = f'Garage door service in {esc(t["city"])}, {esc(t["st"])}'
    badge = f'<div class="hero__badge">{icon("shield")}<div><b>Licensed</b><span>&amp; insured crew</span></div></div>'
    media = f'<div class="hero__media"><img src="{src}" alt="{alt}" fetchpriority="high">{badge}</div>'

    if variant == "split-left":
        return f'<section class="hero hero--split hero--left"><div class="wrap">{media}{copy}</div></section>'
    if variant == "stacked":
        wide = f'<div class="hero__media--wide"><img src="{src}" alt="{alt}" fetchpriority="high"></div>'
        return f'<section class="hero hero--stacked"><div class="wrap">{copy}{wide}</div></section>'
    if variant == "center":
        return f'<section class="hero hero--center" style="--hero-bg:url({src})"><div class="wrap">{copy}</div></section>'
    if variant == "overlap":
        return (f'<section class="hero hero--overlap"><div class="hero__bgimg"><img src="{src}" alt="{alt}" fetchpriority="high"></div>'
                f'<div class="wrap"><div class="hero__card">{copy}</div></div></section>')
    if variant == "split-right":
        return f'<section class="hero hero--split hero--right"><div class="wrap">{copy}{media}</div></section>'
    return f'<section class="hero hero--banner" style="--hero-bg:url({src})"><div class="wrap">{copy}</div></section>'

def trust_bar():
    return (f'<section class="trust"><div class="wrap">'
            f'<div>{icon("clock")}<span><b>Same-day</b> service available</span></div>'
            f'<div>{icon("shield")}<span>Licensed &amp; <b>fully insured</b></span></div>'
            f'<div>{icon("tag")}<span><b>Upfront</b>, written pricing</span></div>'
            f'<div>{icon("star")}<span><b>Local</b> crew, real reviews</span></div>'
            f'</div></section>')

def services_grid(t, pages):
    """Card style follows the site's layout.cards (classic/overlay/side/bold) instead of
    always rendering the same dark image-overlay card. "bold" keeps that original
    garage-door look (plus the icon chip it always had CSS for but never rendered);
    classic/overlay/side reuse the shared scard component system (build_site.py's
    css()) that was already shipped in every stylesheet but never referenced here."""
    card_imgs = t.get("card_imgs") or CARD_IMGS
    style = t.get("layout", {}).get("cards", "bold")
    items = []
    for i, (ic, title, blurb, slug) in enumerate(SERVICE_TILES):
        url = f"/services/{slug}/" if slug and f"/services/{slug}/" in pages else "/request-a-quote/"
        items.append((ic, title, blurb, url, card_imgs[i % len(card_imgs)]))

    if style == "bold":
        cards = "".join(
            f'<a class="svc-card" href="{url}">'
            f'<img src="/assets/photos/{img}" alt="{title} in {esc(t["city"])}" loading="lazy">'
            f'<div class="svc-card__ic">{icon(ic)}</div>'
            f'<div class="svc-card__b"><h3>{title}</h3><p>{blurb}</p>'
            f'<span class="more">Learn more {icon("arrow")}</span></div></a>'
            for ic, title, blurb, url, img in items)
        grid_cls = "svc-grid"
    else:
        cards = "".join(
            f'<a class="scard" href="{url}">'
            f'<img src="/assets/photos/{img}" alt="{title} in {esc(t["city"])}" loading="lazy">'
            f'<div class="scard__b"><h3>{title}</h3><p>{blurb}</p>'
            f'<span class="more">Learn more {icon("arrow")}</span></div></a>'
            for ic, title, blurb, url, img in items)
        grid_cls = f"grid g3 scards scards--{style}"

    return (f'<section class="sec sec--soft"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">What We Do</p><h2>Garage door services in {esc(t["city"])}</h2>'
            f'<p>From a snapped spring to a full door replacement — one local crew, upfront pricing.</p></div>'
            f'<div class="{grid_cls}">{cards}</div></div></section>')

def why_us(t):
    feats = [("clock", "Same-day dispatch", "Most repair calls are handled the same or next day — springs and openers don't wait."),
             ("shield", "Licensed &amp; insured", "Trained techs, proper spring tools, and the insurance to back the work."),
             ("tag", "Upfront pricing", "A written quote at the door before any work starts — no surprise add-ons."),
             ("check", "Fixed right once", "We diagnose the actual cause, not just the symptom, so the door stays fixed.")]
    cells = "".join(f'<div class="feat"><div class="ic">{icon(ic)}</div><div class="feat__b"><h3>{h}</h3><p>{d}</p></div></div>'
                    for ic, h, d in feats)
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">Why {esc(t["city"])} Calls Us</p><h2>Straight answers, honest fixes</h2></div>'
            f'<div class="grid g3 feats feats--{t["layout"]["feats"]}">{cells}</div></div></section>')

def how_it_works(t):
    style = t["layout"]["steps"]
    return (f'<section class="sec sec--soft"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">How It Works</p><h2>Getting your door fixed is simple</h2></div>'
            f'<div class="steps steps--{style}">'
            f'<div class="step"><div class="step__b"><h3>Tell us the symptom</h3><p>Call or request a quote and describe what the door is doing — noise, off-track, won\'t open.</p></div></div>'
            f'<div class="step"><div class="step__b"><h3>On-site diagnosis</h3><p>A tech inspects the springs, tracks, opener and panels and gives you a written price first.</p></div></div>'
            f'<div class="step"><div class="step__b"><h3>Repaired or installed</h3><p>Most repairs are done on the same visit; installs are scheduled around you.</p></div></div>'
            f'</div></div></section>')

# ---- showcase-variant sections (inspired by the reference design) ----
def stats_band(t):
    """Config-driven credibility row. Renders only if the site defines 'stats'
    (a list of [number, label] pairs) — never fabricates numbers."""
    stats = t.get("stats") or []
    if not stats:
        return ""
    cells = "".join(f'<div class="stat"><b>{esc(str(n))}</b><span>{esc(str(l))}</span></div>' for n, l in stats)
    return f'<div class="stats">{cells}</div>'

def why_us_split(t):
    """Two-column 'why us': copy + checklist beside an image (+ optional review badge)."""
    checks = ["Local, licensed technicians", "Upfront, written quotes",
              "Parts and labor warranty", "No overtime or weekend fees"]
    li = "".join(f'<li>{icon("check")}{esc(c)}</li>' for c in checks)
    card_imgs = t.get("card_imgs") or CARD_IMGS
    img = card_imgs[_stable_idx(t["domain"], len(card_imgs))]
    badge = ""
    if t.get("rating") and t.get("reviews"):     # only with real, configured figures
        badge = (f'<div class="rev-badge"><div class="stars">{icon("star") * 5}</div>'
                 f'<div><b>{esc(str(t["rating"]))}/5</b><span>{esc(str(t["reviews"]))} local reviews</span></div></div>')
    return (f'<section class="sec"><div class="wrap"><div class="whyx"><div>'
            f'<p class="eyebrow">Why Us</p>'
            f'<h2>Local garage door experts {esc(t["city"])} relies on</h2>'
            f'<p>We are a locally owned garage door team that treats your home and your time like our own. '
            f'Every job is handled by a vetted technician, never a subcontractor, and priced upfront before any work starts.</p>'
            f'<p>From the first call to the final test, you get straight answers, clean workmanship, and a warranty that actually means something.</p>'
            f'<ul class="checklist">{li}</ul></div>'
            f'<div class="whyx__img"><img src="/assets/photos/{img}" alt="Garage door service in {esc(t["city"])}" loading="lazy">{badge}</div>'
            f'</div>{stats_band(t)}</div></section>')

def _svg_mail():
    return ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>')

def _svg_pin():
    return ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>')

def contact_band(t):
    """Homepage 'Book Your Service Today' block: call / hours / email / service area."""
    hours = t.get("hours") or "Mon-Sat, 7am-7pm"
    phone_cell = (f'<a href="tel:{t["tel"]}">{esc(t["phone"])}</a>' if t.get("phone")
                  else '<a href="/request-a-quote/">Request a callback</a>')
    email_cell = (f'<div class="contact__c"><span class="lbl">{_svg_mail()}Email</span>'
                  f'<a href="mailto:{esc(t["email"])}">{esc(t["email"])}</a></div>') if t.get("email") else ""
    return (f'<section class="sec sec--contact"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">Get In Touch</p><h2>Book your service today</h2>'
            f'<p>Call, email, or request a callback — a real person in {esc(t["city"])} answers.</p></div>'
            f'<div class="contact">'
            f'<div class="contact__c"><span class="lbl">{icon("phone")}Call us</span>{phone_cell}</div>'
            f'<div class="contact__c"><span class="lbl">{icon("clock")}Hours</span><span class="v">{esc(hours)}</span></div>'
            f'{email_cell}'
            f'<div class="contact__c"><span class="lbl">{_svg_pin()}Service area</span>'
            f'<span class="v">{esc(t["city"])}, {esc(t["st"])} &amp; nearby</span></div></div>'
            f'<div class="contact__cta"><a class="btn btn--primary" href="/request-a-quote/">Get a Free Quote</a>'
            f'<a class="btn btn--ghost" href="tel:{t["tel"]}">{icon("phone")}Call now</a></div>'
            f'</div></section>')

def areas_band(t, pages):
    areas = [p for u, p in pages.items() if p["cat"] == "area"]
    if not areas:
        return ""
    chips = "".join(f'<a href="{p["url"]}">{esc(area_label(p))}</a>' for p in areas[:16])
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">Where We Work</p><h2>Serving {esc(t["city"])} &amp; nearby communities</h2>'
            f'<p>Neighborhoods across the city and suburbs around the metro. Not sure if we reach you? Just ask.</p></div>'
            f'<div class="areas">{chips}<a class="areas__all" href="/service-areas/">View all areas {icon("arrow")}</a></div></div></section>')

def cta_band(t, heading=None):
    heading = heading or f"Need a garage door fixed in {t['city']}?"
    return (f'<section class="sec"><div class="wrap"><div class="cta-band"><h2>{esc(heading)}</h2>'
            f'<p>Call now or request a free quote — same-day service on most repairs, upfront written pricing.</p>'
            f'<div class="cta"><a class="btn btn--primary" href="tel:{t["tel"]}">{icon("phone")}Call {esc(t["phone"])}</a>'
            f'<a class="btn btn--ghost" href="/request-a-quote/">Request a Quote</a></div></div></div></section>')

def home_faqs(t):
    c = t["city"]
    return [
        (f"Do you offer same-day garage door repair in {c}?",
         f"Yes — most repair calls in {c} are handled the same or next day. Broken springs and doors stuck open are prioritized."),
        ("How much does a garage door repair cost?",
         "It depends on the part — a spring, cable, roller or opener are all different jobs. You get a written price on site before any work starts."),
        ("Should I replace or repair an older door?",
         "If the door is original to a house from the 80s or 90s and the panels or track are failing, replacement often makes more sense than repeated repairs. We'll tell you honestly which one fits."),
        ("Is replacing a garage door spring something I can do myself?",
         "No. Torsion springs are wound under high tension and can cause serious injury. It's the one job we always recommend leaving to a tech with the right tools."),
    ]

# ---------------------------------------------------------------- pages
def home_page(t, pages):
    home = pages.get("/")
    h1 = (home["h1"] if home else "") or f"Garage Door Repair & Installation in {t['city']}, {t['st']}"
    lead = (home["meta"] if home else "") or (
        f"Local garage door repair, spring and opener service and new-door installation across {t['city']} "
        f"and the surrounding metro — same-day service, licensed techs, upfront pricing.")
    faqs = home["faq"] if (home and home["faq"]) else home_faqs(t)
    faq_html = (f'<section class="sec sec--soft"><div class="wrap"><div class="sec-head">'
                f'<p class="eyebrow">Good to Know</p><h2>Frequently asked questions</h2></div>'
                f'<div class="faq">{faq_accordion(faqs)}</div></div></section>')
    title = seo_title((home["title"] if home else "") or f"Garage Door Repair in {t['city']}, {t['st']} | {t['brand']}")
    desc = (home["meta"] if home else "") or lead
    schemas = [org_schema(t), faq_schema(faqs)]
    hero_img = t.get("hero_img") or HERO_IMG
    top = (head_html(t, title, desc, "/", schemas, og_image=hero_img) + header(t, pages)
           + hero(t, h1, lead, img=hero_img) + trust_bar())
    if t.get("home") == "showcase":
        # contact_band() helper kept in code for reuse, but not rendered on the page
        mid = (why_us_split(t) + services_grid(t, pages) + how_it_works(t)
               + areas_band(t, pages) + faq_html + cta_band(t))
    else:
        mid = (services_grid(t, pages) + why_us(t) + how_it_works(t)
               + areas_band(t, pages) + faq_html + cta_band(t))
    return top + mid + footer(t, pages) + "</body></html>"

def inner_page(t, p, pages):
    h1 = p["h1"] or area_label(p)
    img = (t.get("inner_imgs") or {}).get(p["url"]) or INNER_IMGS[_stable_idx(p["slug"] or p["url"], len(INNER_IMGS))]
    parts = []
    for idx, sec in enumerate(p["sections"]):
        h2 = sec.get("h2", "")
        parts.append(f'<h2 id="{slugify(h2)}">{esc(humanize_heading(h2))}</h2>{render_body(sec.get("body", ""))}')
        if idx == 0:
            parts.append(f'<img src="/assets/photos/{img}" alt="{esc(h1)}" loading="lazy">')
    if p["faq"]:
        parts.append(f'<h2 id="faq">Frequently asked questions</h2><div class="faq">{faq_accordion(p["faq"])}</div>')

    label = {"service": "Services", "area": "Service Areas", "guide": "Guides"}.get(p["cat"], "")
    parent = {"service": "/services/", "area": "/service-areas/", "guide": "/guides/"}.get(p["cat"], "/")
    crumb = f'<div class="crumb"><a href="/">Home</a> › <a href="{parent}">{label}</a> › {esc(h1)}</div>'
    aside = (f'<aside class="aside"><div class="qcard">{icon("phone")}<h3>Get a free quote</h3>'
             f'<p>Fast answers and real pricing for {esc(t["city"])} garage door work.</p>'
             f'<a class="tel" href="tel:{t["tel"]}">{esc(t["phone"])}</a>'
             f'<a class="btn btn--primary" href="/request-a-quote/">Request a Quote</a>'
             f'<a class="btn btn--outline" href="/service-areas/">Service Areas</a></div></aside>')
    body = (f'<section class="page-hero"><div class="wrap">{crumb}<h1>{esc(h1)}</h1></div></section>'
            f'<div class="wrap"><div class="article"><div class="body">{"".join(parts)}</div>{aside}</div></div>'
            + cta_band(t, f"Book garage door service in {t['city']}"))
    title = seo_title(p["title"] or f"{h1} | {t['brand']}")
    trail = [("Home", "/"), (label, parent), (h1, p["url"])]
    schemas = [org_schema(t), breadcrumb_schema(t, trail)]
    if p["cat"] == "service":
        schemas.append(service_schema(t, re.sub(r"\s+in\s+.*$", "", h1).strip() or h1, p["url"]))
    if p["faq"]:
        schemas.append(faq_schema(p["faq"]))
    return (head_html(t, title, p["meta"] or "", p["url"], schemas, og_image=img) + header(t, pages)
            + body + footer(t, pages) + "</body></html>")

def index_page(t, pages, cat, url, title_h1, eyebrow, blurb):
    items = [p for u, p in pages.items() if p["cat"] == cat]
    cards = ""
    for p in items:
        desc = (p["meta"] or "").split(".")[0]
        cards += (f'<a class="feat" href="{p["url"]}"><div class="ic">{icon("arrow")}</div>'
                  f'<div class="feat__b"><h3>{esc(area_label(p))}</h3><p>{esc(desc)}</p></div></a>')
    crumb = f'<div class="crumb"><a href="/">Home</a> › {esc(title_h1)}</div>'
    body = (f'<section class="page-hero"><div class="wrap">{crumb}<h1>{esc(title_h1)}</h1></div></section>'
            f'<section class="sec"><div class="wrap"><div class="sec-head"><p class="eyebrow">{eyebrow}</p>'
            f'<h2>{esc(title_h1)}</h2><p>{esc(blurb)}</p></div>'
            f'<div class="grid g3 feats feats--tiles">{cards}</div></div></section>'
            + cta_band(t))
    schemas = [org_schema(t), breadcrumb_schema(t, [("Home", "/"), (title_h1, url)])]
    return (head_html(t, seo_title(f"{title_h1} | {t['brand']}"), blurb, url, schemas, og_image=t.get("hero_img") or HERO_IMG)
            + header(t, pages) + body + footer(t, pages) + "</body></html>")

def trust_page(t, pages, url, h1, blocks, is_quote=False):
    parts = "".join(f'<h2>{esc(h)}</h2><p>{esc(b)}</p>' for h, b in blocks)
    embed = ""
    if is_quote and t.get("ghl_form_id"):
        from build_site import quote_embed
        embed = quote_embed(t["ghl_form_id"])
    crumb = f'<div class="crumb"><a href="/">Home</a> › {esc(h1)}</div>'
    aside = (f'<aside class="aside"><div class="qcard">{icon("phone")}<h3>Talk to us</h3>'
             f'<p>Garage door help in {esc(t["city"])}, {esc(t["st"])}.</p>'
             f'<a class="tel" href="tel:{t["tel"]}">{esc(t["phone"])}</a>'
             f'<a class="btn btn--primary" href="/request-a-quote/">Request a Quote</a></div></aside>')
    body = (f'<section class="page-hero"><div class="wrap">{crumb}<h1>{esc(h1)}</h1></div></section>{embed}'
            f'<div class="wrap"><div class="article"><div class="body">{parts}</div>{aside}</div></div>'
            + cta_band(t))
    schemas = [org_schema(t), breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (head_html(t, seo_title(f"{h1} | {t['brand']}"), f"{h1} — {t['brand']}, {t['city']}, {t['st']}.", url, schemas,
                       og_image=t.get("hero_img") or HERO_IMG)
            + header(t, pages) + body + footer(t, pages) + "</body></html>")

# ---------------------------------------------------------------- renderer dispatch
# The default "garage" design is the module functions above. Alternate full designs
# (ironclad / volt / nimbus) live in templates.py and expose the same interface.
GARAGE = {"css": lambda t: css(t) + GD_CSS, "navjs": NAVJS,
          "home": lambda t, pages: home_page(t, pages),
          "inner": lambda t, p, pages: inner_page(t, p, pages),
          "index": lambda t, pages, cat, url, h1, eb, bl: index_page(t, pages, cat, url, h1, eb, bl),
          "trust": lambda t, pages, url, h1, blocks, q=False: trust_page(t, pages, url, h1, blocks, q)}

def get_renderer(t):
    name = t.get("template", "garage")
    if name and name != "garage":
        import sys, templates
        templates.H = sys.modules[__name__]          # give templates access to shared helpers
        r = templates.REGISTRY.get(name)
        if r:
            return r
        print(f"  ! unknown template '{name}' -> using garage")
    return GARAGE

# ---------------------------------------------------------------- build
def write(out, url, htmlstr):
    htmlstr = clean_text(htmlstr)  # sweep any hardcoded typographic chars from the assembled page
    path = os.path.join(out, url.strip("/"), "index.html") if url != "/" else os.path.join(out, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(htmlstr)

def build():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    for domain, t in SITES.items():
        if not os.path.isdir(os.path.join(CONTENT, t["content"])):
            print(f"  skip {domain}: content/{t['content']}/ not found (add content, then rebuild)")
            continue
        R = get_renderer(t)
        out = os.path.join(DIST, domain)
        assets = os.path.join(out, "assets")
        os.makedirs(assets, exist_ok=True)
        open(os.path.join(assets, "site.css"), "w", encoding="utf-8").write(R["css"](t))
        if R.get("navjs"):
            open(os.path.join(assets, "nav.js"), "w", encoding="utf-8").write(R["navjs"])
        open(os.path.join(assets, "favicon.svg"), "w", encoding="utf-8").write(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44">'
            f'<rect width="44" height="44" rx="10" fill="{t["p"]}"/>'
            '<rect x="10" y="12" width="24" height="21" rx="2" fill="#fff"/>'
            f'<path d="M10 18h24M10 23h24M10 28h24" stroke="{t["p"]}" stroke-width="1.8"/>'
            f'<rect x="10" y="10" width="24" height="3.4" rx="1.7" fill="{t["accent"]}"/></svg>')

        # per-domain brand logo (from brand/logos/); falls back to the inline SVG if absent
        t["has_logo"] = False
        for src, dst in ((f"{domain}-emblem.png", "logo-emblem.png"),
                         (f"{domain}-emblem-light.png", "logo-emblem-light.png"),
                         (f"{domain}-lockup.png", "logo-lockup.png"),
                         (f"{domain}-favicon.png", "favicon.png")):
            sp = os.path.join(LOGOS, src)
            if os.path.exists(sp):
                shutil.copy(sp, os.path.join(assets, dst))
                if dst == "logo-emblem.png":
                    t["has_logo"] = True

        pages = load_content(t)

        # generic pool, always copied: the alt templates (ironclad/volt/nimbus in
        # templates.py) reference these gd-*.jpg filenames directly.
        pool = os.path.join(ROOT, "assets_shared", "photos")
        photos = os.path.join(assets, "photos"); os.makedirs(photos, exist_ok=True)
        if os.path.isdir(pool):
            for fn in os.listdir(pool):
                shutil.copy(os.path.join(pool, fn), os.path.join(photos, fn))

        # brand/photos/ -> per-site /assets/photos/: real city hero shot (where one
        # exists) + on-topic photos for every service tile and inner page. Used by
        # the default "garage" design (falls back to the pool above only where
        # brand/photos has no match).
        t["hero_img"], t["card_imgs"], t["inner_imgs"] = select_photos(t, pages, photos)
        # inner content pages
        for url, p in pages.items():
            if p["cat"] == "home":
                continue
            write(out, url, R["inner"](t, p, pages))
        # homepage
        write(out, "/", R["home"](t, pages))
        # section index pages
        if any(p["cat"] == "service" for p in pages.values()):
            write(out, "/services/", R["index"](t, pages, "service", "/services/",
                  f"Garage Door Services in {t['city']}", "What We Do",
                  f"Repair, installation and service for garage doors across {t['city']} and nearby."))
        if any(p["cat"] == "area" for p in pages.values()):
            write(out, "/service-areas/", R["index"](t, pages, "area", "/service-areas/",
                  f"Service Areas Around {t['city']}", "Where We Work",
                  f"Neighborhoods and suburbs we cover across the {t['city']} metro."))
        if any(p["cat"] == "guide" for p in pages.values()):
            write(out, "/guides/", R["index"](t, pages, "guide", "/guides/",
                  "Garage Door Guides", "Good to Know",
                  "Plain-English answers about springs, openers, older doors and what a repair really involves."))
        # trust pages
        write(out, "/about/", R["trust"](t, pages, "/about/", f"About {t['brand']}", [
            ("A local garage door crew",
             f"{t['brand']} is a {t['city']}-based team handling garage door repair, spring and opener service, and new-door installation across {t['city']} and the surrounding {t['st']} metro. We're not a national call center routing your job to whoever's cheapest that day - the person who answers the phone is part of the same crew that shows up in your driveway. We focus on the housing stock here and the specific problems that come with it, from decades-old single-layer steel doors to the springs and openers that wear out on them."),
            ("What we work on",
             "Most of what we do falls into three buckets: repair, service, and installation. Repairs cover the things that fail without warning - a snapped torsion spring, a frayed cable, a door jumped off its track, a bent panel, or an opener that hums but won't lift. Service is the preventive side - spring-tension checks, roller and hinge replacement, lubrication, and safety-sensor alignment that keep an aging door running quiet. Installation is for when a door is past saving and a new insulated one makes more sense than another round of patches."),
            ("The doors we see here",
             f"A lot of homes around {t['city']} still run their original garage door, often single-skin steel with no insulation and hardware that's well past its install date. Those doors were built to a lighter spec than what's standard now, so the rollers, cables, and springs on them wear faster and tend to fail in predictable ways. Knowing the local housing stock means we can usually narrow down what's wrong before we're even in the driveway, and give you a straight answer on whether it's worth repairing or time to replace."),
            ("How we work",
             "We diagnose the real cause before quoting, put the price in writing, and don't upsell parts a door doesn't need. If a spring is all it takes, we're not going to talk you into a whole new door. You get a written quote before any work starts, and most repairs are handled the same or next day - broken springs and stuck doors don't wait, and neither do we."),
            ("Straightforward pricing",
             "No hidden trip fees stacked on at the end, no vague 'diagnostic' charge that balloons once the truck arrives. We quote the whole job - parts and labor - up front, and the number we say is the number you pay. If we open the door up and find something else, we stop and talk it through with you first instead of quietly adding it to the bill."),
            ("Licensed, insured, and accountable",
             f"Our techs are trained on the tools this work actually requires. Torsion springs are wound under enough tension to cause serious injury, and replacing one is the single job we always tell homeowners never to DIY. We carry proper insurance and stand behind the work, and because we live and work in {t['city']}, our reputation here is the whole business - which is why the crew treats every door like it belongs to a neighbor, because more often than not it does."),
            ("Ready when you are",
             f"Whether it's a door that won't open this morning or a replacement you've been putting off, {t['brand']} is one call away. Reach us at {t['phone']} for same-day service on most repairs, or request a written quote and we'll tell you honestly what your door needs - nothing more."),
        ]))
        write(out, "/contact/", R["trust"](t, pages, "/contact/", f"Contact {t['brand']}", [
            ("Get in touch", f"Call {t['phone']} to reach {t['brand']} for garage door repair, service or a new-door quote in {t['city']}, {t['st']}."),
            ("Service area", f"We serve {t['city']} and the surrounding suburbs. Not sure if you're in range? Call and ask — we'll tell you straight.")]))
        write(out, "/request-a-quote/", R["trust"](t, pages, "/request-a-quote/", f"Request a Garage Door Quote in {t['city']}", [
            ("Tell us what the door is doing", f"Describe the problem — noise, off-track, a broken spring, or a door you want replaced — and we'll give you a written price. Call {t['phone']} or use the form."),
            ("Fast, no-pressure quotes", "You get a real number, not a range, once we've seen the door. Same-day service is available on most repairs.")], True))

        # sitemap / robots
        urls = sorted(set(["/"] + [p["url"] for p in pages.values() if p["cat"] != "home"]
                          + ["/services/", "/service-areas/", "/guides/", "/about/", "/contact/", "/request-a-quote/"]))
        sm = "".join(f"<url><loc>https://{domain}{u}</loc><lastmod>{BUILD_DATE}</lastmod></url>" for u in urls)
        open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8").write(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
        open(os.path.join(out, "robots.txt"), "w", encoding="utf-8").write(
            f"User-agent: *\nAllow: /\nSitemap: https://{domain}/sitemap.xml\n")
        print(f"  {domain}: {len(urls)} pages ({t['city']}, {t['st']})")
    print("Done ->", DIST)

if __name__ == "__main__":
    print("Building garage-door sites...")
    build()
