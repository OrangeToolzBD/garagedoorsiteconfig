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
import os, re, json, html, shutil, hashlib
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "config")
CONTENT = os.path.join(ROOT, "content")
DIST = os.path.join(ROOT, "dist")
BUILD_DATE = date.today().isoformat()

# Brand assets have lived at both <repo>/brand/ and <repo>/engine/brand/ at different
# points, and having two copies is genuinely confusing: dropping a new logo into the
# one the build does *not* read looks exactly like the build ignoring your file.
# So resolve it rather than hard-code it -- newest wins, and say out loud which won.
def _brand_root(kind):
    """Path to brand/<kind>, preferring whichever copy has the most files."""
    cands = [os.path.join(os.path.dirname(ROOT), "brand", kind),
             os.path.join(ROOT, "brand", kind)]
    live = [(len([1 for _, _, fs in os.walk(p) for _ in fs]), p) for p in cands if os.path.isdir(p)]
    if not live:
        return cands[0]
    # most files wins; on a tie the repo-root copy wins, because `cands` is in
    # preference order and sort() is stable. Never let it come down to path spelling.
    live.sort(key=lambda x: -x[0])
    if len(live) > 1:
        print(f"  note: brand/{kind} exists in two places; using {live[0][1]} "
              f"({live[0][0]} files), ignoring {live[1][1]} ({live[1][0]} files)")
    return live[0][1]

LOGOS = _brand_root("logos")    # per-domain brand logos (logo_prep.py / logo_gen.py)

# logo_prep.py's manifest: {domain: {kind, w, h}} for the 200 hand-made lockups.
# "kind" decides whether the header prints the business name beside the mark -- a
# lockup already draws the name into the artwork, so repeating it reads as a bug.
# Anything absent here (logo_gen.py's symbol-only marks) defaults to "mark".
try:
    LOGO_INFO = json.load(open(os.path.join(LOGOS, "_logo_manifest.json"), encoding="utf-8"))
except Exception:
    LOGO_INFO = {}

def logo_box(t, h):
    """(width, height) to render this site's logo at, at `h` px tall, preserving the
    real aspect ratio. Forcing every mark into a square box squashed the wide
    wordmarks (Mesa's is 3:1) and left the square badges swimming in padding."""
    info = t.get("logo") or {}
    w, hh = info.get("w") or 1, info.get("h") or 1
    return max(1, round(h * w / hh)), h

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

# ---------------------------------------------------------------- expanded-homepage data
# Symptom chips -> the most relevant page. Candidates are tried in order against the
# pages this site actually has, so a site missing a guide still gets a working link.
SYMPTOMS = [
    ("Door won't close",             ["/services/garage-door-repair/"]),
    ("Loud grinding or banging",     ["/guides/noises-that-mean-something/", "/services/garage-door-repair/"]),
    ("A spring has snapped",         ["/guides/when-a-spring-goes-in-cold-weather/", "/services/garage-door-repair/"]),
    ("Door came off the track",      ["/guides/why-a-door-goes-off-track/", "/services/garage-door-repair/"]),
    ("Opener hums, door won't lift", ["/services/garage-door-repair/"]),
    ("Remote or keypad is dead",     ["/services/garage-door-repair/"]),
    ("Opens partway, then stops",    ["/services/garage-door-service/", "/services/garage-door-repair/"]),
    ("Old door - fix or replace?",   ["/guides/what-an-older-door-is-worth-fixing/", "/services/garage-door-installation/"]),
]

# Door categories for the "styles we install" grid. Product facts only -- nothing here
# claims a dealership, certification or inventory we can't back on every domain.
DOOR_TYPES = [
    ("Insulated steel", "Two- and three-layer steel doors with a polyurethane or polystyrene core - the usual pick for an attached garage."),
    ("Carriage house", "Swing-out looks on a modern sectional door: overlays, decorative hardware and window inserts."),
    ("Full-view glass", "Aluminium frames with clear, frosted or tinted glass, for contemporary elevations and shop fronts."),
    ("Wood and composite", "Cedar, hemlock and composite faces for a period house or a door that has to match a stained entry."),
    ("Roll-up and commercial", "Slat and sheet roll-up doors for shops, warehouses and detached buildings on heavy daily cycles."),
    ("Custom and double-wide", "Non-standard openings, double-wide singles and paired doors measured to the opening you actually have."),
]

REPAIR_SIGNS = ["Panels are straight, sealed and rust-free",
                "Only the springs, cables or rollers have failed",
                "The opener is roughly ten years old or newer",
                "The door still balances and seals at the floor",
                "One damaged section can still be sourced"]
REPLACE_SIGNS = ["Several panels are cracked, bowed or rusted through",
                 "It is single-skin steel with no insulation at all",
                 "Sections or hardware for it are discontinued",
                 "You are paying for another repair every year",
                 "You want a quieter door, or a different look"]

MAINT_TIPS = [
    ("clock", "Listen once a month",
     "Run the door with the radio off. New rattles, pops or grinding are early warnings, not background noise."),
    ("check", "Do the balance test",
     "Pull the release, lift the door halfway and let go. A balanced door holds; one that drops is a spring problem, not an opener problem."),
    ("sparkle", "Lubricate, don't grease",
     "A light garage-door lubricant on the hinges, rollers and spring - never heavy grease, and never on the face of the track."),
    ("shield", "Test the safety reverse",
     "Lay a flat board under the door and close it. It should touch and reverse. If it doesn't, stop using the opener."),
]

def _stable_idx(s, n):
    return (sum(ord(c) for c in s) % n) if n else 0

def uses_expanded(t):
    """The 17-section homepage is the default for the "garage" design. A site opts out
    with "home": "classic" (the original 8-section stack) or "home": "showcase"."""
    return (t.get("template", "garage") or "garage") == "garage" and \
           t.get("home") not in ("classic", "showcase")

# ---------------------------------------------------------------- brand/photos
# 30 city hero shots ("<city>_garage_door.webp") + 4 per-service category pools
# (30 photos each) + 5 per-guide-topic pools (~10 photos each). Real, on-topic
# photography for every one of the 1000 registered domains -- not just the 10
# that currently build. assets_shared/photos/gd-*.jpg is now only a fallback for
# the rare gap (e.g. a city with no hero shot).
BRAND_PHOTOS = _brand_root("photos")

def _brand_list(subdir=""):
    d = os.path.join(BRAND_PHOTOS, subdir)
    try:
        return sorted(f for f in os.listdir(d) if f.lower().endswith(".webp"))
    except FileNotFoundError:
        return []

# Hero photography lives in brand/photos/GD HERO/:
#   v1/  30 city-named shots ("<slug>_garage_door.webp", plus one-offs like
#        "dallas_door.webp" and "wheaton_garage_doo.webp")
#   v2/  20 generic "garage-door-hero NN.webp" shots, no city in the name
#
# So a city with its own shot gets it, and every other city draws from the 20-image
# generic pool by a hash of its domain. That matters at this scale: the previous set
# had heroes loose at the top level with no generic pool, so ~970 of the 1000 domains
# would all have opened with the same single gd-4.jpg.
HERO_DIRS = ["GD HERO/v1", "GD HERO/v2"]

_CITY_HERO = {}
for _dir in ("GD HERO/v1", ""):          # "" keeps a flat legacy layout working
    for _fn in _brand_list(_dir):
        _base = re.sub(r"_garage_door$|_garage_doo$|_door$|_doo$", "", os.path.splitext(_fn)[0])
        if _base.startswith("garage-door-hero"):
            continue                      # generic, not a city
        _CITY_HERO.setdefault(_base, (_dir, _fn))

HERO_POOL = [("GD HERO/v2", f) for f in _brand_list("GD HERO/v2")]

SVC_PHOTO_DIRS = {
    "garage-door-repair": "GD REPAIR",
    "garage-door-installation": "GD INSTALLATION",
    "garage-door-service": "GD SERVICE",
}
GENERAL_PHOTO_DIRS = ["GD REPAIR", "GD INSTALLATION", "GD SERVICE", "GD MAINTENNANCE"]  # sic: source folder is misspelled
# the per-topic guide folders are nested inside brand/photos/GD GUIDE/, not at the top
# level -- without the prefix every guide page silently fell back to generic stock.
GUIDE_PHOTO_DIRS = {
    "why-a-door-goes-off-track": "GD GUIDE/Door Goes Off Track",
    "doors-on-houses-built-before-insulation-rules": "GD GUIDE/Doors on Houses Built Before Insulation Rules",
    "noises-that-mean-something": "GD GUIDE/Noises",
    "what-an-older-door-is-worth-fixing": "GD GUIDE/Older Door Worth Fixing",
    "when-a-spring-goes-in-cold-weather": "GD GUIDE/Spring Goes Cold Weather",
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

    # this city's own shot -> else one of the 20 generic heroes, picked by domain so
    # neighbouring cities don't land on the same image -> else the shared stock pool
    hero_src = _CITY_HERO.get(slugify(t["city"]))
    if not hero_src and HERO_POOL:
        hero_src = HERO_POOL[_stable_idx(t["domain"] + "hero", len(HERO_POOL))]
    if hero_src:
        hero_fn = "hero.webp"
        to_copy[hero_fn] = os.path.join(BRAND_PHOTOS, hero_src[0], hero_src[1])
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

    # Expanded homepage only: 6 more GD INSTALLATION shots for the door-styles grid
    # plus one GD MAINTENNANCE shot for the local-context block. Offset from the
    # service-card picks so the two grids never land on the same photo.
    door_imgs, ctx_img = [], None
    if uses_expanded(t):
        files = _brand_list("GD INSTALLATION")
        for i in range(len(DOOR_TYPES)):
            if files:
                dest = f"door-{i}.webp"
                fn = files[(_stable_idx(t["domain"] + "door", len(files)) + i * 3) % len(files)]
                to_copy[dest] = os.path.join(BRAND_PHOTOS, "GD INSTALLATION", fn)
            else:
                dest = CARD_IMGS[i % len(CARD_IMGS)]
                to_copy[dest] = os.path.join(fallback_pool, dest)
            door_imgs.append(dest)
        mfiles = _brand_list("GD MAINTENNANCE")
        if mfiles:
            ctx_img = "context.webp"
            to_copy[ctx_img] = os.path.join(BRAND_PHOTOS, "GD MAINTENNANCE",
                                            mfiles[_stable_idx(t["domain"] + "ctx", len(mfiles))])

    for dest, src in to_copy.items():
        try:
            shutil.copy(src, os.path.join(photos_dir, dest))
        except FileNotFoundError:
            pass

    return hero_fn, card_imgs, inner_imgs, door_imgs, ctx_img

# garage-door-specific CSS (appended after the shared design system; leaves porta-potty untouched)
GD_CSS = """
/* ===== garage-door overrides ===== */
/* Header brand when the logo is a full lockup: no white chip box, no text beside it.
   Height-constrained with width:auto so a 3:1 wordmark and a 1:1 badge both land at
   the same optical weight instead of one filling the bar and the other vanishing. */
.brand--lockup{display:flex;align-items:center;flex:0 0 auto;padding:2px 0}
.brand--lockup img{height:46px;width:auto;max-width:250px;object-fit:contain;display:block}
@media(max-width:960px){.brand--lockup img{height:40px;max-width:190px}}
@media(max-width:560px){.brand--lockup img{height:34px;max-width:150px}}
/* A square badge logo is a finished shape already -- drop the white chip box and let
   it sit on the header directly, a touch larger to earn back the padding it loses. */
.brand__chip--art{width:48px;height:48px;background:none;border:0;box-shadow:none;padding:0}
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
.gf-cols h3{color:#fff;font-size:.82rem;letter-spacing:.09em;text-transform:uppercase;margin:0 0 14px}
.gf-cols a{color:#b9c3ce;display:block;padding:5px 0;font-size:.94rem;text-decoration:none}
.gf-cols a:hover{color:#fff}
.gf-logo{display:flex;align-items:center;gap:11px;color:#fff;font-family:var(--disp);font-weight:800;font-size:1.2rem;margin-bottom:14px;text-decoration:none}
.gf-mark{width:42px;height:42px;border-radius:11px;background:#fff;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.gf-logo-img{height:128px;width:auto;max-width:320px;display:block}
.areas-tier{margin-bottom:22px}
.areas-tier h3{font-size:.76rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
/* The logos are dark artwork on transparency; on this near-black footer they need a
   light plate behind them or they read as an empty gap. */
.gf-logo:has(.gf-logo-img){background:#fff;border-radius:16px;padding:12px 20px;
  box-shadow:0 4px 16px rgba(0,0,0,.28);align-self:flex-start}
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

/* ===== expanded homepage ===== */
/* shared: narrow prose column for JSON-fed copy, and a centred section CTA */
.prose{max-width:760px}
.prose p{color:var(--muted);line-height:1.72;margin:0 0 1em}
.prose ul{color:var(--muted);line-height:1.72;margin:0 0 1em;padding-left:20px}
.prose--tight{max-width:640px;margin:0 auto}
.prose--tight p{margin:0}
.sec-head .prose--tight p{color:var(--muted)}
.sec-cta{display:flex;justify-content:center;margin-top:30px}

/* symptom finder */
.syms{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.sym{display:flex;align-items:center;justify-content:space-between;gap:12px;
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:17px 18px;
  font-family:var(--disp);font-weight:700;font-size:.95rem;color:var(--ink);
  box-shadow:var(--shadow);text-decoration:none;transition:border-color .18s,transform .18s,box-shadow .18s}
.sym svg{width:18px;height:18px;fill:none;stroke:var(--accent);stroke-width:2;flex:0 0 auto;transition:transform .18s}
.sym:hover{border-color:var(--p);transform:translateY(-2px);box-shadow:var(--shadow-lg);text-decoration:none;color:var(--p)}
.sym:hover svg{transform:translateX(3px)}
@media(max-width:980px){.syms{grid-template-columns:1fr 1fr}}
@media(max-width:520px){.syms{grid-template-columns:1fr}}

/* local-conditions block (city copy + photo) */
.ctx{display:grid;grid-template-columns:1.15fr .85fr;gap:44px;align-items:center}
.ctx__copy h2{font-size:clamp(1.5rem,2.4vw,2.05rem);margin-bottom:.7em}
.ctx__copy p{color:var(--muted);line-height:1.72;margin:0 0 1em}
.ctx__copy p:last-child{margin-bottom:0}
.ctx__img{border-radius:calc(var(--radius) + 4px);overflow:hidden;box-shadow:var(--shadow-lg);align-self:stretch;min-height:330px}
.ctx__img img{width:100%;height:100%;object-fit:cover;display:block}
@media(max-width:900px){.ctx{grid-template-columns:1fr;gap:28px}.ctx__img{min-height:250px;order:-1}}

/* repair vs replace */
.rvr{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.rvr__c{background:#fff;border:1px solid var(--line);border-top:3px solid var(--p);
  border-radius:var(--radius);box-shadow:var(--shadow);padding:28px 26px}
.rvr__c--alt{border-top-color:var(--accent)}
.rvr__c h3{display:flex;align-items:center;gap:11px;margin:0 0 18px;font-size:1.14rem;color:var(--ink)}
.rvr__c h3 svg{width:22px;height:22px;color:var(--p);flex:0 0 auto}
.rvr__c--alt h3 svg{color:var(--accent)}
.rvr__c ul{list-style:none;padding:0;margin:0;display:grid;gap:12px}
.rvr__c li{display:flex;align-items:flex-start;gap:11px;color:var(--muted);line-height:1.55;font-size:.96rem}
.rvr__c li svg{width:19px;height:19px;color:var(--accent);flex:0 0 auto;margin-top:2px}
@media(max-width:820px){.rvr{grid-template-columns:1fr}}

/* door styles grid */
.dts{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.dt{background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;
  box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s}
.dt:hover{transform:translateY(-4px);box-shadow:var(--shadow-lg)}
.dt img{width:100%;aspect-ratio:16/10;object-fit:cover;display:block}
.dt__b{padding:20px 21px 23px}
.dt__b h3{margin:0 0 8px;font-size:1.12rem;color:var(--ink)}
.dt__b p{margin:0;color:var(--muted);font-size:.93rem;line-height:1.6}
@media(max-width:940px){.dts{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.dts{grid-template-columns:1fr}}

/* emergency strip */
.emerg{background:linear-gradient(135deg,var(--pd),var(--p));color:#fff;padding:30px 0}
.emerg__in{display:flex;align-items:center;justify-content:space-between;gap:26px;flex-wrap:wrap}
.emerg__t{display:flex;align-items:center;gap:15px}
.emerg__t>svg{width:32px;height:32px;color:var(--accent);flex:0 0 auto}
.emerg__t b{display:block;font-family:var(--disp);font-size:1.16rem;line-height:1.3}
.emerg__t span{display:block;margin-top:4px;font-size:.93rem;color:rgba(255,255,255,.85)}
.emerg .btn{background:#fff;color:var(--p);border:0;flex:0 0 auto}
.emerg .btn:hover{background:var(--accent);color:var(--on-accent)}
@media(max-width:760px){.emerg__in{flex-direction:column;align-items:flex-start}}

/* maintenance tips */
.tips{display:grid;grid-template-columns:repeat(4,1fr);gap:22px}
.tip{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:24px 22px;box-shadow:var(--shadow)}
.tip__ic{width:46px;height:46px;border-radius:13px;display:flex;align-items:center;justify-content:center;
  background:color-mix(in srgb, var(--accent) 15%, #fff);color:var(--accent);margin-bottom:15px}
.tip__ic svg{width:24px;height:24px}
.tip h3{margin:0 0 8px;font-size:1.04rem;color:var(--ink)}
.tip p{margin:0;color:var(--muted);font-size:.9rem;line-height:1.6}
@media(max-width:1000px){.tips{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.tips{grid-template-columns:1fr}}

/* spring-safety callout */
.safety{display:grid;grid-template-columns:auto 1fr;gap:26px;align-items:start;
  background:#fff;border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:var(--radius);box-shadow:var(--shadow);padding:32px 34px;max-width:960px;margin:0 auto}
.safety__ic{width:56px;height:56px;border-radius:15px;display:flex;align-items:center;justify-content:center;
  background:color-mix(in srgb, var(--accent) 15%, #fff);color:var(--accent);flex:0 0 auto}
.safety__ic svg{width:30px;height:30px}
.safety__b h2{font-size:clamp(1.35rem,2vw,1.7rem);margin-bottom:.6em}
.safety__b p{color:var(--muted);line-height:1.72;margin:0 0 .9em}
.safety__b p:last-child{margin-bottom:0}
@media(max-width:640px){.safety{grid-template-columns:1fr;gap:18px;padding:26px 22px}}

/* guides teaser */
.gcards{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.gcard{background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;
  box-shadow:var(--shadow);text-decoration:none;display:flex;flex-direction:column;transition:transform .2s,box-shadow .2s}
.gcard:hover{transform:translateY(-4px);box-shadow:var(--shadow-lg);text-decoration:none}
.gcard img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.gcard__b{padding:21px 22px 24px;display:flex;flex-direction:column;gap:9px;flex:1}
.gcard__b h3{margin:0;font-size:1.08rem;color:var(--ink);line-height:1.3}
.gcard__b p{margin:0;color:var(--muted);font-size:.92rem;line-height:1.58;flex:1}
.gcard__b .more{display:inline-flex;align-items:center;gap:7px;font-family:var(--disp);font-weight:700;font-size:.89rem;color:var(--p)}
.gcard__b .more svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;transition:transform .2s}
.gcard:hover .more svg{transform:translateX(4px)}
@media(max-width:940px){.gcards{grid-template-columns:1fr}}
"""

# ===== quote form =====
# The conversion asset, and the only markup shared verbatim across all four designs --
# templates.py appends this too, so ironclad/nimbus get the same form styling without
# pulling in the rest of the garage design system. Deliberately uses only the CSS
# custom properties every design defines.
# Every custom property carries a fallback: ironclad/volt/nimbus each define their own,
# disjoint variable sets (--rule/--brass, --lime/--out, --sky/--soft), so bare var()
# references would resolve to nothing on three of the four designs.
QFORM_CSS = """
.qform{background:var(--card,#fff);border:1px solid var(--line,#e3e8ee);
  border-radius:var(--radius,16px);box-shadow:var(--shadow-lg,0 12px 40px rgba(16,32,48,.14));
  padding:clamp(22px,3vw,34px)}
.qform__grid{display:grid;grid-template-columns:1fr 1fr;gap:16px 18px}
.qform__f{display:flex;flex-direction:column;gap:6px}
.qform__f--wide{grid-column:1/-1}
.qform label{font-family:var(--disp,inherit);font-weight:700;font-size:.88rem;color:var(--ink,#16202b)}
.qform label .req{color:var(--accent,#c0392b);margin-left:3px}
.qform input,.qform select,.qform textarea{font:inherit;font-size:1rem;color:var(--ink,#16202b);
  background:#fff;border:1px solid var(--line,#d8dee6);border-radius:12px;padding:12px 14px;width:100%;
  transition:border-color .15s,box-shadow .15s}
.qform input:focus,.qform select:focus,.qform textarea:focus{outline:none;
  border-color:var(--p,#16202b);box-shadow:0 0 0 3px color-mix(in srgb,var(--p,#16202b) 22%,transparent)}
.qform input:user-invalid,.qform textarea:user-invalid{border-color:#c0392b}
.qform textarea{min-height:120px;resize:vertical}
.qform__hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.qform__foot{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:22px}
.qform__foot button{flex:0 0 auto;font:inherit;font-family:var(--disp,inherit);font-weight:700;
  font-size:1rem;cursor:pointer;border:0;border-radius:var(--btn-r,12px);padding:14px 26px;
  background:var(--accent,#16202b);color:var(--on-accent,#fff)}
.qform__foot button:hover{filter:brightness(1.07)}
.qform__note{color:var(--muted,#5b6b7c);font-size:.86rem;margin:0;flex:1;min-width:200px}
/* shown only when an unconfigured form is submitted, so the placeholder state is
   visible to whoever is reviewing the page and invisible once form_action is set */
.qform__pending{flex-basis:100%;margin:6px 0 0;padding:11px 14px;border-radius:10px;
  background:#fff4e5;border:1px solid #f0c98a;color:#7a4b12;font-size:.88rem}
.qform__pending code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em}
.qform__pending[hidden]{display:none}
.qform__side{display:flex;flex-direction:column;gap:14px}
.qform__side .qcard{margin:0}
.quote-lead{display:grid;grid-template-columns:1.35fr .65fr;gap:34px;align-items:start;
  padding:44px 0 8px}
@media(max-width:900px){.quote-lead{grid-template-columns:1fr;gap:26px}
  .qform__grid{grid-template-columns:1fr}}
"""

# ---------------------------------------------------------------- config
def load_config():
    themes = json.load(open(os.path.join(CONFIG, "themes.json"), encoding="utf-8"))
    sdata = json.load(open(os.path.join(CONFIG, "sites.json"), encoding="utf-8"))
    lpath = os.path.join(CONFIG, "layouts.json")
    layouts = json.load(open(lpath, encoding="utf-8")) if os.path.exists(lpath) else {}
    # Optional top-level "defaults" object in sites.json, applied under every entry.
    # This is how one lead-capture endpoint (form_action) or one phone number can be
    # set for all 1000+ domains at once instead of edited into each of them.
    defaults = {k: v for k, v in sdata.get("defaults", {}).items() if not k.startswith("_")}
    sites = {}
    for s in sdata["sites"]:
        s = {**defaults, **s}
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
            # Endpoint the native quote form POSTs to. Empty = no working form; the
            # build prints a warning and the page falls back to a "how to reach us" block.
            "form_action": s.get("form_action", ""),
            "port": s.get("port"),
            # design template ("garage" default; ironclad/nimbus are full alt designs)
            # deliberately NOT defaulted to "garage": site_design() derives one from
            # the domain when this is blank, so sites registered without a template
            # spread across all ten designs instead of stacking on the default
            "template": s.get("template", ""),
            # homepage stack: "expanded" (default, 17 sections) | "classic" (the original
            # 8) | "showcase" -- plus the optional, business-supplied trust data below
            "home": s.get("home", "expanded"),
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

def home_title(t, pages):
    """Homepage <title>, guaranteed not to collide with a service page's.

    Several cities' content ships the identical title in both `<city>-home.json` and
    `<city>-svc-garage-door-repair.json`, which left the homepage and its strongest
    money page competing for the same query. Fall back to a brand-led title when the
    authored one is already taken."""
    home = pages.get("/")
    taken = {(p.get("title") or "").strip().lower()
             for u, p in pages.items() if u != "/" and p.get("title")}
    b, c, st = t["brand"], t["city"], t["st"]
    candidates = [
        ((home or {}).get("title") or "").strip(),
        f"{b} | Garage Door Repair in {c}, {st}",
        f"{b} | Garage Door Repair & Service",       # for brands too long for the above
        f"{b} | Garage Door Repair",
    ]
    free = [x for x in candidates if x and x.lower() not in taken]
    # prefer a candidate that also survives the 60-char trim intact
    return next((x for x in free if len(x) <= 60), free[0] if free else f"Garage Door Repair in {c}, {st}")

# ---------------------------------------------------------------- phone / call-to-action
# Only 2 of 1001 registered domains carry a phone number today. Rendering the call
# affordances unconditionally produced `<a href="tel:+1"></a>` -- an empty, unlabelled
# link that dials nothing -- on roughly six spots per page. Every caller below now goes
# through these helpers, which fall back to the quote page when there is no number.
def has_phone(t):
    """True when this site has a real, dialable number configured."""
    return bool(re.sub(r"\D", "", t.get("phone") or ""))

def phone_link(t, cls="", with_icon=False):
    """Bare `<a>` showing the number, or "" when no number is on file."""
    if not has_phone(t):
        return ""
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="tel:{t["tel"]}">{icon("phone") if with_icon else ""}{esc(t["phone"])}</a>'

def _reach(t, form_first=False):
    """Sentence fragment naming how to reach this business, for hard-coded trust-page
    prose. Never emits a dangling "Call  ." when no number is configured."""
    if has_phone(t) and form_first:
        return f"Call {t['phone']} or use the form above"
    if has_phone(t):
        return f"Call {t['phone']}"
    return "Send us the details" if form_first else "Use the quote form"

def call_cta(t, cls="btn btn--primary", label=None, quote_label="Get a Free Quote"):
    """The primary "reach us" button: dial it when there's a number, otherwise send
    the visitor to the quote form, which is the working conversion path either way."""
    if has_phone(t):
        return f'<a class="{cls}" href="tel:{t["tel"]}">{icon("phone")}{esc(label or "Call " + t["phone"])}</a>'
    return f'<a class="{cls}" href="/request-a-quote/">{_svg_mail()}{esc(quote_label)}</a>'

# ---------------------------------------------------------------- content loading
# ---------------------------------------------------------------- variation recipe
# At ~1000 sites there is no version of "pick a nice layout" that scales -- the look has
# to be derived. Every axis below is chosen from a hash of the domain, so:
#   * a domain always builds the same site (rebuilds are diffable, nothing churns),
#   * neighbouring cities land on different combinations,
#   * and nothing has to be stored, assigned by hand, or kept in sync by a teammate.
#
# The axes are intentionally *compositional*: each one emits a class onto <body> and the
# shared stylesheet defines what that class means. A design supplies the visual language
# (colour, type, its own hero and sections); the recipe varies the structure inside it.
# Ten designs x these axes is a very large space, and every combination is one that the
# CSS was written to handle -- which is the difference between variation and randomness.

TYPE_PAIRS = [
    ("Urbanist:wght@600;700;800", "Urbanist", "Open Sans:wght@400;500;600", "Open Sans"),
    ("Sora:wght@600;700;800", "Sora", "Inter:wght@400;500;600", "Inter"),
    ("Manrope:wght@600;700;800", "Manrope", "Inter:wght@400;500;600", "Inter"),
    ("Outfit:wght@600;700;800", "Outfit", "Karla:wght@400;500;600", "Karla"),
    ("Bricolage+Grotesque:wght@600;700;800", "Bricolage Grotesque", "Inter:wght@400;500;600", "Inter"),
    ("Fraunces:opsz,wght@9..144,600;9..144,700", "Fraunces", "Karla:wght@400;500;600", "Karla"),
    ("Bitter:wght@600;700", "Bitter", "Nunito Sans:wght@400;600;700", "Nunito Sans"),
    ("Archivo:wght@600;700;800", "Archivo", "Inter:wght@400;500;600", "Inter"),
    ("Space Grotesk:wght@600;700", "Space Grotesk", "Inter:wght@400;500;600", "Inter"),
    ("Plus Jakarta Sans:wght@600;700;800", "Plus Jakarta Sans", "Inter:wght@400;500;600", "Inter"),
]

VARIANT_AXES = {
    "nav":   ["left", "center", "split", "wide"],      # where the nav sits in the bar
    "hero":  ["tall", "compact", "left", "center"],    # hero height and alignment
    "btn":   ["pill", "round", "sharp", "wide"],       # button shape
    "card":  ["raised", "flat", "outline", "edge"],    # card treatment
    "foot":  ["cols", "stack", "center", "split"],     # footer layout
    "space": ["tight", "normal", "airy"],              # vertical rhythm
    "img":   ["square", "round", "soft"],              # image corners
    "grid":  ["g2", "g3", "g4"],                       # cards per row
    "cta":   ["end", "mid", "both"],                   # CTA placement
    "reviews": ["quote", "card", "row"],               # review block layout (when data exists)
}

# Blocks a site may go without. The rest are load-bearing (services, areas, FAQ, CTA)
# and are never dropped: cutting them would trade page variety for lost conversions and
# thinner pages, which is the opposite of the point.
DROPPABLE = ["segments", "tips", "safety", "emergency", "rvr", "doors", "symptoms", "signals"]


def _pick(seed, key, options):
    return options[int(hashlib.md5(f"{seed}|{key}".encode()).hexdigest(), 16) % len(options)]


# The ten designs, in the order engine.py's bulk assigns them.
DESIGN_NAMES = ["garage", "ironclad", "nimbus", "forge", "coastline",
                "beacon", "atlas", "hearth", "quarry", "verdant"]


def site_design(t):
    """Which design this site renders with.

    An explicit "template" in sites.json always wins. Without one the design is DERIVED
    from the domain rather than falling back to "garage" -- because 992 of the 1001
    registered sites have no template, and returning the default for all of them meant
    every site a teammate generated came out on the same design. The recipe varied nav,
    cards, spacing and type inside that one design, which is real variation but reads as
    "almost the same site". Deriving it spreads them across all ten.
    """
    name = (t.get("template") or "").strip()
    return name if name else _pick(t.get("domain", ""), "design", DESIGN_NAMES)


def recipe(t):
    """The per-site variation recipe. Cached on `t` so every caller sees one answer."""
    if t.get("_recipe"):
        return t["_recipe"]
    seed = t.get("domain", "")
    r = {k: _pick(seed, k, opts) for k, opts in VARIANT_AXES.items()}
    r["type"] = _pick(seed, "type", TYPE_PAIRS)
    # drop 2 of the optional blocks, so section *selection* varies and not just order
    order = sorted(DROPPABLE, key=lambda n: hashlib.md5(f"{seed}|drop|{n}".encode()).hexdigest())
    r["drop"] = tuple(order[:2])
    t["_recipe"] = r
    return r


def variant_classes(t):
    """The <body> class list. A design reads these purely through CSS."""
    r = recipe(t)
    return " ".join(f"v-{k}-{r[k]}" for k in VARIANT_AXES)


def type_css(t):
    """Per-site typography. Appended after the design's own stylesheet so it wins, and
    applied through variables rather than by rewriting each design's font rules."""
    _, disp, _, body = recipe(t)["type"]
    return (f":root{{--v-disp:'{disp}';--v-body:'{body}'}}\n"
            "body{font-family:var(--v-body),system-ui,sans-serif}\n"
            "h1,h2,h3,h4,.hb-eyebrow,.tc-brand__txt{font-family:var(--v-disp),system-ui,sans-serif}\n")


def type_fonts(t):
    """The Google Fonts query for this site's pairing."""
    d, _, b, _ = recipe(t)["type"]
    return f"family={d}&family={b}"


# Structure only: each token adjusts layout, never colour, so it composes with any
# design's palette.
VARIANT_CSS = """
/* ---- nav placement ---- */
.v-nav-center .tc-nav{margin:0 auto}
.v-nav-center .tc-inner{justify-content:space-between}
.v-nav-split .tc-nav{margin-left:auto;margin-right:auto}
.v-nav-split .tc-acts{margin-left:0}
.v-nav-wide .tc-inner{max-width:none;padding-left:40px;padding-right:40px}
.v-nav-wide .tc-nav{gap:14px}
/* ---- hero rhythm ---- */
.v-hero-tall .fg-hero,.v-hero-tall .qy-slab img{min-height:84vh}
.v-hero-tall .cs-hero,.v-hero-tall .at-in,.v-hero-tall .vd-hero,.v-hero-tall .ht-hero{padding-top:92px;padding-bottom:64px}
.v-hero-compact .fg-hero{min-height:58vh}
.v-hero-compact .cs-hero,.v-hero-compact .at-in,.v-hero-compact .vd-hero,.v-hero-compact .ht-hero{padding-top:44px;padding-bottom:26px}
.v-hero-compact .bc-hero,.v-hero-compact .qy-hero{padding-top:52px;padding-bottom:44px}
.v-hero-center .vd-hero,.v-hero-center .bc-in,.v-hero-center .qy-hero{text-align:center;margin-left:auto;margin-right:auto}
.v-hero-center .bc-acts,.v-hero-center .qy-acts{justify-content:center}
.v-hero-left .vd-hero{text-align:left;margin-left:0}
.v-hero-left .vd-acts{justify-content:flex-start}
/* ---- buttons ---- */
.v-btn-pill .tc-cta,.v-btn-pill .hb-cta__btn,.v-btn-pill .pg-btn,.v-btn-pill .hb-emerg__btn,
.v-btn-pill .abar__btn{border-radius:999px}
.v-btn-round .tc-cta,.v-btn-round .hb-cta__btn,.v-btn-round .pg-btn,.v-btn-round .hb-emerg__btn,
.v-btn-round .abar__btn{border-radius:12px}
.v-btn-sharp .tc-cta,.v-btn-sharp .hb-cta__btn,.v-btn-sharp .pg-btn,.v-btn-sharp .hb-emerg__btn,
.v-btn-sharp .abar__btn{border-radius:0}
.v-btn-wide .tc-cta,.v-btn-wide .hb-cta__btn,.v-btn-wide .pg-btn,.v-btn-wide .hb-emerg__btn{
  border-radius:8px;padding-left:34px;padding-right:34px;letter-spacing:.02em}
/* ---- cards ---- */
/* The card axis sets the *treatment* (shadow / border / edge). Corner radius goes
   through --v-card-r so a design keeps its own roundness: nimbus is a soft 26px design
   and a hard-coded 10px here fought that, making its cards look like a different site's.
   Designs that want square corners set --v-card-r:0. */
.v-card-raised .hb-svc,.v-card-raised .hb-guide,.v-card-raised .hb-sig,.v-card-raised .hb-door,
.v-card-raised .hb-tip,.v-card-raised .hb-seg{box-shadow:0 10px 30px rgba(15,23,42,.10);
  border-radius:var(--v-card-r,16px);overflow:hidden}
.v-card-flat .hb-svc,.v-card-flat .hb-guide,.v-card-flat .hb-sig,.v-card-flat .hb-door,
.v-card-flat .hb-tip,.v-card-flat .hb-seg{box-shadow:none;border-radius:var(--v-card-r,0)}
.v-card-outline .hb-svc,.v-card-outline .hb-guide,.v-card-outline .hb-sig,.v-card-outline .hb-door,
.v-card-outline .hb-tip,.v-card-outline .hb-seg{box-shadow:none;border:1px solid currentColor;
  border-color:color-mix(in srgb,currentColor 18%,transparent);border-radius:var(--v-card-r,10px)}
.v-card-edge .hb-svc,.v-card-edge .hb-guide,.v-card-edge .hb-door,.v-card-edge .hb-tip{
  box-shadow:none;border-radius:0;border-left:3px solid var(--accent,currentColor)}
/* ---- images ---- */
.v-img-round .hb-svc__img img,.v-img-round .hb-guide__img img,.v-img-round .hb-door__img img,
.v-img-round .pg-body img{border-radius:18px}
.v-img-soft .hb-svc__img img,.v-img-soft .hb-guide__img img,.v-img-soft .hb-door__img img,
.v-img-soft .pg-body img{border-radius:8px}
.v-img-square .hb-svc__img img,.v-img-square .hb-guide__img img,.v-img-square .hb-door__img img,
.v-img-square .pg-body img{border-radius:0}
/* ---- grid density ---- */
.v-grid-g2 .hb-svcs,.v-grid-g2 .hb-guides,.v-grid-g2 .hb-doors{grid-template-columns:repeat(2,1fr)}
.v-grid-g4 .hb-svcs,.v-grid-g4 .hb-guides,.v-grid-g4 .hb-doors{grid-template-columns:repeat(4,1fr)}
.v-grid-g2 .hb-sigs,.v-grid-g2 .hb-tips{grid-template-columns:repeat(2,1fr)}
/* ---- vertical rhythm ---- */
.v-space-tight .hb{padding-top:52px;padding-bottom:52px}
.v-space-airy .hb{padding-top:104px;padding-bottom:104px}
.v-space-airy .hb h2{margin-bottom:44px}
/* ---- footer ---- */
.v-foot-stack .tc-fcols{grid-template-columns:1fr 1fr}
.v-foot-center .tc-fcols{grid-template-columns:1fr;text-align:center;justify-items:center}
.v-foot-center .tc-fbrand p,.v-foot-center .tc-fbrand address{margin-left:auto;margin-right:auto}
.v-foot-center .tc-flegal{justify-content:center;text-align:center}
.v-foot-split .tc-fcols{grid-template-columns:1.4fr 1fr 1fr}
.v-foot-split .tc-fcol:nth-child(n+4){display:none}
/* ---- reviews (only rendered when a site has real review data) ---- */
.hb-revs{display:grid;gap:20px}
.hb-rev{margin:0;padding:26px}
.hb-rev blockquote{margin:0 0 14px;font-size:1.05rem;line-height:1.55}
.hb-rev figcaption{font-size:.88rem;opacity:.75;font-style:normal}
.hb-rev--quote .hb-revs{grid-template-columns:1fr;max-width:74ch}
.hb-rev--quote .hb-rev blockquote{font-size:1.25rem}
.hb-rev--card .hb-revs{grid-template-columns:repeat(3,1fr)}
.hb-rev--row .hb-revs{grid-template-columns:1fr}
.hb-rev--row .hb-rev{display:grid;grid-template-columns:1fr auto;gap:20px;align-items:center;padding:20px 0}
.hb-rev--row .hb-rev blockquote{margin:0}
@media(max-width:980px){.hb-rev--card .hb-revs{grid-template-columns:1fr}}
@media(max-width:620px){.hb-rev--row .hb-rev{grid-template-columns:1fr;gap:8px}}
@media(max-width:980px){
  .v-grid-g4 .hb-svcs,.v-grid-g4 .hb-guides,.v-grid-g4 .hb-doors{grid-template-columns:repeat(2,1fr)}
  .v-foot-split .tc-fcols{grid-template-columns:1fr 1fr}
}
@media(max-width:620px){
  .v-grid-g2 .hb-svcs,.v-grid-g2 .hb-guides,.v-grid-g2 .hb-doors,
  .v-grid-g4 .hb-svcs,.v-grid-g4 .hb-guides,.v-grid-g4 .hb-doors,
  .v-grid-g2 .hb-sigs,.v-grid-g2 .hb-tips{grid-template-columns:1fr}
  .v-nav-wide .tc-inner{padding-left:18px;padding-right:18px}
  .v-space-airy .hb{padding-top:60px;padding-bottom:60px}
}
"""


# ---------------------------------------------------------------- local conditions
# The engine's biggest content problem is that a Boone page and a Mesa page say the same
# thing with the city name swapped. Conditions fix that at the source: a site in Arizona
# writes about heat and dust, a site in Minnesota writes about freeze-thaw, and the pages
# differ because the subject differs.
#
# Keyed by state, because a state-level climate claim holds for every city in it. City
# claims ("this town is in a Very High Fire Hazard Severity Zone") are not something the
# engine can know for 1000 cities without inventing them, so those live in the "cities"
# override block and only appear where someone has checked.
try:
    CONDITIONS = json.load(open(os.path.join(CONFIG, "conditions.json"), encoding="utf-8"))
except Exception:
    CONDITIONS = {"conditions": {}, "states": {}, "cities": {}, "_default": []}


def site_conditions(t):
    """[(id, condition)] for this site: city override, else state, else the default."""
    ids = (CONDITIONS.get("cities", {}).get(t.get("content", ""))
           or CONDITIONS.get("states", {}).get(t.get("st", "").upper())
           or CONDITIONS.get("_default", []))
    defs = CONDITIONS.get("conditions", {})
    return [(i, defs[i]) for i in ids if i in defs]


def _fill(text, t):
    return (text or "").replace("{city}", t["city"]).replace("{st}", t["st"])


def condition_pages(t):
    """Generated guide pages, one per local condition, in the same shape load_content()
    produces -- so navigation, the guides index, sitemap and internal linking pick them
    up with no special-casing anywhere downstream."""
    out = {}
    for cid, c in site_conditions(t):
        slug = f"{cid}-and-your-garage-door"
        url = f"/guides/{slug}/"
        title = _fill(c.get("title", ""), t)
        out[url] = {
            "cat": "guide", "slug": slug, "url": url, "kind": "cond",
            "h1": title, "title": f"{title} | {t['brand']}",
            "meta": _fill(c.get("summary", ""), t),
            "sections": [{"h2": "", "body": _fill(p, t)} for p in c.get("body", [])],
            "faq": [(_fill(f.get("q", ""), t), _fill(f.get("a", ""), t)) for f in c.get("faq", [])],
            "area_served": t["city"],
        }
    return out


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
            # "nb" (a neighborhood inside the city) vs "sub" (a nearby community) is
            # already encoded in the filename and used to be thrown away here. Keeping
            # it lets the areas section split into two real tiers instead of one flat
            # list -- the distinction is in the content, not invented at render time.
            "kind": ptype,
            "h1": data.get("h1", ""), "title": data.get("title", ""),
            "meta": data.get("meta", ""), "sections": data.get("sections", []),
            "faq": faqs, "area_served": data.get("schema_facts", {}).get("areaServed", t["city"]),
        }
    # Local-condition guides, added only where the city's own content has not already
    # written that topic -- a hand-written page always beats a generated one.
    for url, page in condition_pages(t).items():
        pages.setdefault(url, page)
    return pages

# ---------------------------------------------------------------- schema / head
def org_schema(t):
    # Omit rather than invent: a blank telephone and a streetAddress holding the city
    # name are both worse than an absent property in LocalBusiness markup.
    addr = {"@type": "PostalAddress", "addressLocality": t["city"], "addressRegion": t["st"]}
    if t["street"]:
        addr["streetAddress"] = t["street"]
    if t["zip"]:
        addr["postalCode"] = t["zip"]
    org = {"@type": ["LocalBusiness", "HomeAndConstructionBusiness"],
           "@id": f"https://{t['domain']}/#business", "name": t["brand"],
           "url": f"https://{t['domain']}/", "priceRange": "$$",
           "address": addr, "areaServed": {"@type": "City", "name": f"{t['city']}, {t['st']}"}}
    if has_phone(t):
        org["telephone"] = t["phone"]
    return org

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
    bodycls = (f'lay-nav-{lay["nav"]} lay-bands-{lay["bands"]} shape-{lay["shape"]} '
               + variant_classes(t))
    graph = {"@context": "https://schema.org", "@graph": schemas}
    og = f"https://{t['domain']}/assets/photos/{og_image}" if og_image else ""
    ogtags = (f'<meta property="og:image" content="{og}">\n<meta name="twitter:image" content="{og}">' if og else "")
    # The hero is the LCP element on every page type -- preload it so it isn't queued
    # behind the stylesheet and the webfont request.
    preload = (f'<link rel="preload" as="image" href="/assets/photos/{og_image}" fetchpriority="high">'
               if og_image else "")
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{type_fonts(t)}&display=swap">
<link rel="stylesheet" href="/assets/site.css">
{preload}
<script type="application/ld+json">{json.dumps(graph)}</script>
</head><body class="{bodycls}"><a class="skip" href="#main">Skip to content</a>"""

# ---------------------------------------------------------------- brand / chrome
def gdoor_svg(w=40):
    return (f'<svg viewBox="0 0 44 44" width="{w}" height="{w}" aria-hidden="true">'
            f'<rect x="5" y="7" width="34" height="30" rx="3" fill="var(--p)"/>'
            f'<rect x="9" y="13" width="26" height="20" rx="1.5" fill="#fff"/>'
            f'<path d="M9 18h26M9 23h26M9 28h26" stroke="var(--p)" stroke-width="1.6"/>'
            f'<rect x="9" y="11" width="26" height="3" rx="1.5" fill="var(--accent)"/></svg>')

def brand_chip(t, px=40):
    """Brand emblem: the per-domain logo PNG when present, else the generated SVG mark.
    Sized from the file's real aspect ratio, never forced square."""
    if t.get("has_logo"):
        w, h = logo_box(t, px)
        return (f'<img src="/assets/logo-emblem.png" alt="{esc(t["brand"])} logo" '
                f'width="{w}" height="{h}" loading="eager" decoding="async">')
    return gdoor_svg(px)

def is_wide_lockup(t, min_aspect=1.6):
    """True when the logo is a *horizontal* lockup -- name set beside the mark, so it
    stays readable at header height and can stand on its own.

    A square badge is also a lockup (the name is drawn inside it), but stacked into
    a circle or crest it is illegible at 46px -- so those keep the text label and the
    badge acts as the emblem. Judging this by shape rather than by `kind` is what
    keeps Mesa's 3:1 wordmark and Naperville's round crest both looking deliberate."""
    info = t.get("logo") or {}
    if not t.get("has_logo") or info.get("kind") != "lockup":
        return False
    w, h = info.get("w") or 0, info.get("h") or 0
    return bool(h) and (w / h) >= min_aspect

def brand_lockup(t, h=46):
    """The clickable brand in the header. Both paths carry the accessible name --
    alt text on the standalone lockup, visible text alongside the badge."""
    if is_wide_lockup(t):
        w, hh = logo_box(t, h)
        return (f'<a class="brand brand--lockup" href="/">'
                f'<img src="/assets/logo-emblem.png" alt="{esc(t["brand"])}" '
                f'width="{w}" height="{hh}" loading="eager" decoding="async"></a>')
    # A real badge is already a finished shape -- the white chip box is only there to
    # give the generated SVG mark something to sit on.
    chip = "brand__chip brand__chip--art" if t.get("has_logo") else "brand__chip"
    return (f'<a class="brand" href="/"><span class="{chip}">{brand_chip(t, 44)}</span>'
            f'<span>{esc(t["brand"])}<small>{esc(t["tagline"])}</small></span></a>')

def header(t, pages):
    svc = [p for u, p in pages.items() if p["cat"] == "service"]
    areas = [p for u, p in pages.items() if p["cat"] == "area"]
    guides = [p for u, p in pages.items() if p["cat"] == "guide"]

    def mega(items, mid, all_url=None, all_label=None, cls=""):
        links = "".join(f'<a href="{p["url"]}">{esc(area_label(p))}</a>' for p in items)
        allx = f'<a class="mega-all" href="{all_url}">{all_label}</a>' if all_url else ""
        return f'<div class="mega{cls}" id="{mid}">{allx}{links}</div>'

    def trigger(label, mid):
        return (f'<button type="button" aria-expanded="false" aria-controls="{mid}" '
                f'aria-haspopup="true">{label}</button>')

    # Only surface service pages whose label reads like a menu item (short, no "?");
    # the odd marketing-headline page is still reachable via the /services/ index.
    nav_svc = [p for p in svc if "?" not in area_label(p) and len(area_label(p)) <= 32]
    nav = ""
    if nav_svc:
        nav += (f'<div class="nav-item">{trigger("Services", "m-svc")}'
                f'{mega(nav_svc, "m-svc", "/services/", "All Services")}</div>')
    if areas:
        nav += (f'<div class="nav-item">{trigger("Service Areas", "m-area")}'
                f'{mega(areas[:18], "m-area", "/service-areas/", "All Service Areas", " mega--areas")}</div>')
    if guides:
        nav += (f'<div class="nav-item">{trigger("Guides", "m-guide")}'
                f'{mega(guides, "m-guide", "/guides/", "All Guides")}</div>')
    # About / Contact promoted to real navbar links (visible on desktop and in the mobile menu)
    nav += '<a href="/about/">About</a><a href="/contact/">Contact</a>'
    nav += '<a class="nav-quote" href="/request-a-quote/">Request a Quote</a>'

    # The top strip only earns its space when there is actually a number to show.
    tel = phone_link(t, with_icon=True)
    topbar = (f'<div class="top"><div class="wrap"><span>Serving {esc(t["city"])} &amp; the surrounding metro</span>'
              f'<span class="dot">&bull;</span><span>Same-day service available</span>'
              f'<span class="tsp"></span>{tel}</div></div>') if tel else ""

    return f"""{topbar}
<header class="site"><div class="wrap hd">
{brand_lockup(t)}
<button class="burger" aria-label="Menu" aria-expanded="false" aria-controls="navmain"><span></span><span></span><span></span></button>
<nav class="main" id="navmain" aria-label="Main">{nav}</nav>
<a class="btn btn--primary" href="/request-a-quote/">Free Quote</a>
</div></header><main id="main">"""

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
        # width/height must be the file's real dimensions or the browser reserves
        # the wrong box and the footer jumps as the image lands.
        lw, lh = logo_box(t, 128)
        logo = (f'<img class="gf-logo-img" src="/assets/logo-emblem.png" alt="{esc(t["brand"])}" '
                f'width="{lw}" height="{lh}" loading="lazy" decoding="async">')
    else:
        logo = f'<span class="gf-mark">{brand_chip(t, 30)}</span><span>{esc(t["brand"])}</span>'
    tel = phone_link(t)
    brand_block = (f'<div class="gf-brand"><a class="gf-logo" href="/">{logo}</a><p>{blurb}</p>'
                   f'<address class="gf-addr">{addr}{"<br>" + tel if tel else ""}</address></div>')
    # h3, not h4: the last heading before the footer is an h2, and jumping straight
    # to h4 was the one heading-level skip on every page.
    cols = (f'<div><h3>Services</h3>{services}</div><div><h3>Company</h3>{company}</div>'
            f'<div><h3>Service Areas</h3>{area_links}</div>')
    trust = (f'<div class="gf-trust">'
             f'<div>{icon("shield")}<span>Licensed &amp; fully insured</span></div>'
             f'<div>{icon("clock")}<span>Same-day service available</span></div>'
             f'<div>{icon("tag")}<span>Upfront, written pricing</span></div>'
             f'<div>{icon("star")}<span>Local crew, real reviews</span></div></div>')
    legal = (f'<div class="gf-legal"><span>&copy; {date.today().year} {esc(t["brand"])}. All rights reserved.</span>'
             f'<span>{addr}{" &middot; " + tel if tel else ""}</span></div>')
    js = '<script src="/assets/nav.js" defer></script>'
    # </main> closes the landmark opened at the end of header() -- every garage page is
    # head_html + header + <body content> + footer, so the pair always balances.
    return (f'</main><footer class="gfooter"><div class="gf-main"><div class="wrap">'
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
    # With no number on file the hero would otherwise lead with a dead "Call" button;
    # drop it and let the quote CTA carry the primary weight instead.
    call = call_cta(t) if has_phone(t) else ""
    qcls = "btn btn--ghost" if call else "btn btn--primary"
    quote = f'<a class="{qcls}" href="/request-a-quote/">Get a Free Quote</a>'
    eyebrow = f'<p class="eyebrow">{esc(t["city"])}, {esc(t["st"])} &middot; Garage Door Service</p>'
    leadh = f'<p class="lead">{esc(lead)}</p>'
    chips = ('<ul class="chips">'
             f'<li>{icon("check")}Same-day service</li><li>{icon("check")}Licensed &amp; insured</li>'
             f'<li>{icon("check")}Upfront pricing</li><li>{icon("check")}Local crew</li></ul>')
    copy = f'<div class="hero__copy">{eyebrow}<h1>{esc(h1)}</h1>{leadh}<div class="cta">{call}{quote}</div>{chips}</div>'
    src = f'/assets/photos/{img}'
    alt = f'Garage door service in {esc(t["city"])}, {esc(t["st"])}'
    badge = f'<div class="hero__badge">{icon("shield")}<div><b>Licensed</b><span>&amp; insured crew</span></div></div>'
    media = f'<div class="hero__media"><img src="{src}" alt="{alt}" width="1200" height="900" fetchpriority="high" decoding="async">{badge}</div>'

    if variant == "split-left":
        return f'<section class="hero hero--split hero--left"><div class="wrap">{media}{copy}</div></section>'
    if variant == "stacked":
        wide = f'<div class="hero__media--wide"><img src="{src}" alt="{alt}" width="1600" height="900" fetchpriority="high" decoding="async"></div>'
        return f'<section class="hero hero--stacked"><div class="wrap">{copy}{wide}</div></section>'
    if variant == "center":
        return f'<section class="hero hero--center" style="--hero-bg:url({src})"><div class="wrap">{copy}</div></section>'
    if variant == "overlap":
        return (f'<section class="hero hero--overlap"><div class="hero__bgimg"><img src="{src}" alt="{alt}" width="1600" height="900" fetchpriority="high" decoding="async"></div>'
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
            f'<img src="/assets/photos/{img}" alt="{title} in {esc(t["city"])}" width="1200" height="900" loading="lazy" decoding="async">'
            f'<div class="svc-card__ic">{icon(ic)}</div>'
            f'<div class="svc-card__b"><h3>{title}</h3><p>{blurb}</p>'
            f'<span class="more">Learn more {icon("arrow")}</span></div></a>'
            for ic, title, blurb, url, img in items)
        grid_cls = "svc-grid"
    else:
        cards = "".join(
            f'<a class="scard" href="{url}">'
            f'<img src="/assets/photos/{img}" alt="{title} in {esc(t["city"])}" width="1200" height="900" loading="lazy" decoding="async">'
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

def how_it_works(t, intro=""):
    """`intro` is the city's own 'how_a_call_goes' copy from the home JSON when the
    site opts into the expanded homepage; the 3 steps below stay generic."""
    style = t["layout"]["steps"]
    lead = f'<div class="prose prose--tight">{render_body(intro)}</div>' if intro else ""
    return (f'<section class="sec sec--soft"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">How It Works</p><h2>Getting your door fixed is simple</h2>{lead}</div>'
            f'<div class="steps steps--{style}">'
            f'<div class="step"><div class="step__b"><h3>Tell us the symptom</h3><p>Call or request a quote and describe what the door is doing — noise, off-track, won\'t open.</p></div></div>'
            f'<div class="step"><div class="step__b"><h3>On-site diagnosis</h3><p>A tech inspects the springs, tracks, opener and panels and gives you a written price first.</p></div></div>'
            f'<div class="step"><div class="step__b"><h3>Repaired or installed</h3><p>Most repairs are done on the same visit; installs are scheduled around you.</p></div></div>'
            f'</div></div></section>')

# ---- showcase-variant sections (inspired by the reference design) ----
def stats_band(t, pages=None):
    """Credibility row. Uses the site's configured 'stats' ([number, label] pairs) when
    present; otherwise falls back to figures counted from what this site actually
    contains — services built, areas covered, guides written. Still never fabricates:
    there is deliberately no population or "jobs completed" number, because neither is
    in the data and both would have to be invented."""
    stats = t.get("stats") or []
    if not stats and pages:
        counted = [(len([p for p in pages.values() if p["cat"] == c]), label)
                   for c, label in (("service", "Services offered"),
                                    ("area", "Areas covered"),
                                    ("guide", "Guides written"))]
        stats = [(str(n), l) for n, l in counted if n]
        if stats:
            stats.append(("Diagnosis", "first, then the fix"))
    if not stats:
        return ""
    cells = "".join(f'<div class="stat"><b>{esc(str(n))}</b><span>{esc(str(l))}</span></div>' for n, l in stats)
    return f'<div class="stats">{cells}</div>'

def why_us_split(t, pages=None):
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
            f'<div class="whyx__img"><img src="/assets/photos/{img}" alt="Garage door service in {esc(t["city"])}" width="1200" height="900" loading="lazy" decoding="async">{badge}</div>'
            f'</div>{stats_band(t, pages)}</div></section>')

def _svg_mail():
    return ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>')

def _svg_pin():
    return ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>')

def contact_band(t):
    """Homepage 'Book Your Service Today' block: call / hours / email / service area."""
    hours = t.get("hours") or "Mon-Sat, 7am-7pm"
    phone_cell = phone_link(t) or '<a href="/request-a-quote/">Request a callback</a>'
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
            f'{call_cta(t, "btn btn--ghost", label="Call now") if has_phone(t) else ""}</div>'
            f'</div></section>')

# ---- expanded-homepage sections --------------------------------------------
# Ten sections that take the homepage from 8 body blocks to 18. Four of them render
# the per-city copy that already ships in every home JSON (`sections[]`) and that the
# original homepage silently discarded; the rest are static but niche-true -- no
# invented reviews, counts, awards or certifications.
def _first_url(pages, cands, fallback="/request-a-quote/"):
    """First candidate URL this site actually has, else a page that always exists."""
    for u in cands:
        if u in pages:
            return u
    return fallback

def _home_sec(home, *keys):
    """Body text of the first home JSON section whose h2 matches one of `keys`
    (snake_case). Keys are tried in order, so the real content shape wins and the
    seeded demo shape (`what_we_do` / `why_local_matters`) is a fallback. Returns ""
    when a city has none of them, and the calling section then renders nothing."""
    for k in keys:
        for s in (home or {}).get("sections", []):
            if slugify(s.get("h2", "")).replace("-", "_") == k:
                return s.get("body", "")
    return ""

def symptom_finder(t, pages):
    """Symptom chips -> the page that explains that symptom. Pure internal linking:
    every chip resolves against pages this site really has."""
    chips = "".join(f'<a class="sym" href="{_first_url(pages, cands)}">'
                    f'<span>{esc(label)}</span>{icon("arrow")}</a>'
                    for label, cands in SYMPTOMS)
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">Start Here</p><h2>What is your door doing?</h2>'
            f'<p>Pick the closest symptom and read what usually causes it - or call and describe it to a tech.</p></div>'
            f'<div class="syms">{chips}</div></div></section>')

def local_context(t, home):
    """City-specific housing/climate copy from the home JSON, beside a photo."""
    body = _home_sec(home, "the_area_and_its_housing", "why_local_matters")
    if not body:
        return ""
    img = t.get("ctx_img") or (t.get("card_imgs") or CARD_IMGS)[-1]
    return (f'<section class="sec sec--soft"><div class="wrap"><div class="ctx">'
            f'<div class="ctx__copy"><p class="eyebrow">Local Conditions</p>'
            f'<h2>Garage doors in {esc(t["city"])}, {esc(t["st"])}</h2>{render_body(body)}</div>'
            f'<div class="ctx__img"><img src="/assets/photos/{img}" '
            f'alt="Garage door work in {esc(t["city"])}, {esc(t["st"])}" width="1200" height="900" loading="lazy" decoding="async"></div>'
            f'</div></div></section>')

def fix_most_here(t, home):
    """City-specific 'what actually breaks around here' copy from the home JSON."""
    body = _home_sec(home, "what_we_fix_most_here")
    if not body:
        return ""
    return (f'<section class="sec sec--soft"><div class="wrap"><div class="prose">'
            f'<p class="eyebrow">On The Trucks</p><h2>What we fix most in {esc(t["city"])}</h2>'
            f'{render_body(body)}</div></div></section>')

def repair_vs_replace(t):
    rep = "".join(f'<li>{icon("check")}{esc(s)}</li>' for s in REPAIR_SIGNS)
    rpl = "".join(f'<li>{icon("check")}{esc(s)}</li>' for s in REPLACE_SIGNS)
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">Straight Answer</p><h2>Repair it, or replace it?</h2>'
            f'<p>Nobody should be sold a whole new door for a broken spring. Here is how the call actually gets made.</p></div>'
            f'<div class="rvr">'
            f'<div class="rvr__c"><h3>{icon("tag")}Repair usually wins when</h3><ul>{rep}</ul></div>'
            f'<div class="rvr__c rvr__c--alt"><h3>{icon("calendar")}Replacement usually wins when</h3><ul>{rpl}</ul></div>'
            f'</div></div></section>')

def door_types(t, pages):
    imgs = t.get("door_imgs") or t.get("card_imgs") or CARD_IMGS
    tiles = "".join(f'<article class="dt">'
                    f'<img src="/assets/photos/{imgs[i % len(imgs)]}" '
                    f'alt="{esc(name)} garage door in {esc(t["city"])}" width="1200" height="900" loading="lazy" decoding="async">'
                    f'<div class="dt__b"><h3>{esc(name)}</h3><p>{esc(blurb)}</p></div></article>'
                    for i, (name, blurb) in enumerate(DOOR_TYPES))
    url = _first_url(pages, ["/services/garage-door-installation/", "/services/"])
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">New Doors</p><h2>Door styles we install</h2>'
            f'<p>Measured to your opening and specified for the local heat load - not whatever happens to be on the truck.</p></div>'
            f'<div class="dts">{tiles}</div>'
            f'<div class="sec-cta"><a class="btn btn--primary" href="{url}">Talk about a new door</a></div>'
            f'</div></section>')

def emergency_strip(t):
    ask = "call" if has_phone(t) else "send it through"
    return (f'<section class="emerg"><div class="wrap emerg__in">'
            f'<div class="emerg__t">{icon("clock")}<div>'
            f'<b>Door stuck open, or a spring already gone?</b>'
            f'<span>Neither one waits for an appointment window - {ask} and we will move the job up the list.</span>'
            f'</div></div>'
            f'{call_cta(t, "btn", quote_label="Request urgent service")}'
            f'</div></section>')

def maintenance_tips(t):
    cells = "".join(f'<div class="tip"><div class="tip__ic">{icon(ic)}</div>'
                    f'<h3>{esc(h)}</h3><p>{esc(d)}</p></div>' for ic, h, d in MAINT_TIPS)
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">Make It Last</p><h2>Four checks that prevent most callouts</h2>'
            f'<p>None of these need tools, and all four take under a minute.</p></div>'
            f'<div class="tips">{cells}</div></div></section>')

def safety_callout(t):
    return (f'<section class="sec sec--soft"><div class="wrap"><div class="safety">'
            f'<div class="safety__ic">{icon("shield")}</div><div class="safety__b">'
            f'<p class="eyebrow">Please Read</p><h2>The one job we ask you not to do yourself</h2>'
            f'<p>A torsion spring stores enough energy to lift a door that weighs about as much as you do, '
            f'and it lets go of all of it the moment a winding bar slips. Spring replacement is the most '
            f'common source of serious injury in this trade, and it is the one repair we tell every '
            f'homeowner in {esc(t["city"])} to hand over.</p>'
            f'<p>Plenty of the rest is fair game for a confident DIYer. This one is not.</p>'
            f'</div></div></div></section>')

def guides_teaser(t, pages):
    """Three guide pages on the homepage - the content already exists and was only
    reachable from the nav and the /guides/ index."""
    guides = [p for u, p in pages.items() if p["cat"] == "guide"][:3]
    if not guides:
        return ""
    inner = t.get("inner_imgs") or {}
    cards = ""
    for p in guides:
        img = inner.get(p["url"]) or INNER_IMGS[_stable_idx(p["slug"] or p["url"], len(INNER_IMGS))]
        cards += (f'<a class="gcard" href="{p["url"]}">'
                  f'<img src="/assets/photos/{img}" alt="{esc(area_label(p))}" width="1200" height="900" loading="lazy" decoding="async">'
                  f'<div class="gcard__b"><h3>{esc(area_label(p))}</h3>'
                  f'<p>{esc((p["meta"] or "").split(".")[0])}</p>'
                  f'<span class="more">Read the guide {icon("arrow")}</span></div></a>')
    return (f'<section class="sec sec--soft"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">Good to Know</p><h2>Plain-English garage door guides</h2>'
            f'<p>What actually goes wrong, why it goes wrong, and what it takes to put right.</p></div>'
            f'<div class="gcards">{cards}</div>'
            f'<div class="sec-cta"><a class="btn btn--outline" href="/guides/">All guides {icon("arrow")}</a></div>'
            f'</div></section>')

def areas_band(t, pages, prose=""):
    """`prose` is the city's own 'areas_we_cover' copy from the home JSON, which
    replaces the generic one-liner when the site opts into the expanded homepage."""
    areas = [p for u, p in pages.items() if p["cat"] == "area"]
    if not areas:
        return ""
    # Split into neighborhoods inside the city vs nearby communities where the content
    # distinguishes them (the nb-/sub- filename prefix, kept as page["kind"]). One flat
    # list reads as an undifferentiated keyword dump; two tiers match how someone
    # actually looks for their own street.
    nb = [p for p in areas if p.get("kind") == "nb"]
    sub = [p for p in areas if p.get("kind") == "sub"]
    chip = lambda p: f'<a href="{p["url"]}">{esc(area_label(p))}</a>'
    if nb and sub:
        grid = (f'<div class="areas-tier"><h3>{esc(t["city"])} neighborhoods</h3>'
                f'<div class="areas">{"".join(chip(p) for p in nb[:16])}</div></div>'
                f'<div class="areas-tier"><h3>Nearby communities</h3>'
                f'<div class="areas">{"".join(chip(p) for p in sub[:16])}'
                f'<a class="areas__all" href="/service-areas/">View all areas {icon("arrow")}</a></div></div>')
    else:
        grid = (f'<div class="areas">{"".join(chip(p) for p in areas[:16])}'
                f'<a class="areas__all" href="/service-areas/">View all areas {icon("arrow")}</a></div>')
    blurb = (f'<div class="prose prose--tight">{render_body(prose)}</div>' if prose else
             f'<p>{len(areas)} {esc(t["city"])}-area neighborhoods and communities we cover '
             f'&mdash; is your street on the list?</p>')
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">Where We Work</p><h2>Serving {esc(t["city"])} &amp; nearby communities</h2>'
            f'{blurb}</div>{grid}</div></section>')

def cta_band(t, heading=None):
    heading = heading or f"Need a garage door fixed in {t['city']}?"
    if has_phone(t):
        lead = "Call now or request a free quote — same-day service on most repairs, upfront written pricing."
        cta = call_cta(t) + '<a class="btn btn--ghost" href="/request-a-quote/">Request a Quote</a>'
    else:
        lead = "Send us the details and we will come back with a written price — same-day service on most repairs."
        cta = '<a class="btn btn--primary" href="/request-a-quote/">Request a Quote</a>'
    return (f'<section class="sec"><div class="wrap"><div class="cta-band"><h2>{esc(heading)}</h2>'
            f'<p>{lead}</p><div class="cta">{cta}</div></div></div></section>')

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
    # the expanded stack already has a soft band either side of the FAQ, so it runs plain there
    faq_cls = "sec" if uses_expanded(t) else "sec sec--soft"
    faq_html = (f'<section class="{faq_cls}"><div class="wrap"><div class="sec-head">'
                f'<p class="eyebrow">Good to Know</p><h2>Frequently asked questions</h2></div>'
                f'<div class="faq">{faq_accordion(faqs)}</div></div></section>')
    title = seo_title(home_title(t, pages))
    desc = (home["meta"] if home else "") or lead
    schemas = [org_schema(t), faq_schema(faqs)]
    hero_img = t.get("hero_img") or HERO_IMG
    top = (head_html(t, title, desc, "/", schemas, og_image=hero_img) + header(t, pages)
           + hero(t, h1, lead, img=hero_img) + trust_bar())
    if uses_expanded(t):
        # DEFAULT stack: 15 body sections after the hero + trust bar. Four of them
        # (local_context, fix_most_here, the how-it-works intro and the areas prose)
        # render the per-city copy from the home JSON, so no two cities share this
        # page's text; each renders nothing if that city's JSON lacks the section.
        # contact_band() is deliberately not here -- it duplicated the closing CTA.
        mid = (services_grid(t, pages)                                  # soft
               + symptom_finder(t, pages)                               # plain
               + local_context(t, home)                                 # soft   <- city copy
               + why_us_split(t, pages)                                        # plain
               + fix_most_here(t, home)                                 # soft   <- city copy
               + repair_vs_replace(t)                                   # plain
               + how_it_works(t, _home_sec(home, "how_a_call_goes"))     # soft   <- city copy
               + door_types(t, pages)                                   # plain
               + emergency_strip(t)                                     # accent
               + maintenance_tips(t)                                    # plain
               + safety_callout(t)                                      # soft
               + areas_band(t, pages, _home_sec(home, "areas_we_cover"))  # plain <- city copy
               + guides_teaser(t, pages)                                # soft
               + faq_html                                               # plain
               + cta_band(t))                                           # plain
    elif t.get("home") == "showcase":
        # contact_band() helper kept in code for reuse, but not rendered on the page
        mid = (why_us_split(t, pages) + services_grid(t, pages) + how_it_works(t)
               + areas_band(t, pages) + faq_html + cta_band(t))
    else:
        # "classic": the original 8-section stack, kept for sites that want it short
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
            parts.append(f'<img src="/assets/photos/{img}" alt="{esc(h1)}" width="1200" height="900" loading="lazy" decoding="async">')
    if p["faq"]:
        parts.append(f'<h2 id="faq">Frequently asked questions</h2><div class="faq">{faq_accordion(p["faq"])}</div>')

    label = {"service": "Services", "area": "Service Areas", "guide": "Guides"}.get(p["cat"], "")
    parent = {"service": "/services/", "area": "/service-areas/", "guide": "/guides/"}.get(p["cat"], "/")
    crumb = f'<div class="crumb"><a href="/">Home</a> › <a href="{parent}">{label}</a> › {esc(h1)}</div>'
    aside = (f'<aside class="aside"><div class="qcard">{icon("phone")}<h3>Get a free quote</h3>'
             f'<p>Fast answers and real pricing for {esc(t["city"])} garage door work.</p>'
             f'{phone_link(t, cls="tel")}'
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

# ---------------------------------------------------------------- page FX
# Smooth scrolling, scroll-reveal on content, and a back-to-top button. Shared by all
# ten designs and injected by write(), for the same reason the action bar is: the
# scroll-reveal previously lived in the default design's nav.js, so the nine alt
# designs silently had no entrance animation at all.
#
# Three things this must not get wrong:
#   1. prefers-reduced-motion is honoured for BOTH the reveal and the smooth scroll.
#      Motion sensitivity is the whole reason that media query exists.
#   2. Content is never hidden unless JS is actually running. The reveal styles are
#      gated on `html.anim`, a class set by an inline <head> script, so with JS off or
#      broken nothing is ever stuck at opacity:0.
#   3. There is a timeout fallback, so a failed IntersectionObserver cannot leave a
#      page blank.

def fx_css(t):
    """Per-site so the back-to-top button picks up the site's brand colour."""
    return ("""
html{scroll-behavior:smooth;scroll-padding-top:96px}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media (prefers-reduced-motion:no-preference){
  html.anim .fx-r{opacity:0;transform:translateY(22px);
    transition:opacity .6s ease,transform .7s cubic-bezier(.2,.75,.25,1)}
  html.anim .fx-r.in{opacity:1;transform:none}
}
.totop{position:fixed;right:18px;bottom:18px;z-index:92;width:46px;height:46px;
  border:0;border-radius:50%;cursor:pointer;display:grid;place-items:center;
  background:__P__;color:#fff;box-shadow:0 6px 20px rgba(15,23,42,.30);
  opacity:0;visibility:hidden;transform:translateY(10px);
  transition:opacity .25s,transform .25s,visibility .25s}
.totop.show{opacity:1;visibility:visible;transform:none}
.totop:hover{background:__PD__}
.totop svg{width:20px;height:20px;display:block}
/* clear the mobile action bar when the page has one */
@media(max-width:__BP__px){
  .totop{right:14px;bottom:calc(16px + env(safe-area-inset-bottom,0px))}
  body:has(.abar) .totop{bottom:calc(88px + env(safe-area-inset-bottom,0px))}
}
"""
            .replace("__BP__", str(ACTIONBAR_BP))
            .replace("__PD__", t.get("pd", "#0b1626"))
            .replace("__P__", t.get("p", "#12213a")))


TOTOP_HTML = ('<button class="totop" type="button" aria-label="Back to top">'
              '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">'
              '<path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" stroke-width="2.2" '
              'stroke-linecap="round" stroke-linejoin="round"/></svg></button>')

FX_JS = """<script>(function(){
 var root=document.documentElement;
 var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;

 // ---- back to top
 var btn=document.querySelector('.totop');
 if(btn){
   var onScroll=function(){
     if((window.pageYOffset||root.scrollTop)>600)btn.classList.add('show');
     else btn.classList.remove('show');
   };
   window.addEventListener('scroll',onScroll,{passive:true});onScroll();
   btn.addEventListener('click',function(){
     window.scrollTo({top:0,behavior:reduce?'auto':'smooth'});
     // move focus to the top of the document, or a keyboard user is left mid-page
     var skip=document.querySelector('.skip');if(skip)skip.focus({preventScroll:true});
   });
 }

 // ---- scroll reveal
 if(!root.classList.contains('anim')||reduce) return;
 var sel=[
   // default "garage" design
   '.sec-head','.scard','.feat','.step','.pricewrap','.areas a','.cta-band','.faq details',
   '.article .body>h2','.article .body>h3','.article .body>p','.article .body>ul',
   '.article .body>ol','.article .body>.tw','.article .body>.faq','.article .body>img','.aside',
   // shared section blocks + page skeleton used by the alt designs
   '.hb-wrap>h2','.hb-svc','.hb-step','.hb-sig','.hb-guide','.hb-faq','.hb-areas a',
   '.hb--cta .hb-wrap','.pg-body>h2','.pg-body>h3','.pg-body>p','.pg-body>ul','.pg-body>ol',
   '.pg-body>img','.pg-body>details','.pg-aside','.pg-row',
   // ironclad / nimbus keep their own section markup
   '.svc__row','.tile','.tl','.q','.bubble'
 ].join(',');
 var els=[].slice.call(document.querySelectorAll(sel));
 if(!els.length) return;
 els.forEach(function(el){el.classList.add('fx-r')});
 // stagger within a grid or list so rows arrive in sequence, not all at once
 [].forEach.call(document.querySelectorAll(
     '.grid,.steps,.areas,.faq,.hb-svcs,.hb-steps,.hb-sigs,.hb-guides,.hb-areas,.hb-faqs,.tiles'),
   function(g){var i=0;[].forEach.call(g.children,function(c){
     if(c.classList.contains('fx-r')){c.style.transitionDelay=(Math.min(i,6)*80)+'ms';i++;}});});
 function showAll(){els.forEach(function(el){el.classList.add('in')});}
 if(!('IntersectionObserver' in window)){showAll();return;}
 var io=new IntersectionObserver(function(ents){
   ents.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});
 },{threshold:0.08,rootMargin:'0px 0px -5% 0px'});
 els.forEach(function(el){io.observe(el)});
 // safety net: never leave content hidden if the observer never fires
 setTimeout(showAll,2600);
})();</script>"""

# Sets the gate class before first paint, so revealed content never flashes visible
# then hides. Only added when the design's own <head> has not done it already.
FX_HEAD = "<script>document.documentElement.classList.add('anim')</script>"


# ---------------------------------------------------------------- mobile action bar
# A fixed call/quote bar under 1024px. Injected by write() for every page of every
# design rather than added to each renderer, so no design can ship without it and none
# can ship two.
ACTIONBAR_BP = 1024

def action_bar(t, url):
    """Sticky bottom call/quote bar, or "" when it would add nothing.

    The call button follows the same rule as every other call affordance here: it only
    exists when there is a real number (has_phone), so no site renders a `tel:` link
    that dials nothing. On /request-a-quote/ the quote button is dropped -- linking a
    page to itself is not an action -- which means a phone-less site gets no bar there
    at all."""
    on_quote = url.rstrip("/") == "/request-a-quote"
    call = (f'<a class="abar__btn abar__btn--call" href="tel:{t["tel"]}">'
            f'{icon("phone")}<span>Call now</span></a>') if has_phone(t) else ""
    quote = ("" if on_quote else
             f'<a class="abar__btn abar__btn--quote" href="/request-a-quote/">'
             f'{_svg_mail()}<span>Get a quote</span></a>')
    if not (call or quote):
        return ""
    return (f'<div class="abar" role="group" aria-label="Contact {esc(t["brand"])}">'
            f'{call}{quote}</div>')

def actionbar_css(t):
    """Per-site so the bar picks up that site's brand colours; the ten designs declare
    their palettes under different variable names, so nothing here relies on --p/--accent
    resolving to anything."""
    return ("""
.abar{display:none}
@media(max-width:__BP__px){
  .abar{display:flex;gap:10px;position:fixed;left:0;right:0;bottom:0;z-index:95;
    padding:10px 14px;padding-bottom:calc(10px + env(safe-area-inset-bottom,0px));
    background:rgba(255,255,255,.97);backdrop-filter:blur(10px);
    border-top:1px solid rgba(15,23,42,.14);box-shadow:0 -6px 22px rgba(15,23,42,.14)}
  /* the buttons share the width evenly, but stop growing on a tablet where a
     half-viewport-wide button just looks broken */
  .abar__btn{flex:1 1 0;min-width:0;max-width:340px}
  .abar{justify-content:center}
  .abar__btn{display:flex;align-items:center;justify-content:center;gap:9px;
    min-height:52px;padding:0 14px;border-radius:12px;text-decoration:none;
    font-weight:700;font-size:1rem;line-height:1.1;text-align:center}
  .abar__btn svg{width:19px;height:19px;flex:0 0 auto}
  .abar__btn--call{background:__P__;color:#fff}
  .abar__btn--quote{background:__ACCENT__;color:__ONACCENT__}
  /* keep the bar from sitting on top of the last of the footer */
  body{padding-bottom:calc(74px + env(safe-area-inset-bottom,0px))}
}
@media(max-width:__BP__px) and (prefers-color-scheme:dark){
  .abar{background:rgba(255,255,255,.97)}
}
"""
            .replace("__BP__", str(ACTIONBAR_BP))
            .replace("__P__", t.get("p", "#12213a"))
            .replace("__ACCENT__", t.get("accent", "#c2703a"))
            .replace("__ONACCENT__", t.get("on_accent", "#ffffff")))


SERVICE_OPTIONS = ["Garage door repair", "New door installation", "Spring replacement",
                   "Opener repair or replacement", "Off-track door or cable",
                   "Service / tune-up", "Something else"]

def quote_form(t):
    """The site's lead-capture form. Native HTML: no JS required, works on any host,
    and POSTs to whatever `form_action` names.

    The form always renders, so the quote page is never a dead end and the layout is
    reviewable before an endpoint exists. Until `form_action` is set the form is
    *inert*: it carries no action, and a submit shows an inline notice instead of
    posting. That is deliberate -- a form that silently POSTs into the void looks
    identical to a working one while dropping every lead. Set `form_action` (per site,
    or once in the `defaults` block of config/sites.json) and the same markup becomes
    live with no other change."""
    action = (t.get("form_action") or "").strip()
    live = bool(action)
    opts = "".join(f'<option>{esc(o)}</option>' for o in SERVICE_OPTIONS)
    city = esc(f'{t["city"]}, {t["st"]}')
    attrs = f' method="post" action="{esc(action)}"' if live else ' data-unconfigured="1"'
    return (f'<form class="qform"{attrs} novalidate>'
            # Identify which of the ~1000 domains a submission came from.
            f'<input type="hidden" name="site" value="{esc(t["domain"])}">'
            f'<input type="hidden" name="city" value="{city}">'
            # Honeypot: bots fill it, humans never see it. Reject on the receiving end.
            f'<div class="qform__hp" aria-hidden="true"><label for="q-company">Company</label>'
            f'<input id="q-company" name="company" type="text" tabindex="-1" autocomplete="off"></div>'
            f'<div class="qform__grid">'
            f'<div class="qform__f"><label for="q-name">Your name<span class="req">*</span></label>'
            f'<input id="q-name" name="name" type="text" autocomplete="name" required></div>'
            f'<div class="qform__f"><label for="q-phone">Phone<span class="req">*</span></label>'
            f'<input id="q-phone" name="phone" type="tel" autocomplete="tel" required></div>'
            f'<div class="qform__f"><label for="q-email">Email</label>'
            f'<input id="q-email" name="email" type="email" autocomplete="email"></div>'
            f'<div class="qform__f"><label for="q-zip">Service address or ZIP</label>'
            f'<input id="q-zip" name="address" type="text" autocomplete="street-address"></div>'
            f'<div class="qform__f qform__f--wide"><label for="q-service">What do you need?</label>'
            f'<select id="q-service" name="service">{opts}</select></div>'
            f'<div class="qform__f qform__f--wide"><label for="q-notes">Tell us what the door is doing</label>'
            f'<textarea id="q-notes" name="notes" '
            f'placeholder="e.g. it opens about a foot then stops, and there is a loud bang from the spring"></textarea></div>'
            f'</div>'
            f'<div class="qform__foot"><button class="btn btn--primary" type="submit">Request my free quote</button>'
            f'<p class="qform__note">No obligation. We use your details only to quote this job.</p>'
            f'<p class="qform__pending" role="status" hidden>This form is not connected to an inbox yet. '
            f'Set <code>form_action</code> in config/sites.json to start receiving these.</p></div>'
            + ("" if live else
               '<script>(function(){var f=document.currentScript.parentNode;'
               'f.addEventListener("submit",function(e){e.preventDefault();'
               'var n=f.querySelector(".qform__pending");if(n)n.hidden=false;});})();</script>')
            + '</form>')

def trust_page(t, pages, url, h1, blocks, is_quote=False):
    parts = "".join(f'<h2>{esc(h)}</h2><p>{esc(b)}</p>' for h, b in blocks)
    crumb = f'<div class="crumb"><a href="/">Home</a> › {esc(h1)}</div>'
    tel = phone_link(t, cls="tel")
    aside = (f'<aside class="aside"><div class="qcard">{icon("phone")}<h3>Talk to us</h3>'
             f'<p>Garage door help in {esc(t["city"])}, {esc(t["st"])}.</p>{tel}'
             f'<a class="btn btn--primary" href="/request-a-quote/">Request a Quote</a></div></aside>')

    # The quote page leads with the form itself; everything else stays prose-first.
    # A configured GHL embed wins over the native form; otherwise the native form
    # always renders (inert until form_action is set -- see quote_form). This used to
    # test `not form` first, which now that the form always renders would have meant
    # the GHL embed could never appear.
    lead = ""
    if is_quote:
        if t.get("ghl_form_id"):
            from build_site import quote_embed
            lead = quote_embed(t["ghl_form_id"])
        else:
            side = (# h2, not h3: this card sits directly under the page h1. It only ever rendered
                    # when a form endpoint was configured, so the level skip it introduces
                    # surfaced the moment the form started rendering unconditionally.
                    f'<div class="qform__side"><div class="qcard">{icon("clock")}<h2>What happens next</h2>'
                    f'<p>We read every request the same day and come back with a written price '
                    f'— not a range, and no visit needed for most repairs.</p>{tel}</div></div>')
            lead = f'<div class="wrap"><div class="quote-lead">{quote_form(t)}{side}</div></div>'

    body = (f'<section class="page-hero"><div class="wrap">{crumb}<h1>{esc(h1)}</h1></div></section>{lead}'
            f'<div class="wrap"><div class="article"><div class="body">{parts}</div>{aside}</div></div>'
            + cta_band(t))
    schemas = [org_schema(t), breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (head_html(t, seo_title(f"{h1} | {t['brand']}"), f"{h1} — {t['brand']}, {t['city']}, {t['st']}.", url, schemas,
                       og_image=t.get("hero_img") or HERO_IMG)
            + header(t, pages) + body + footer(t, pages) + "</body></html>")

# ---------------------------------------------------------------- renderer dispatch
# The default "garage" design is the module functions above. Alternate full designs
# (ironclad / volt / nimbus) live in templates.py and expose the same interface.
GARAGE = {"css": lambda t: css(t) + GD_CSS + QFORM_CSS + actionbar_css(t) + fx_css(t)
                           + VARIANT_CSS + type_css(t), "navjs": NAVJS,
          "home": lambda t, pages: home_page(t, pages),
          "inner": lambda t, p, pages: inner_page(t, p, pages),
          "index": lambda t, pages, cat, url, h1, eb, bl: index_page(t, pages, cat, url, h1, eb, bl),
          "trust": lambda t, pages, url, h1, blocks, q=False: trust_page(t, pages, url, h1, blocks, q)}

def get_renderer(t):
    name = site_design(t)
    if name and name != "garage":
        import sys, templates
        templates.H = sys.modules[__name__]          # give templates access to shared helpers
        r = templates.REGISTRY.get(name)
        if r:
            return r
        print(f"  ! unknown template '{name}' -> using garage")
    return GARAGE

# ---------------------------------------------------------------- build
def write(out, url, htmlstr, t=None):
    htmlstr = clean_text(htmlstr)  # sweep any hardcoded typographic chars from the assembled page
    # The mobile action bar and the page FX go in here, not in the renderers: ten
    # designs x five page types is fifty places to forget them, and every page ends
    # with the same </body>.
    if t is not None:
        # gate class must be set before first paint, or revealed content flashes
        if "classList.add('anim')" not in htmlstr:
            htmlstr = htmlstr.replace("</head>", FX_HEAD + "</head>", 1)
        tail = action_bar(t, url) + TOTOP_HTML + FX_JS
        htmlstr = htmlstr.replace("</body>", tail + "</body>", 1)
    path = os.path.join(out, url.strip("/"), "index.html") if url != "/" else os.path.join(out, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(htmlstr)

def build():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    no_lead, built = [], 0
    for domain, t in SITES.items():
        if not os.path.isdir(os.path.join(CONTENT, t["content"])):
            print(f"  skip {domain}: content/{t['content']}/ not found (add content, then rebuild)")
            continue
        # A site with neither a phone number nor a form endpoint renders correctly but
        # gives a visitor no way to make contact. Worth saying out loud, per build.
        if not has_phone(t) and not (t.get("form_action") or t.get("ghl_form_id")):
            no_lead.append(domain)
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
        t["logo"] = dict(LOGO_INFO.get(domain) or {"kind": "mark"})
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
        (t["hero_img"], t["card_imgs"], t["inner_imgs"],
         t["door_imgs"], t["ctx_img"]) = select_photos(t, pages, photos)
        # inner content pages
        for url, p in pages.items():
            if p["cat"] == "home":
                continue
            write(out, url, R["inner"](t, p, pages), t)
        # homepage
        write(out, "/", R["home"](t, pages), t)
        # section index pages
        if any(p["cat"] == "service" for p in pages.values()):
            write(out, "/services/", R["index"](t, pages, "service", "/services/",
                  f"Garage Door Services in {t['city']}", "What We Do",
                  f"Repair, installation and service for garage doors across {t['city']} and nearby."), t)
        if any(p["cat"] == "area" for p in pages.values()):
            write(out, "/service-areas/", R["index"](t, pages, "area", "/service-areas/",
                  f"Service Areas Around {t['city']}", "Where We Work",
                  f"Neighborhoods and suburbs we cover across the {t['city']} metro."), t)
        if any(p["cat"] == "guide" for p in pages.values()):
            write(out, "/guides/", R["index"](t, pages, "guide", "/guides/",
                  "Garage Door Guides", "Good to Know",
                  "Plain-English answers about springs, openers, older doors and what a repair really involves."), t)
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
             f"Whether it's a door that won't open this morning or a replacement you've been putting off, {t['brand']} is one call away. {_reach(t)} for same-day service on most repairs, or request a written quote and we'll tell you honestly what your door needs - nothing more."),
        ]), t)
        write(out, "/contact/", R["trust"](t, pages, "/contact/", f"Contact {t['brand']}", [
            ("Get in touch", f"{_reach(t)} to reach {t['brand']} for garage door repair, service or a new-door quote in {t['city']}, {t['st']}."),
            ("Service area", f"We serve {t['city']} and the surrounding suburbs. Not sure if you're in range? Ask when you get in touch — we'll tell you straight.")]), t)
        write(out, "/request-a-quote/", R["trust"](t, pages, "/request-a-quote/", f"Request a Garage Door Quote in {t['city']}", [
            ("Tell us what the door is doing", f"Describe the problem — noise, off-track, a broken spring, or a door you want replaced — and we'll give you a written price. {_reach(t, form_first=True)}."),
            ("Fast, no-pressure quotes", "You get a real number, not a range, once we've seen the door. Same-day service is available on most repairs.")], True), t)

        # sitemap / robots
        urls = sorted(set(["/"] + [p["url"] for p in pages.values() if p["cat"] != "home"]
                          + ["/services/", "/service-areas/", "/guides/", "/about/", "/contact/", "/request-a-quote/"]))
        sm = "".join(f"<url><loc>https://{domain}{u}</loc><lastmod>{BUILD_DATE}</lastmod></url>" for u in urls)
        open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8").write(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
        open(os.path.join(out, "robots.txt"), "w", encoding="utf-8").write(
            f"User-agent: *\nAllow: /\nSitemap: https://{domain}/sitemap.xml\n")

        # Vercel config, written per site so `vercel deploy dist/<domain>` needs no
        # extra setup. It lives in dist/ (regenerated each build), not in the repo,
        # because build() rmtree's dist/ on every run.
        #
        # trailingSlash: every internal link the engine emits ends in "/" and each page
        # is a directory index, so this keeps "/services" and "/services/" from being
        # two URLs. No cleanUrls: that would strip the slash and fight the same links.
        #
        # Caching is deliberately conservative on CSS/JS: those filenames are NOT
        # content-hashed, so a long immutable max-age would serve a stale stylesheet
        # after the next deploy. Photos are cached longer -- their names are stable and
        # tied to the content that chose them.
        open(os.path.join(out, "vercel.json"), "w", encoding="utf-8").write(json.dumps({
            "$schema": "https://openapi.vercel.sh/vercel.json",
            "trailingSlash": True,
            "headers": [
                {"source": "/(.*)", "headers": [
                    {"key": "X-Content-Type-Options", "value": "nosniff"},
                    {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"},
                ]},
                {"source": "/assets/photos/(.*)", "headers": [
                    {"key": "Cache-Control", "value": "public, max-age=604800"},
                ]},
                {"source": "/assets/(.*).(css|js)", "headers": [
                    {"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"},
                ]},
            ],
        }, indent=2))
        built += 1
        print(f"  {domain}: {len(urls)} pages ({t['city']}, {t['st']})")
    print(f"Done -> {DIST}  ({built} sites)")
    if no_lead:
        print(f"\n  !! {len(no_lead)} of {built} built sites have NO way for a visitor to make contact:")
        print(f"     {', '.join(no_lead[:6])}{' ...' if len(no_lead) > 6 else ''}")
        print( '     Set "phone" per site, and/or a "form_action" endpoint (per site or in')
        print( '     the top-level "defaults" object of config/sites.json) before deploying.')

if __name__ == "__main__":
    print("Building garage-door sites...")
    build()
