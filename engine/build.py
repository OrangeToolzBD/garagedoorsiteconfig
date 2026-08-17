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
import os, re, sys, json, html, shutil, hashlib
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

# ---------------------------------------------------------------- copy decks
# Every string below the hero used to be a single hardcoded constant, so 1000
# sites shipped the same words. Measured: below-hero text was 81% similar at the
# median and two sites were 100.0% identical after swapping the city name.
#
# These decks hold authored ALTERNATIVES for each slot, picked per-domain by
# digest (same mechanism as BUTTON_STYLES). Rules for anything added here:
#
#   * Variants must be factually INTERCHANGEABLE -- the same claims in different
#     words and order. They are re-phrasings, not new promises. A site cannot
#     back up a claim just because the deck made one.
#   * Do not assert social proof (review counts, ratings, testimonials). The
#     sites have none, and the original "Local crew, real reviews" trust item
#     was already overstating it -- the replacements below drop that claim.
#   * ORDER IS APPEND-ONLY. Selection is digest % len(deck), so reordering
#     re-rolls every domain. Add new variants at the end.
#
# "{city}" is substituted with the escaped city name at render time.
COPY = {
    # ---- trust bar: 4 short proof points, each "<b>lead</b> tail"
    "trust": [
        [("clock", "<b>Same-day</b> service available"), ("shield", "Licensed &amp; <b>fully insured</b>"),
         ("tag", "<b>Upfront</b>, written pricing"), ("star", "<b>Local</b> crew, local vans")],
        [("clock", "Most repairs <b>done today</b>"), ("tag", "Written price <b>before we start</b>"),
         ("shield", "<b>Insured</b> techs, proper tools"), ("check", "One visit, <b>fixed properly</b>")],
        [("shield", "<b>Licensed</b> and insured"), ("clock", "<b>Same-day</b> slots most days"),
         ("check", "No <b>surprise</b> add-ons"), ("star", "Based <b>in {city}</b>")],
        [("tag", "<b>Flat pricing</b>, quoted on site"), ("clock", "Fast <b>callout windows</b>"),
         ("check", "Parts <b>sized to your door</b>"), ("shield", "Fully <b>insured work</b>")],
    ],
    # ---- services grid header: (eyebrow, h2, blurb)
    "services_head": [
        ("What We Do", "Garage door services in {city}",
         "From a snapped spring to a full door replacement — one local crew, upfront pricing."),
        ("Our Services", "What we fix around {city}",
         "Springs, openers, cables, panels and full replacements — quoted before the work starts."),
        ("The Work", "Garage door repair &amp; installation, {city}",
         "One crew for the whole job: diagnose it, price it in writing, then fix it."),
        ("Where We Help", "Every part of the door, {city}",
         "Whether it's the spring, the opener or the door itself, it's the same team either way."),
    ],
    # ---- service tiles. Catalogues vary in COUNT as well as wording: a fixed
    # 6-up grid is itself a fingerprint. The three real service slugs stay in
    # every catalogue so the tile links keep resolving to real pages.
    "tiles": [
        SERVICE_TILES,
        [("shield", "Spring Replacement", "Torsion and extension springs swapped safely — the one job never worth DIY-ing.", None),
         ("check", "Opener Not Working", "Chain, belt and screw-drive units, safety sensors and rolling-code remotes.", None),
         ("arrow", "Door Off Its Track", "Rollers re-seated, bent track straightened, frayed cables replaced and re-tensioned.", "garage-door-repair"),
         ("calendar", "New Doors Fitted", "Insulated steel and composite doors measured to your opening.", "garage-door-installation"),
         ("clock", "Annual Tune-Up", "Tension, rollers, hinges and sensor alignment — what keeps an older door quiet.", "garage-door-service")],
        [("arrow", "Emergency Door Repair", "Stuck open, stuck shut, or off the track — the calls that can't wait until next week.", "garage-door-repair"),
         ("calendar", "Door Replacement", "When the panels or track are past saving, a new insulated door sized to the opening.", "garage-door-installation"),
         ("clock", "Maintenance Visits", "Spring tension, roller wear and sensor alignment checked before they strand you.", "garage-door-service"),
         ("check", "Openers &amp; Remotes", "Motors, travel limits, safety eyes and rolling-code remotes reprogrammed.", None)],
        [("shield", "Repairs", "Snapped cables, bent panels, grinding openers and doors that won't seal.", "garage-door-repair"),
         ("clock", "Springs", "Torsion and extension springs replaced with parts rated for your door's weight.", None),
         ("check", "Service Calls", "A full check of tension, rollers, hinges and sensors on an ageing door.", "garage-door-service"),
         ("sparkle", "Openers", "Chain, belt and screw-drive openers repaired or replaced.", None),
         ("calendar", "Installations", "New insulated doors, measured, fitted and balanced.", "garage-door-installation"),
         ("arrow", "Track &amp; Cable", "Doors jumped off their track re-seated and re-tensioned properly.", None)],
    ],
    # ---- why-us: (eyebrow, h2) + 4 feature cells
    "why_head": [
        ("Why {city} Calls Us", "Straight answers, honest fixes"),
        ("What You Get", "No guesswork, no upsell"),
        ("How We Work", "Diagnosed properly, priced in writing"),
        ("Our Approach", "The door fixed once, not twice"),
    ],
    "why_items": [
        [("clock", "Same-day dispatch", "Most repair calls are handled the same or next day — springs and openers don't wait."),
         ("shield", "Licensed &amp; insured", "Trained techs, proper spring tools, and the insurance to back the work."),
         ("tag", "Upfront pricing", "A written quote at the door before any work starts — no surprise add-ons."),
         ("check", "Fixed right once", "We diagnose the actual cause, not just the symptom, so the door stays fixed.")],
        [("check", "A real diagnosis", "We find why the part failed, so you're not calling us again in four months."),
         ("tag", "The price you were quoted", "Written on site before the work begins, parts and labour together."),
         ("clock", "Quick to get to you", "Broken springs and stuck doors get priority over routine visits."),
         ("shield", "Properly equipped", "Correct spring bars and gauges, and the insurance behind the work.")],
        [("tag", "One number, in writing", "You approve a written price before a tool comes out of the van."),
         ("shield", "Insured and trained", "Torsion work needs the right bars and the right training. Our techs have both."),
         ("check", "Right-sized parts", "Springs matched to the door's actual weight, not whatever's on the shelf."),
         ("clock", "No weekend surcharge", "A Saturday call costs the same as a Tuesday one.")],
        [("clock", "We turn up when we say", "You get an arrival window, and a call if anything changes."),
         ("check", "Repair before replace", "If a spring is all it needs, that's all we'll sell you."),
         ("tag", "Nothing added quietly", "If we find something else, we stop and talk it through first."),
         ("shield", "Covered work", "Licensed, insured, and accountable for what we install.")],
    ],
    # ---- how-it-works: (eyebrow, h2) + 3 steps
    "steps_head": [
        ("How It Works", "Getting your door fixed is simple"),
        ("The Process", "Three steps, no runaround"),
        ("What Happens Next", "From your call to a working door"),
        ("Booking A Visit", "What to expect when you call"),
    ],
    "steps": [
        [("Tell us the symptom", "Call or request a quote and describe what the door is doing — noise, off-track, won't open."),
         ("On-site diagnosis", "A tech inspects the springs, tracks, opener and panels and gives you a written price first."),
         ("Repaired or installed", "Most repairs are done on the same visit; installs are scheduled around you.")],
        [("Describe what it's doing", "A grinding noise, a door that lifts crooked, an opener that hums — whatever you've noticed."),
         ("We look at the whole door", "Springs, cables, rollers, track and opener, because the obvious part isn't always the failed one."),
         ("You approve the price", "Written, itemised, before anything is touched. Most repairs finish the same visit.")],
        [("Book a window", "Tell us the problem and pick a time. Broken springs and stuck doors get priority."),
         ("Diagnosis on site", "The tech tests the balance and checks every moving part before quoting."),
         ("The work, done once", "Parts sized to your door, cleaned up after, and notes on what we found.")],
        [("Your call", "Two minutes on the phone is usually enough to know what we're walking into."),
         ("The inspection", "We check tension, cables, rollers and sensors, then write down the price."),
         ("The fix", "Same-visit on most repairs. Replacements get scheduled to suit you.")],
    ],
    # ---- service areas band: (eyebrow, h2, blurb)
    "areas_head": [
        ("Where We Work", "Serving {city} &amp; nearby communities",
         "Neighborhoods across the city and suburbs around the metro. Not sure if we reach you? Just ask."),
        ("Our Patch", "Covering {city} and the surrounding towns",
         "We work across the metro daily. If your street isn't listed, call and ask — it usually is."),
        ("Service Area", "{city} and everywhere around it",
         "Same crew, same pricing, whichever side of the city you're on."),
        ("Coverage", "Around {city}",
         "Neighborhoods in town and the suburbs beyond. Ask if you're not sure we reach you."),
    ],
    # ---- FAQ header: (eyebrow, h2)
    "faq_head": [
        ("Good to Know", "Frequently asked questions"),
        ("Common Questions", "Things people ask before booking"),
        ("Before You Call", "Questions we get a lot"),
        ("Answers", "What homeowners usually want to know"),
    ],
    # ---- CTA band: (h2, body-with-phone, body-without-phone)
    "cta": [
        ("Need a garage door fixed in {city}?",
         "Call now or request a free quote — same-day service on most repairs, upfront written pricing.",
         "Request a free quote — same-day service on most repairs, upfront written pricing."),
        ("Door stuck, noisy or off its track?",
         "Call and describe it, or send a quote request. Written pricing before any work starts.",
         "Send a quote request and describe what the door is doing. Written pricing before any work starts."),
        ("Let's get that {city} door working again",
         "One call and we'll tell you honestly what it needs. Most repairs finish the same visit.",
         "Tell us what it needs and we'll come back with an honest answer. Most repairs finish in one visit."),
        ("Book a {city} garage door visit",
         "Same-day slots on most repairs. Call for a time, or request a written quote.",
         "Same-day slots on most repairs. Request a written quote and we'll confirm a time."),
    ],
    # ---- sidebar quote card: (heading, subline, second-button label, its href)
    "qcard": [
        ("Get a free quote", "Fast answers and real pricing for {city} garage door work.",
         "Service Areas", "/service-areas/"),
        ("Talk to a tech", "Describe the door and we'll tell you what it needs.",
         "What We Do", "/services/"),
        ("Book a visit", "Most {city} repairs are done on the first visit.",
         "Service Areas", "/service-areas/"),
        ("Not sure what's wrong?", "That's normal. We diagnose it before quoting anything.",
         "Read The Guides", "/guides/"),
    ],
    # ---- full-bleed photo band: (heading, subline)
    "photo_band": [
        ("Real doors, real driveways", "Every job on this page was done by the crew that would come to yours."),
        ("The work, not stock promises", "Springs, openers and full replacements across {city} — done once, properly."),
        ("What a finished job looks like", "Balanced door, quiet track, and a written price you agreed to first."),
        ("On {city} driveways every week", "Same crew, same vans, same standard on every call."),
    ],
    # ---- split image + claim: (heading, subline, [checklist points])
    "split_feature": [
        ("Why the diagnosis matters more than the part",
         "Most repeat callouts happen because someone replaced the symptom instead of the cause.",
         ["We test the door balanced and under power",
          "You get the cause in writing, not a parts list",
          "Springs sized to your door's actual weight"]),
        ("A door is the biggest moving thing in your house",
         "It is also the one most people never think about until it stops.",
         ["Torsion work done with the correct bars",
          "Safety sensors checked and aligned every visit",
          "We tell you when a repair is not worth it"]),
        ("Repair first, replace only when it's honest",
         "If a spring is all it needs, that is all we will sell you.",
         ["No upsell on a door with life left in it",
          "Written price before a tool comes out",
          "Same crew from the quote to the fix"]),
        ("The parts that actually fail in {city}",
         "Local conditions decide what wears first, and we stock for that.",
         ["Parts matched to the local housing stock",
          "Most repairs finished on the first visit",
          "We say so when something has to be ordered"]),
    ],
    # ---- footer CTA strip: (heading, subline). Only the "cta" footer variant.
    "footer_cta": [
        ("Ready when your door isn't.", "Same-day slots on most repairs across {city}."),
        ("Get it looked at properly.", "A written price before any work starts — no surprises."),
        ("Talk to a {city} tech.", "Tell us what the door is doing and we'll tell you what it needs."),
        ("Book a visit.", "Most repairs are finished on the first visit."),
    ],
}
_COPY_ORDER = {k: list(range(len(v))) for k, v in COPY.items()}

def copy_deck(t, slot):
    """Pick this site's variant for a copy slot.

    A `copy` map in sites.json pins individual slots, e.g. {"cta": 2}; anything
    out of range warns and falls back to the digest pick rather than raising
    mid-build."""
    opts = COPY[slot]
    pin = (t.get("copy") or {}).get(slot)
    if pin is not None:
        if isinstance(pin, int) and 0 <= pin < len(opts):
            return opts[pin]
        print(f"  ! {t['domain']}: copy.{slot}={pin!r} out of range 0-{len(opts)-1}, using digest pick")
    return opts[_hash_idx(f"{t['domain']}|copy|{slot}", len(opts))]

def _city(s, t):
    return s.replace("{city}", esc(t["city"]))

def service_tiles(t):
    """This site's service catalogue. Catalogues differ in wording *and length* --
    a fixed 6-up grid is itself a fingerprint across a thousand sites."""
    return copy_deck(t, "tiles")

# license-free garage-door photos (Pexels), pooled in assets_shared/photos and copied per site
# -- last-resort fallback only; brand/photos/ (below) is the real photo source now.
PHOTO_POOL = [f"gd-{i}.jpg" for i in range(1, 10)]
HERO_IMG = "gd-4.jpg"
CARD_IMGS = ["gd-2.jpg", "gd-3.jpg", "gd-5.jpg", "gd-6.jpg", "gd-7.jpg", "gd-9.jpg"]
INNER_IMGS = ["gd-1.jpg", "gd-8.jpg", "gd-2.jpg", "gd-5.jpg", "gd-6.jpg"]

def _stable_idx(s, n):
    return (sum(ord(c) for c in s) % n) if n else 0

def _hash_idx(s, n):
    """Stable index for picking one of n options, safe for *independent* axes.

    _stable_idx sums character codes, so salting it ("<domain>|a" vs "<domain>|b")
    only shifts the sum by a constant and every axis derived from one domain moves
    in lockstep. Measured over the 1001 registered domains, three 4-option axes
    yielded 4 of 64 possible combinations that way; a real digest yields all 64.

    blake2s rather than md5: same distribution, but md5 raises "unsupported hash
    type" on FIPS-hardened hosts.

    Do not repurpose _stable_idx for this -- it drives photo selection, and
    templates.py reaches it as H._stable_idx."""
    if not n:
        return 0
    return int.from_bytes(hashlib.blake2s(s.encode("utf-8"), digest_size=8).digest(), "big") % n

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
GENERAL_PHOTO_DIRS = ["GD REPAIR", "GD INSTALLATION", "GD SERVICE", "GD MAINTENNANCE"]
_GAL_LABEL = {"GD REPAIR": "Repair", "GD INSTALLATION": "Installation",
              "GD SERVICE": "Service", "GD MAINTENNANCE": "Maintenance"}  # sic: source folder is misspelled
# the 5 guide-topic pools sit one level deeper than the service pools, under
# "GD GUIDE/". Without the prefix every lookup missed, all 50 guide photos were
# unreachable, and guide pages silently fell back to generic stock.
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

    # Gallery pool for the visual break sections. Drawn with a different salt
    # from the service tiles so the same shot doesn't appear twice on one page.
    gallery, gallery_cat = [], []
    for i, dirname in enumerate(GENERAL_PHOTO_DIRS):
        files = _brand_list(dirname)
        if not files:
            continue
        fn = files[_hash_idx(f'{t["domain"]}|gallery|{dirname}', len(files))]
        dest = f"gal-{i}.webp"
        if os.path.join(BRAND_PHOTOS, dirname, fn) in to_copy.values():
            continue
        to_copy[dest] = os.path.join(BRAND_PHOTOS, dirname, fn)
        gallery.append(dest)
        # the source folder is the ONLY truthful per-photo signal that exists --
        # no captions, titles or dates are recorded anywhere. "GD MAINTENNANCE"
        # is misspelled on disk; title-case the words we can trust.
        gallery_cat.append(_GAL_LABEL.get(dirname, "Garage door work"))

    for dest, src in to_copy.items():
        try:
            shutil.copy(src, os.path.join(photos_dir, dest))
        except FileNotFoundError:
            pass

    return hero_fn, card_imgs, inner_imgs, gallery, gallery_cat

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
.gf-trust svg{width:20px;height:20px;color:var(--accent-dk);flex:0 0 auto}
.gf-legal{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;padding-top:20px;font-size:.85rem;color:#7d8894}
.gf-legal a{color:#aeb9c5;text-decoration:none}

/* ---- footer variants -------------------------------------------------------
   config/layouts.json has assigned every one of the 1001 sites one of six
   footer values from the start, evenly distributed -- and build.py never read
   the field, so all 1000 shipped the same dark footer. The CSS that existed for
   this targeted `footer.site`, the porta-potty renderer's element, whose
   internal structure differs from .gfooter; these are garage-native. */
.gfooter.gf--dark{border-top:4px solid var(--accent)}
/* brand: the dark brand tint, so this variant also differs per theme */
.gfooter.gf--brand{background:var(--pd)}
.gfooter.gf--brand .gf-cols h4{color:var(--accent-dk)}
.gfooter.gf--brand .gf-cols,.gfooter.gf--brand .gf-trust{border-bottom-color:rgba(255,255,255,.18)}
/* light: full inversion onto the soft page tint */
.gfooter.gf--light{background:var(--soft);color:var(--muted);border-top:1px solid var(--line)}
.gfooter.gf--light .gf-cols h4,.gfooter.gf--light .gf-logo{color:var(--ink)}
.gfooter.gf--light .gf-cols a,.gfooter.gf--light .gf-brand p,
.gfooter.gf--light .gf-addr,.gfooter.gf--light .gf-trust div{color:var(--muted)}
.gfooter.gf--light .gf-cols a:hover{color:var(--p)}
.gfooter.gf--light .gf-addr a{color:var(--p)}
.gfooter.gf--light .gf-mark{background:var(--p)}
.gfooter.gf--light .gf-cols,.gfooter.gf--light .gf-trust{border-bottom-color:var(--line)}
.gfooter.gf--light .gf-legal{color:#6b7682}
.gfooter.gf--light .gf-legal a{color:var(--p)}
/* center: no columns at all -- the link lists flatten into one inline row */
.gfooter.gf--center{text-align:center;border-top:4px solid var(--accent)}
.gfooter.gf--center .gf-cols{display:block;border-bottom:0;padding-bottom:10px}
.gfooter.gf--center .gf-brand{max-width:56ch;margin:0 auto 16px}
.gfooter.gf--center .gf-brand p{max-width:none;margin:0 auto}
.gfooter.gf--center .gf-logo{justify-content:center}
.gfooter.gf--center .gf-cols>div:not(.gf-brand){display:inline}
.gfooter.gf--center .gf-cols h4{display:none}
.gfooter.gf--center .gf-cols a{display:inline-block;padding:4px 13px}
.gfooter.gf--center .gf-trust{justify-content:center;border-top:1px solid rgba(255,255,255,.1)}
.gfooter.gf--center .gf-legal{justify-content:center}
/* split: brand lifted into its own panel beside the link columns */
.gfooter.gf--split .gf-cols{grid-template-columns:1.2fr 1.8fr;gap:30px;align-items:start}
.gfooter.gf--split .gf-brand{background:rgba(255,255,255,.05);border-radius:var(--radius);padding:24px}
.gfooter.gf--split .gf-cols>div:not(.gf-brand){display:inline-block;vertical-align:top;
  width:30%;min-width:145px;margin-right:2.5%}
/* cta: the gradient strip above the columns */
.gfooter.gf--cta .gf-main{padding-top:38px}

/* Footer links were ~32px tall with no mobile override anywhere in the sheet,
   and each footer carries 13-17 of them stacked with no gutter. */
@media(max-width:1120px){
  .gf-cols a{padding:11px 0;min-height:44px;display:flex;align-items:center}
  .gfooter.gf--center .gf-cols a{min-height:44px;padding:11px 13px}
  .gf-legal a{display:inline-block;padding:6px 0}
}
@media(max-width:820px){.gf-cols{grid-template-columns:1fr 1fr}.gf-brand{grid-column:1/-1}
  .gfooter.gf--split .gf-cols{grid-template-columns:1fr}}
@media(max-width:520px){.gf-cols{grid-template-columns:1fr}.gf-cta__in{flex-direction:column;align-items:flex-start}
  .gfooter.gf--split .gf-cols>div:not(.gf-brand),
  .gfooter.gf--center .gf-cols>div:not(.gf-brand){display:block;width:auto;margin-right:0}}

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
.checklist svg{width:22px;height:22px;color:var(--accent-lt);flex:0 0 auto;margin-top:1px}
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
.contact__c .lbl svg{width:18px;height:18px;color:var(--accent-lt);flex:0 0 auto}
.contact__c a,.contact__c .v{color:var(--muted);font-size:.95rem;word-break:break-word;text-decoration:none}
.contact__c a:hover{color:var(--p)}
.contact__cta{display:flex;gap:13px;justify-content:center;flex-wrap:wrap;margin-top:28px}
@media(max-width:700px){.contact{grid-template-columns:1fr 1fr;gap:22px 16px}}
@media(max-width:430px){.contact{grid-template-columns:1fr}}

/* per-city prose from the homepage content JSON's `sections` array. Reads as an
   editorial column rather than another card grid, which is the point -- it is
   the one part of the page that is genuinely different per city. */
/* ============================================================ SERVICES
   Six compositions of the same data. Every rule below reuses the site's own
   tokens (--p/--accent/--accent-lt/--radius/--btn-r/--disp/--line/--shadow) so
   each archetype reads as native to that site's identity rather than as a
   bolted-on style. Each has a deliberate mobile composition -- none of them is
   "the desktop grid, stacked". */
.svcx{margin-top:8px}
.svcx a{text-decoration:none}
.svcx-go{display:inline-flex;align-items:center;gap:7px;font-family:var(--disp);
  font-weight:700;font-size:.9rem;color:var(--p)}
.svcx-go svg{width:17px;height:17px;transition:transform .2s}
.svcx a:hover .svcx-go svg{transform:translateX(4px)}
.svcx-ic{display:inline-flex;align-items:center;justify-content:center;
  width:42px;height:42px;border-radius:12px;flex:0 0 42px;
  background:color-mix(in srgb,var(--accent) 14%,#fff);color:var(--p)}
.svcx-ic svg{width:20px;height:20px;fill:none;stroke:currentColor}
.svcx-all{display:inline-flex;align-items:center;gap:8px;margin-top:26px;
  min-height:44px;padding:10px 2px;                      /* comfortable tap target */
  font-family:var(--disp);font-weight:700;color:var(--p);font-size:.96rem}
.svcx-all svg{width:17px;height:17px;transition:transform .2s}
.svcx-all:hover svg{transform:translateX(4px)}
.svcx-sec .sec-head{margin-bottom:38px}

/* ---- Services: shared primitives -----------------------------------------
   Eight compositions, one vocabulary. The image frame, the ruled service rail
   and the in-composition heading are defined once; an archetype supplies the
   grid and a modifier or two. */

/* heading placed inside a composition rather than centred above it */
.svcx-sec .sec-head--left{text-align:left;margin:0 0 30px;max-width:34ch}
.svcx-sec .sec-head--left h2{font-size:clamp(1.7rem,3.2vw,2.5rem);line-height:1.08;
  margin:0 0 12px}
.svcx-sec .sec-head--left p{margin:0;font-size:1.04rem;max-width:44ch}

/* the image plane */
.svcx-vis{position:relative;overflow:hidden;border-radius:calc(var(--radius) + 6px);
  box-shadow:var(--shadow-lg);background:var(--soft2)}
.svcx-vis img{width:100%;height:100%;object-fit:cover;display:block;
  object-position:50% 50%;transition:transform .7s cubic-bezier(.2,.7,.3,1),
  object-position .7s cubic-bezier(.2,.7,.3,1)}
.svcx-vis--hero{aspect-ratio:5/4}
.svcx-vis--tall{aspect-ratio:4/5}
.svcx-vis--pano{aspect-ratio:2/1}
.svcx-vis--fill{position:absolute;inset:0;border-radius:0;box-shadow:none}
.svcx-vis--sticky{position:sticky;top:100px}

/* ruled service rail -- rows, not boxes. A stack of bordered white rectangles
   is what makes a services section read as a database dump. */
.svcx-rail{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}
.svcx-rail a{display:grid;grid-template-columns:auto 1fr 26px;align-items:baseline;
  gap:4px 18px;padding:20px 4px;border-bottom:1px solid var(--line);
  transition:padding .25s,background .25s}
.svcx-rail a:hover,.svcx-rail a:focus-visible{padding-left:14px;
  background:linear-gradient(90deg,color-mix(in srgb,var(--accent) 7%,transparent),transparent 65%)}
/* thumbnail rail: every row shows the service it links to */
.svcx-rail--thumb a{grid-template-columns:82px 1fr 26px;align-items:center}
.svcx-thumb{width:82px;height:64px;border-radius:calc(var(--radius) - 3px);
  overflow:hidden;background:var(--soft2)}
.svcx-thumb img{width:100%;height:100%;object-fit:cover;display:block;
  transition:transform .55s cubic-bezier(.2,.7,.3,1)}
.svcx-rail--thumb a:hover .svcx-thumb img,
.svcx-rail--thumb a:focus-visible .svcx-thumb img{transform:scale(1.09)}
.svcx-txt{display:flex;flex-direction:column;gap:5px;min-width:0}
.svcx-txt b{font-family:var(--disp);font-weight:700;color:var(--ink);
  font-size:clamp(1.08rem,1.9vw,1.32rem);line-height:1.2;letter-spacing:-.01em}
.svcx-rail--big .svcx-txt b{font-size:clamp(1.15rem,2.2vw,1.55rem)}
.svcx-txt em{font-style:normal;color:var(--muted);font-size:.95rem;line-height:1.5;
  max-width:52ch;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;
  -webkit-box-orient:vertical}
.svcx-rail a:hover b,.svcx-rail a:focus-visible b{color:var(--p)}
.svcx-num{font-family:var(--disp);font-weight:800;font-size:.86rem;
  color:var(--accent-lt);letter-spacing:.06em;padding-top:.35em}
.svcx-rail .svcx-go svg{width:19px;height:19px;color:var(--p);
  opacity:.35;transition:opacity .2s,transform .2s}
.svcx-rail a:hover .svcx-go svg,.svcx-rail a:focus-visible .svcx-go svg{
  opacity:1;transform:translateX(4px)}
.svcx-go{display:inline-flex;align-items:center;gap:8px;font-family:var(--disp);
  font-weight:700;font-size:.92rem;color:var(--p)}
.svcx-all{display:inline-flex;align-items:center;gap:8px;margin-top:24px;
  min-height:44px;padding:10px 2px;font-family:var(--disp);font-weight:700;
  color:var(--p);font-size:.96rem}
.svcx-all svg{width:17px;height:17px;transition:transform .2s}
.svcx-all:hover svg{transform:translateX(4px)}

/* THE ACTIVE SERVICE DRIVES THE IMAGE.
   Every service owns a photograph -- select_photos draws each one from that
   service's own pool, salted by domain -- so the plane holds the whole set
   stacked and cross-fades to whichever service is engaged. No JS: :has() does
   the switching.

   Two selection tiers share one class family (.svcx-sel--N):
     COMMITTED  a radio stays checked -- this is what makes the section usable
                by touch, where there is no hover to preview with.
     TRANSIENT  hover / keyboard focus / :active, which must visibly override
                whatever is committed for as long as it lasts.
   The transient tier is written second AND padded with :nth-child(n) purely to
   match the committed tier's specificity, so source order decides the tie and
   exactly one layer is ever lit. */
.svcx-vis--swap{isolation:isolate}
.svcx-vis--swap img{position:absolute;inset:0;width:100%;height:100%;
  object-fit:cover;opacity:0;transform:scale(1.045);
  transition:opacity .5s ease,transform .9s cubic-bezier(.2,.7,.3,1)}
.svcx-vis--swap img:first-child{opacity:1;transform:scale(1)}

/* the swapping copy panel: same mechanism, text instead of photographs */
.svcx-cs{display:grid;margin:0;padding:0;list-style:none}
.svcx-cs>li{grid-area:1/1;opacity:0;visibility:hidden;
  transform:translateY(6px);transition:opacity .35s ease,transform .45s ease}
.svcx-cs>li:first-child{opacity:1;visibility:visible;transform:none}

/* -- committed: a radio stays checked, which is how touch selects -- */
.svcx:has(.svcx-sel:checked) .svcx-vis--swap img{opacity:0}
.svcx:has(.svcx-sel:checked) .svcx-cs>li{opacity:0;visibility:hidden}
.svcx:has(.svcx-sel--1:checked) .svcx-vis--swap img:nth-child(1){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--1:checked) .svcx-cs>li:nth-child(1){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--2:checked) .svcx-vis--swap img:nth-child(2){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--2:checked) .svcx-cs>li:nth-child(2){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--3:checked) .svcx-vis--swap img:nth-child(3){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--3:checked) .svcx-cs>li:nth-child(3){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--4:checked) .svcx-vis--swap img:nth-child(4){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--4:checked) .svcx-cs>li:nth-child(4){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--5:checked) .svcx-vis--swap img:nth-child(5){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--5:checked) .svcx-cs>li:nth-child(5){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--6:checked) .svcx-vis--swap img:nth-child(6){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--6:checked) .svcx-cs>li:nth-child(6){opacity:1;visibility:visible;transform:none}

/* -- pointer: hover / press, outranks the radio for as long as it lasts -- */
.svcx:has(.svcx-sel:is(:hover,:active)) .svcx-vis--swap img:nth-child(n){opacity:0}
.svcx:has(.svcx-sel:is(:hover,:active)) .svcx-cs>li:nth-child(n){opacity:0;visibility:hidden}
.svcx:has(.svcx-sel--1:is(:hover,:active)) .svcx-vis--swap img:nth-child(1){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--1:is(:hover,:active)) .svcx-cs>li:nth-child(1){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--2:is(:hover,:active)) .svcx-vis--swap img:nth-child(2){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--2:is(:hover,:active)) .svcx-cs>li:nth-child(2){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--3:is(:hover,:active)) .svcx-vis--swap img:nth-child(3){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--3:is(:hover,:active)) .svcx-cs>li:nth-child(3){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--4:is(:hover,:active)) .svcx-vis--swap img:nth-child(4){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--4:is(:hover,:active)) .svcx-cs>li:nth-child(4){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--5:is(:hover,:active)) .svcx-vis--swap img:nth-child(5){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--5:is(:hover,:active)) .svcx-cs>li:nth-child(5){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--6:is(:hover,:active)) .svcx-vis--swap img:nth-child(6){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--6:is(:hover,:active)) .svcx-cs>li:nth-child(6){opacity:1;visibility:visible;transform:none}

/* -- keyboard: focus wins over a mouse left sitting somewhere else -- */
.svcx:has(.svcx-sel:focus-visible) .svcx-vis--swap img:nth-child(n){opacity:0}
.svcx:has(.svcx-sel:focus-visible) .svcx-cs>li:nth-child(n){opacity:0;visibility:hidden}
.svcx:has(.svcx-sel--1:focus-visible) .svcx-vis--swap img:nth-child(1){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--1:focus-visible) .svcx-cs>li:nth-child(1){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--2:focus-visible) .svcx-vis--swap img:nth-child(2){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--2:focus-visible) .svcx-cs>li:nth-child(2){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--3:focus-visible) .svcx-vis--swap img:nth-child(3){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--3:focus-visible) .svcx-cs>li:nth-child(3){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--4:focus-visible) .svcx-vis--swap img:nth-child(4){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--4:focus-visible) .svcx-cs>li:nth-child(4){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--5:focus-visible) .svcx-vis--swap img:nth-child(5){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--5:focus-visible) .svcx-cs>li:nth-child(5){opacity:1;visibility:visible;transform:none}
.svcx:has(.svcx-sel--6:focus-visible) .svcx-vis--swap img:nth-child(6){opacity:1;transform:scale(1)}
.svcx:has(.svcx-sel--6:focus-visible) .svcx-cs>li:nth-child(6){opacity:1;visibility:visible;transform:none}

/* the radio is the state, never the visual: it stays focusable and reachable
   but the step/word/node it belongs to carries the focus ring */
.svcx-r{position:absolute;width:1px;height:1px;opacity:0;margin:0;
  pointer-events:none}
.svcx-pick{position:absolute;inset:0;z-index:1;cursor:pointer;
  border-radius:inherit}
.svcx-sr{position:absolute;width:1px;height:1px;overflow:hidden;
  clip-path:inset(50%);white-space:nowrap}
/* the service link sits ABOVE the selection overlay so clicking the name
   always navigates and never just previews */
.svcx-nav{position:relative;z-index:2}

@media(prefers-reduced-motion:reduce){
  .svcx-vis--swap img,.svcx-cs>li{transition:opacity .001s;transform:none!important}
  /* `.svcx *` matches elements only -- a pseudo-element's transition is not
     inherited and was still animating under reduce */
  .svcx-word::after{transition:none!important}
  .svcx-word__t{transform:none!important}
}


/* 01 FEATURED -- dominant image carries the primary service */
.svcx--featured{display:grid;grid-template-columns:1.15fr .85fr;gap:56px;
  align-items:stretch}
/* the left column is heading + a tall image, the right is a short rail; left
   to itself that leaves an empty quadrant. Anchor the rail's tail to the
   bottom of the picture so the two columns close together. */
.svcx--featured .svcx-col{display:flex;flex-direction:column}
.svcx--featured .svcx-leadlink{flex:1;display:flex}
.svcx--featured .svcx-leadlink .svcx-vis{flex:1}
.svcx--featured .svcx-col--side .svcx-all{margin-top:auto;padding-top:26px}
.svcx-leadlink{display:block;position:relative;overflow:hidden;
  border-radius:calc(var(--radius) + 6px)}
.svcx-leadlink .svcx-vis{border-radius:calc(var(--radius) + 6px)}
.svcx-leadlink:hover .svcx-vis img{transform:scale(1.05)}
.svcx-leadcap{position:absolute;left:0;right:0;bottom:0;z-index:1;padding:30px 32px;
  display:flex;flex-direction:column;gap:10px;align-items:flex-start;color:#fff;
  background:linear-gradient(to top,rgba(8,12,18,.9) 22%,rgba(8,12,18,.45) 62%,transparent)}
.svcx-leadcap b{font-family:var(--disp);font-weight:700;color:#fff;
  font-size:clamp(1.35rem,2.6vw,1.95rem);line-height:1.1}
.svcx-leadcap .svcx-go{color:#fff}
.svcx-col--side{padding-top:6px}
.svcx--featured .svcx-vis--hero{aspect-ratio:auto;min-height:380px}

/* 02 EDITORIAL -- type-led list, tall reactive panel */
.svcx--editorial{display:grid;grid-template-columns:1.2fr .8fr;gap:56px;align-items:start}

/* 08 SPOTLIGHT -- sticky visual anchored, services advance beside it */
.svcx--spotlight{display:grid;grid-template-columns:.95fr 1.05fr;gap:56px;align-items:start}

/* 10 FLOATING -- offset image plane, service stack layered across it */
/* Overlap via grid cells, never negative margins: a percentage margin-top here
   is a percentage of the container WIDTH, which pulled the panel clean out of
   the section and over the band above it. */
.svcx--floating{display:grid;grid-template-columns:repeat(12,1fr);align-items:center}
.svcx-vis--float{grid-column:5/13;grid-row:1;align-self:stretch;margin:30px 0;
  min-height:400px}
.svcx-stack{grid-column:1/7;grid-row:1;z-index:1;background:var(--card);
  border-radius:calc(var(--radius) + 6px);padding:36px 38px;box-shadow:var(--shadow-lg)}
.svcx-stack .svcx-rail a:hover{background:none;padding-left:10px}

/* 03 BENTO -- image sets the hierarchy, blocks stay unequal */
.svcx--bento{display:grid;grid-template-columns:repeat(3,1fr);
  grid-auto-rows:minmax(132px,auto);gap:14px}
.svcx-blk{display:flex;flex-direction:column;background:var(--card);
  border-radius:var(--radius);transition:.2s;border:1px solid var(--line);
  overflow:hidden}
.svcx-blk__im{display:block;flex:0 0 136px;overflow:hidden;background:var(--soft2)}
.svcx-blk__im img{width:100%;height:100%;object-fit:cover;display:block;
  transition:transform .6s cubic-bezier(.2,.7,.3,1)}
.svcx-blk:hover .svcx-blk__im img{transform:scale(1.06)}
.svcx-blk--c .svcx-blk__im{flex-basis:104px}
.svcx-blk__t{display:flex;flex-direction:column;gap:8px;padding:20px 22px 22px}
.svcx-blk:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg);border-color:var(--p)}
.svcx-blk h3{margin:0;font-size:1.12rem}
.svcx-blk p{margin:0;color:var(--muted);font-size:.94rem;overflow:hidden;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical}
.svcx-blk--c p{-webkit-line-clamp:2}
.svcx-blk--img{grid-column:span 2;grid-row:span 2;padding:0;border:0;position:relative;
  overflow:hidden;min-height:400px;justify-content:flex-end}
.svcx-blk--img .svcx-vis{position:absolute;inset:0;border-radius:var(--radius);box-shadow:none}
.svcx-blk--img:hover .svcx-vis img{transform:scale(1.05)}
.svcx-blk__cap{position:relative;z-index:1;margin-top:auto;padding:30px 32px;color:#fff;
  display:flex;flex-direction:column;gap:10px;align-items:flex-start;
  background:linear-gradient(to top,rgba(8,12,18,.9) 24%,rgba(8,12,18,.42) 64%,transparent)}
.svcx-blk__cap b{font-family:var(--disp);font-weight:700;color:#fff;
  font-size:clamp(1.3rem,2.4vw,1.8rem)}
.svcx-blk__cap .svcx-go{color:#fff}

/* 06 OVERLAY -- the photograph is the section */
.svcx--overlay{position:relative;overflow:hidden;border-radius:calc(var(--radius) + 8px);
  min-height:480px;display:flex;align-items:center;box-shadow:var(--shadow-lg)}
/* the scrim is load-bearing: white type over an unknown photograph is how this
   composition normally fails contrast */
.svcx--overlay::after{content:"";position:absolute;inset:0;
  background:linear-gradient(102deg,rgba(8,12,18,.93) 0%,rgba(8,12,18,.9) 30%,
  rgba(8,12,18,.62) 58%,rgba(8,12,18,.14) 100%)}
.svcx-over{position:relative;z-index:1;padding:56px;max-width:620px}
.svcx-over .eyebrow{color:#fff;opacity:.75}
.svcx-over h2{color:#fff;font-size:clamp(1.8rem,3.4vw,2.7rem);line-height:1.08;
  margin:0 0 14px}
.svcx-over__p{color:rgba(255,255,255,.85);margin:0 0 26px;max-width:46ch;font-size:1.04rem}
.svcx-pills{display:flex;flex-wrap:wrap;gap:10px}
.svcx-pill{display:inline-flex;align-items:center;gap:9px;min-height:46px;
  padding:11px 18px;border-radius:999px;background:rgba(255,255,255,.12);
  border:1px solid rgba(255,255,255,.3);color:#fff;font-family:var(--disp);
  font-weight:700;font-size:.98rem;transition:.18s;backdrop-filter:blur(6px)}
.svcx-pill svg{width:16px;height:16px;opacity:.7;transition:transform .2s}
.svcx-pill:hover,.svcx-pill:focus-visible{background:#fff;color:var(--ink);
  border-color:#fff}
.svcx-pill:hover svg{transform:translateX(3px);opacity:1}

/* 07 ACCORDION -- one open at a time, the open panel carries the visual */
.svcx--accordion{display:grid;grid-template-columns:.72fr 1.28fr;gap:52px;
  align-items:start}
.svcx--accordion .svcx-hd{position:sticky;top:104px}
.svcx-accs{border-top:1px solid var(--line);min-width:0}
.svcx-acc{border-bottom:1px solid var(--line)}
.svcx-acc summary{display:grid;grid-template-columns:auto 1fr 24px;align-items:center;
  gap:18px;padding:22px 4px;cursor:pointer;list-style:none;min-height:62px;transition:.2s}
.svcx-acc summary::-webkit-details-marker{display:none}
.svcx-acc summary:hover,.svcx-acc summary:focus-visible{padding-left:12px}
.svcx-acc summary b{font-size:clamp(1.1rem,2vw,1.42rem)}
.svcx-caret svg{width:20px;height:20px;color:var(--p);opacity:.45;
  transform:rotate(90deg);transition:transform .3s,opacity .2s}
.svcx-acc[open] .svcx-caret svg{transform:rotate(-90deg);opacity:1}
.svcx-acc[open] summary b{color:var(--p)}
.svcx-acc__b{display:grid;grid-template-columns:1.1fr .9fr;gap:28px;
  align-items:center;padding:6px 4px 32px}
.svcx-acc__t p{margin:0 0 20px;color:var(--muted);font-size:1.02rem;max-width:46ch}

/* 09 PROBLEM -> SERVICE */
.svcx--problem{display:grid;grid-template-columns:.85fr 1.15fr;gap:48px;align-items:center}
.svcx-pcs{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.svcx-pc{display:grid;gap:9px;padding:22px 24px;border-radius:var(--radius);
  background:var(--card);border:1px solid var(--line);
  border-left:3px solid var(--accent);transition:.18s}
.svcx-pc:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg)}
.svcx-pc b{font-family:var(--disp);font-size:1.08rem;color:var(--ink)}
.svcx-ans{display:inline-flex;align-items:center;gap:9px;color:var(--p);
  font-family:var(--disp);font-weight:700;font-size:.95rem}
.svcx-ans svg{width:16px;height:16px;color:var(--accent-lt)}

/* 11 TIMELINE -- the work as a route, not a menu.
   Horizontal on desktop so the sequence reads left-to-right; a vertical spine
   on small screens, which is a different composition rather than the same row
   squeezed. */
.svcx--timeline{display:grid;gap:30px}
.svcx-vis--journey{aspect-ratio:2.4/1;min-height:280px}
.svcx-steps{display:grid;grid-template-columns:repeat(var(--svcx-n),minmax(0,1fr));
  margin:0;padding:0;list-style:none}
.svcx-step{position:relative;padding:30px 26px 4px 0;border-top:2px solid var(--line);
  transition:border-color .3s}
.svcx-step+.svcx-step{padding-left:26px}
.svcx-step__n{position:absolute;top:-14px;left:0;width:28px;height:28px;
  border-radius:50%;background:var(--soft);border:2px solid var(--line);
  color:var(--muted);display:grid;place-items:center;
  font-family:var(--disp);font-weight:800;font-size:.68rem;transition:.3s}
.svcx-step+.svcx-step .svcx-step__n{left:26px}
.svcx-step__t{display:block;font-family:var(--disp);font-weight:700;
  font-size:clamp(1.02rem,1.6vw,1.24rem);line-height:1.2;color:var(--ink);
  margin-bottom:7px;transition:color .25s}
.svcx-step__d{display:block;color:var(--muted);font-size:.93rem;line-height:1.5;
  overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical}
.svcx-step .svcx-nav{margin-top:13px;font-size:.86rem;opacity:.5;
  transition:opacity .25s;min-height:44px;align-items:center}
.svcx-step .svcx-nav svg{width:15px;height:15px}
.svcx-step:hover .svcx-nav,.svcx-step:focus-within .svcx-nav{opacity:1}
.svcx-step:hover .svcx-step__n{border-color:var(--p);color:var(--p)}
/* committed step */
.svcx-step:has(.svcx-r:checked){border-top-color:var(--accent)}
.svcx-step:has(.svcx-r:checked) .svcx-step__n{background:var(--accent);
  border-color:var(--accent);color:var(--on-accent)}
.svcx-step:has(.svcx-r:checked) .svcx-step__t{color:var(--p)}
.svcx-step:has(.svcx-r:checked) .svcx-nav{opacity:1}
.svcx-step:has(.svcx-r:focus-visible){outline:3px solid var(--accent);
  outline-offset:5px;border-radius:4px}

/* 12 TYPO -- the service names are the artwork.
   The plate OVERLAPS the list rather than sitting beside it. Each rule runs the
   full section width and terminates underneath the photograph, so there is no
   dead tail to leave the rows looking unfinished -- that overlap is the
   composition, not decoration. Row padding-right keeps the type clear of it. */
.svcx--typo{--plate:clamp(300px,40%,470px);--gut:44px;--rowpad:30px;
  display:grid;grid-template-columns:minmax(0,1fr) var(--plate);
  grid-template-rows:auto auto auto;gap:0}
/* five names would make the plate tall and narrow; tighten the rows instead */
.svcx--typo:has(.svcx-word:nth-child(5)){--rowpad:22px}
.svcx-kick{grid-column:1/-1;grid-row:1;display:grid;grid-template-columns:1fr auto;
  gap:14px 40px;align-items:end;padding-bottom:26px;
  border-bottom:1px solid var(--line)}
.svcx-kick h2{margin:6px 0 0;font-size:clamp(1.05rem,1.3vw,1.18rem);
  line-height:1.35;letter-spacing:0;max-width:34ch}
.svcx-kick__p{margin:0;color:var(--muted);font-size:.97rem;max-width:34ch;
  text-align:right}
.svcx-words{grid-column:1/-1;grid-row:2;list-style:none;margin:0;padding:0;
  min-width:0}
/* no border-top on the first row: the kicker's rule already opens the list, and
   two hairlines a row-padding apart read as a table header */
.svcx-word{position:relative;display:grid;grid-template-columns:44px minmax(0,1fr);
  align-items:baseline;gap:0 8px;padding:var(--rowpad) 0;
  padding-right:calc(var(--plate) + var(--gut));
  border-bottom:1px solid var(--line)}
.svcx-word__i{display:flex;align-items:center;justify-content:flex-start;
  min-width:44px;min-height:44px;cursor:pointer;font-family:var(--disp);
  font-weight:800;font-size:.8rem;letter-spacing:.08em;
  color:color-mix(in srgb,var(--ink) 42%,transparent);transition:color .25s}
/* justify-self:start is load-bearing. As a grid item the anchor stretched to
   fill its cell, so hundreds of px of blank space per row was still a link --
   it navigated on click and it made the rules run into nothing. */
.svcx-word__t{display:inline-block;justify-self:start;font-family:var(--disp);
  font-weight:800;font-size:clamp(1.65rem,2.9vw + .45rem,2.85rem);line-height:1.1;
  letter-spacing:-.02em;color:var(--ink);overflow-wrap:break-word;padding:8px 0;
  transition:color .3s ease,transform .35s cubic-bezier(.2,.7,.3,1)}
/* transient tier = preview: colour and a small shift, never geometry */
.svcx-word:hover .svcx-word__t,.svcx-word:focus-within .svcx-word__t{
  color:var(--p);transform:translateX(9px)}
.svcx-word:hover .svcx-word__i,.svcx-word:focus-within .svcx-word__i{color:var(--p)}
/* committed tier = the rule itself draws. Hover must NOT draw it, or four bars
   animate as the cursor travels and the section reads as a menu. */
.svcx-word::after{content:"";position:absolute;left:0;bottom:-1px;height:2px;
  width:0;background:var(--accent);transition:width .55s cubic-bezier(.2,.7,.3,1)}
.svcx-word:has(.svcx-r:checked)::after{width:100%}
.svcx-word:has(.svcx-r:checked) .svcx-word__t{color:var(--p)}
.svcx-word:has(.svcx-r:checked) .svcx-word__i{color:var(--accent-lt)}
.svcx-word:has(.svcx-r:focus-visible){outline:3px solid var(--accent);
  outline-offset:4px;border-radius:4px}
/* the plate: column 2, spanning the list and the all-services row, painted over
   the rules. z-index 3 clears .svcx-pick (1) and .svcx-nav (2). */
.svcx-reveal{grid-column:2;grid-row:2/4;position:relative;z-index:3;
  align-self:stretch}
.svcx-vis--reveal{aspect-ratio:auto;height:100%;min-height:400px}
/* the copy is a caption ON the plate, not a paragraph parked under it */
/* the scrim is load-bearing, not decoration: measured at 1.74:1 with a
   lighter ramp, because the caption can land on a bright part of an
   unknown photograph. Hold it near-opaque wherever type actually sits. */
.svcx-reveal .svcx-cs{position:absolute;left:0;right:0;bottom:0;z-index:1;
  padding:44px 28px 24px;border-radius:0 0 calc(var(--radius) + 6px)
  calc(var(--radius) + 6px);
  background:linear-gradient(to top,rgba(8,12,18,.96) 0%,rgba(8,12,18,.94) 64%,
  rgba(8,12,18,.84) 86%,rgba(8,12,18,.38) 100%)}
.svcx-reveal .svcx-cs>li h3{display:none}
.svcx-reveal .svcx-cs>li p{margin:0 0 12px;max-width:38ch;font-size:.98rem;
  color:rgba(255,255,255,.9)}
.svcx-reveal .svcx-cs>li .svcx-nav,.svcx-reveal .svcx-cs>li .svcx-go{color:#fff}
.svcx--typo .svcx-all{grid-column:1;grid-row:3;justify-self:start}

/* 13 ORBIT -- services placed around the work itself.
   Positioned with cos()/sin() on an ellipse that is deliberately wider than it
   is tall and rotated off the vertical, so it reads as a composition rather
   than a compass rose. Trig in calc() is newer than nothing here -- the whole
   selection mechanism already requires :has(), which shipped alongside it. */
.svcx--orbit{display:grid;grid-template-columns:1.34fr .66fr;gap:26px 44px;
  align-items:center}
.svcx--orbit .svcx-hd{grid-column:1/-1}
.svcx-ring{position:relative;aspect-ratio:1/.82;width:100%}
.svcx-vis--core{position:absolute;left:50%;top:50%;width:42%;aspect-ratio:1;
  transform:translate(-50%,-50%);border-radius:50%}
.svcx-vis--core img{border-radius:50%}
.svcx-nodes{list-style:none;margin:0;padding:0;position:absolute;inset:0}
.svcx-node{--ang:calc((1turn * (var(--i) - 1) / var(--svcx-n)) - .25turn + .045turn);
  position:absolute;left:calc(50% + cos(var(--ang)) * 37%);
  top:calc(50% + sin(var(--ang)) * 40%);transform:translate(-50%,-50%);
  width:22%;text-align:center;padding:10px 4px;
  border-radius:var(--radius);transition:transform .3s cubic-bezier(.2,.7,.3,1)}
/* node number = preview control; node title = the link */
.svcx-node__n{display:grid;place-items:center;width:44px;height:44px;
  margin:0 auto 8px;border-radius:50%;border:1px solid var(--line);
  background:var(--card);cursor:pointer;font-family:var(--disp);
  font-weight:800;font-size:.7rem;letter-spacing:.04em;color:var(--muted);
  transition:.25s}
.svcx-node__n:hover{border-color:var(--p);color:var(--p)}
.svcx-node__t{display:inline-flex;align-items:center;min-height:44px;
  font-family:var(--disp);font-weight:700;font-size:clamp(.94rem,1.35vw,1.1rem);
  line-height:1.22;color:var(--muted);transition:color .25s}
.svcx-node::after{content:"";position:absolute;left:50%;bottom:-9px;width:7px;
  height:7px;border-radius:50%;background:var(--line);transform:translateX(-50%);
  transition:background .25s,transform .25s}
.svcx-node:hover .svcx-node__t{color:var(--p)}
.svcx-node:has(.svcx-r:checked){transform:translate(-50%,-50%) scale(1.06)}
.svcx-node:has(.svcx-r:checked) .svcx-node__t{color:var(--p)}
.svcx-node:has(.svcx-r:checked)::after{background:var(--accent);
  transform:translateX(-50%) scale(1.7)}
.svcx-node:has(.svcx-r:checked) .svcx-node__n{background:var(--accent);
  border-color:var(--accent);color:var(--on-accent)}
.svcx-node:has(.svcx-r:focus-visible){outline:3px solid var(--accent);
  outline-offset:3px}
.svcx-orbit__b{min-width:0}

/* the copy panel shared by TYPO and ORBIT */
.svcx-cs>li h3{margin:0 0 10px;font-size:clamp(1.14rem,2vw,1.5rem)}
.svcx-cs>li p{margin:0 0 18px;color:var(--muted);font-size:1.01rem;max-width:44ch}
.svcx-cs>li .svcx-nav{min-height:44px;align-items:center}

/* 14 TABS -- adapted from the client's "Services 05: Tabs + Image".
   Their DESIGN.md rejects shadows in favour of tonal layering and 1px rules, so
   this archetype is built flat: hairline tab bar, hairline panel, no elevation.
   Every colour is a token -- the source palette is one fixed light-blue scheme
   and hardcoding it would render all 1001 sites identically. */
.svcx--tabs{display:grid;gap:0}
.svcx-tabs__hd{text-align:center;margin-bottom:26px}
.svcx-tabs__hd p:last-child{margin-left:auto;margin-right:auto}
/* the scroller centres while the tabs fit and scrolls when they do not.
   justify-content:center on the scroller itself would clip the first tab. */
.svcx-tabs{overflow-x:auto;scroll-snap-type:x proximity;
  border-bottom:1px solid var(--line);-webkit-overflow-scrolling:touch}
.svcx-tabs__in{display:flex;margin:0 auto;padding:0;list-style:none;width:max-content;
  max-width:100%}
.svcx-tab{position:relative;flex:0 0 auto;scroll-snap-align:center}
.svcx-tab__l{display:flex;align-items:center;justify-content:center;
  min-height:52px;padding:14px 26px;cursor:pointer;white-space:nowrap;
  font-family:var(--disp);font-weight:700;
  font-size:clamp(.98rem,1.15vw,1.14rem);color:var(--muted);
  border-bottom:2px solid transparent;margin-bottom:-1px;transition:color .25s}
.svcx-tab__l:hover{color:var(--ink)}
.svcx-tab:has(.svcx-r:checked) .svcx-tab__l{color:var(--p);
  border-bottom-color:var(--accent)}
.svcx-tab:has(.svcx-r:focus-visible) .svcx-tab__l{outline:3px solid var(--accent);
  outline-offset:-3px;border-radius:4px}

.svcx-panel{display:grid;grid-template-columns:.88fr 1.12fr;gap:56px;
  align-items:center;padding-top:52px}
.svcx-panel__t{min-width:0}
/* the panel heading is the section's display type, but the page h1 is 53px --
   keep it at section-h2 scale so the Services list never outranks the hero */
.svcx-panel__t .svcx-cs>li h3{margin:0 0 14px;
  font-size:clamp(1.5rem,2.4vw,2.25rem);line-height:1.14;letter-spacing:-.02em}
.svcx-panel__t .svcx-cs>li p{margin:0 0 26px;color:var(--muted);
  font-size:1.04rem;line-height:1.6;max-width:46ch}
/* their "Secondary (Outline)" button; .btn--outline already exists */
.svcx-panel__t .svcx-cs>li .svcx-nav{display:inline-flex;align-items:center;
  gap:10px;min-height:48px;padding:12px 24px;border:1px solid var(--ink);
  border-radius:var(--btn-r);color:var(--ink);transition:.2s}
.svcx-panel__t .svcx-cs>li .svcx-nav:hover{background:var(--ink);color:var(--card)}
.svcx-panel__t .svcx-cs>li .svcx-nav svg{width:17px;height:17px;
  transition:transform .2s}
.svcx-panel__t .svcx-cs>li .svcx-nav:hover svg{transform:translateX(4px)}
/* flat per DESIGN.md: sharp-ish corners, a hairline, no shadow */
.svcx-vis--tab{aspect-ratio:3/2;box-shadow:none;border:1px solid var(--line);
  border-radius:var(--radius)}
.svcx--tabs .svcx-all{justify-self:start;margin-top:4px}

/* ---- MOBILE: an intentional composition per archetype -------------------- */
@media(max-width:980px){
  .svcx--featured,.svcx--editorial,.svcx--spotlight,.svcx--problem{
    grid-template-columns:1fr;gap:26px}
  /* relative, NOT static: the swap layers are absolutely positioned and
     .svcx-vis must stay their containing block, or they escape the frame
     and widen the page */
  .svcx-vis--sticky{position:relative;top:auto}
  .svcx-vis--tall{aspect-ratio:4/3}
  /* editorial keeps the numbered list first: the sequence is the composition */
  .svcx--editorial .svcx-vis{order:2}
  .svcx--editorial .svcx-col{order:1}
  .svcx-col--side{padding-top:0}
  /* floating un-stacks into image then panel, no negative offset */
  .svcx--floating{grid-template-columns:1fr}
  /* reset the desktop stretch: min-height + aspect-ratio would otherwise
     drive WIDTH off the height and blow past a narrow viewport */
  .svcx-vis--float{grid-column:1;grid-row:1;align-self:auto;margin:0;
    min-height:0;aspect-ratio:16/10}
  .svcx-stack{grid-column:1;grid-row:2;margin:-42px 12px 0;padding:26px 22px}
  /* bento -> anchor image then unequal blocks */
  .svcx--bento{grid-template-columns:1fr 1fr}
  .svcx-blk--img{grid-column:1/-1;grid-row:auto;min-height:260px}
  .svcx-blk{padding:20px}
  /* overlay -> vertical scrim so the pills keep contrast */
  .svcx--overlay{min-height:0}
  .svcx--overlay::after{background:linear-gradient(180deg,rgba(8,12,18,.72) 0%,
    rgba(8,12,18,.94) 52%)}
  .svcx-over{padding:34px 24px;max-width:none}
  /* accordion -> image above the copy inside the open panel */
  .svcx--accordion{grid-template-columns:1fr;gap:22px}
  .svcx--accordion .svcx-hd{position:static}
  .svcx-acc__b{grid-template-columns:1fr;gap:18px}
  .svcx-pcs{grid-template-columns:1fr}

  /* TIMELINE -> vertical spine. Not the desktop row squeezed: the sequence
     runs top-to-bottom against a rule, which is how a journey scans on a phone. */
  .svcx--timeline{gap:22px}
  .svcx-vis--journey{aspect-ratio:16/10;min-height:0}
  .svcx-steps{grid-template-columns:1fr}
  .svcx-step,.svcx-step+.svcx-step{border-top:0;border-left:2px solid var(--line);
    padding:2px 0 26px 28px}
  .svcx-step:last-child{border-left-color:transparent}
  .svcx-step__n,.svcx-step+.svcx-step .svcx-step__n{top:0;left:-15px}
  .svcx-step:has(.svcx-r:checked){border-top-color:var(--line);
    border-left-color:var(--accent)}
  .svcx-step .svcx-nav{opacity:1}

  /* TYPO -> not the desktop grid stacked. The name moves ONTO the photograph
     as its caption and the list demotes to a compact ruled index, so the type
     stays the artwork without needing a width the phone does not have. */
  .svcx--typo{--plate:0px;--gut:0px;--rowpad:0px;
    grid-template-columns:1fr;grid-template-rows:none;gap:22px}
  .svcx-kick,.svcx-words,.svcx-reveal,.svcx--typo .svcx-all{
    grid-column:1;grid-row:auto}
  .svcx-kick{order:1;grid-template-columns:1fr;align-items:start;gap:10px;
    padding-bottom:18px}
  .svcx-kick__p{text-align:left;max-width:none}
  .svcx-reveal{order:2;align-self:auto}
  .svcx-words{order:3}
  .svcx--typo .svcx-all{order:4}
  .svcx-vis--reveal{height:auto;min-height:0;aspect-ratio:4/3}
  .svcx-reveal .svcx-cs{padding:22px 20px 18px}
  .svcx-reveal .svcx-cs>li h3{display:block;margin:0 0 10px;color:#fff;
    font-size:clamp(1.5rem,6.4vw,2.1rem);line-height:1.08;letter-spacing:-.02em}
  .svcx-reveal .svcx-cs>li p{display:none}
  .svcx-word{grid-template-columns:minmax(0,1fr) 56px;align-items:center;
    padding:0;gap:0}
  .svcx-word__t{grid-column:1;grid-row:1;display:flex;align-items:center;
    min-height:48px;
    padding:12px 0;font-size:clamp(1.05rem,4.4vw,1.32rem);letter-spacing:-.01em}
  .svcx-word:hover .svcx-word__t,.svcx-word:focus-within .svcx-word__t{transform:none}
  .svcx-word__i{grid-column:2;grid-row:1;justify-content:flex-end;min-width:56px;
    font-size:.72rem}

  /* TABS -> head, then the tab bar as a scroll-snap chip row, then image,
     then the active service's copy. The bar scrolls rather than wrapping: a
     wrapped tab bar stops looking like tabs. */
  .svcx-panel{grid-template-columns:1fr;gap:24px;padding-top:28px}
  .svcx-tabs__hd{text-align:left;margin-bottom:20px}
  .svcx-tabs__hd p:last-child{margin-left:0;margin-right:0}
  .svcx-tabs__in{margin:0}
  .svcx-tab__l{min-height:48px;padding:12px 18px}
  .svcx-vis--tab{order:-1;aspect-ratio:16/11}
  .svcx-panel__t .svcx-cs>li p{margin-bottom:22px}

  /* ORBIT -> the ring is abandoned, not shrunk. Image, then a scroll-snap
     selector, then the active service: a circle of tap targets on a phone is a
     worse control, not a smaller one. */
  .svcx--orbit{grid-template-columns:1fr;gap:20px}
  .svcx-ring{aspect-ratio:auto;display:grid;gap:18px}
  .svcx-vis--core{position:relative;left:auto;top:auto;width:100%;
    aspect-ratio:16/11;transform:none;border-radius:calc(var(--radius) + 6px)}
  .svcx-vis--core img{border-radius:calc(var(--radius) + 6px)}
  /* stays inside the wrap: a hardcoded negative margin only full-bleeds
     correctly at one wrap padding, and was 6px wider than the viewport */
  .svcx-nodes{position:static;display:flex;gap:10px;overflow-x:auto;
    scroll-snap-type:x mandatory;padding:2px 2px 10px;margin:0;
    -webkit-overflow-scrolling:touch}
  .svcx-node{position:static;transform:none;width:auto;flex:0 0 auto;
    scroll-snap-align:start;text-align:left;padding:11px 16px;
    border:1px solid var(--line);background:var(--card);white-space:nowrap}
  .svcx-node::after{display:none}
  .svcx-node:has(.svcx-r:checked){transform:none;border-color:var(--accent);
    background:color-mix(in srgb,var(--accent) 8%,var(--card))}
  .svcx-node__t{min-height:44px}
}
@media(max-width:560px){
  .svcx-rail a{grid-template-columns:auto 1fr 20px;gap:4px 12px;padding:17px 2px}
  .svcx-leadcap{padding:20px}
  .svcx-over{padding:26px 18px}
  .svcx-stack{margin:-26px 8px 0;padding:22px 18px}
  .svcx--bento{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){
  .svcx *,.svcx-vis img,.svcx-blk,.svcx-pill,.svcx-caret svg{transition:none!important}
  .svcx-vis img{transform:none!important}
  .svcx-blk:hover,.svcx-pc:hover{transform:none!important}
}

/* ---- visual beats ---------------------------------------------------------
   The page ran eleven consecutive text sections after the services grid with no
   imagery. These two break it up, and they consume photos that were already
   being copied into every site and never referenced. */
.shots{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.shots figure{margin:0;overflow:hidden;border-radius:calc(var(--radius) + 2px);
  box-shadow:var(--shadow)}
.shots img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;transition:transform .5s}
.shots figure:hover img{transform:scale(1.04)}
/* was: hide the third figure below 760px, which silently turned a
   three-photo section into two on every phone */
@media(max-width:760px){.shots{grid-template-columns:1fr;gap:12px}
  .shots img{aspect-ratio:16/10}}

/* ---- VISUAL PROOF variants -------------------------------------------------
   Adapted from the client's visual-proof set. Their DESIGN.md rejects shadows
   in favour of tonal layering and 1px rules, so these are built flat: hairline
   frames, no elevation, tokens throughout. */
/* .sec-head--left is scoped to .svcx-sec upstream, so it does nothing here.
   These heads are direct children of .wrap; the svcx ones never are. */
.wrap>.sec-head--left{text-align:left;max-width:40ch;margin:0 0 30px}
.wrap>.sec-head--left p{margin:0}
.pf-rule{display:block;width:48px;height:3px;background:var(--p);margin:18px 0 22px}
.pf-go{display:inline-flex;align-items:center;gap:9px;min-height:44px;
  font-family:var(--disp);font-weight:700;font-size:.96rem;color:var(--p)}
.pf-go svg{width:17px;height:17px;transition:transform .2s}
.pf-go:hover svg{transform:translateX(4px)}
.pf-points{list-style:none;margin:0;padding:0}
.pf-points li{display:grid;grid-template-columns:26px 1fr;gap:14px;
  align-items:start;padding:16px 0;border-bottom:1px solid var(--line)}
.pf-points li:last-child{border-bottom:0}
.pf-ic{display:grid;place-items:center;width:26px;height:26px;border-radius:50%;
  border:1px solid var(--line);background:var(--card);transition:.25s}
.pf-ic svg{width:14px;height:14px;color:var(--p)}
.pf-points li:hover .pf-ic{background:var(--p);border-color:var(--p)}
.pf-points li:hover .pf-ic svg{color:var(--on-accent)}
.pf-pt b{font-family:var(--disp);font-weight:700;font-size:1.02rem;color:var(--ink);
  line-height:1.45}

/* 03 DETAIL -- one photograph carrying the section, editorial column beside */
.pf-detail{display:grid;grid-template-columns:1.35fr .65fr;gap:56px;align-items:center}
.pf-detail__img{position:relative;overflow:hidden;border:1px solid var(--line);
  border-radius:var(--radius)}
.pf-detail__img img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;
  transition:transform .7s cubic-bezier(.2,.7,.3,1)}
.pf-detail__img:hover img{transform:scale(1.03)}
.pf-detail__b h2{margin:0;font-size:clamp(1.5rem,2.4vw,2.15rem);line-height:1.14}
.pf-detail__b p{margin:0 0 22px;color:var(--muted);font-size:1.04rem;max-width:40ch}

/* 04 TECHNICIAN -- wide plate, claim column offset to the outer columns */
.pf-tech{display:grid;grid-template-columns:repeat(12,1fr);gap:0 40px;align-items:center}
.pf-tech__img{grid-column:1/8;overflow:hidden;border:1px solid var(--line);
  border-radius:var(--radius)}
.pf-tech__img img{display:block;width:100%;aspect-ratio:16/10;object-fit:cover;
  transition:transform .7s cubic-bezier(.2,.7,.3,1)}
.pf-tech__img:hover img{transform:scale(1.03)}
.pf-tech__b{grid-column:9/13}
.pf-tech__b h2{margin:0 0 14px;font-size:clamp(1.4rem,2.1vw,1.95rem);line-height:1.16}
.pf-tech__b>p{margin:0 0 20px;color:var(--muted);font-size:1.01rem}

/* 01 CINEMATIC -- tall plate under a left head, claims as a ruled rail beside */
.pf-cine{display:grid;grid-template-columns:1fr;gap:28px}
.pf-cine__hd{grid-column:1/-1;margin:0 0 6px}
.pf-cine__img{grid-column:1;overflow:hidden;border:1px solid var(--line);
  border-radius:var(--radius)}
.pf-cine__img img{display:block;width:100%;aspect-ratio:21/9;object-fit:cover;
  min-height:340px;transition:transform .8s cubic-bezier(.2,.7,.3,1)}
.pf-cine__img:hover img{transform:scale(1.03)}
/* claims as a caption row under the plate, not a side rail -- that is what
   separates this from the technician variant */
.pf-points--rail{grid-column:1;display:grid;grid-template-columns:repeat(3,1fr);
  gap:0 40px}
.pf-points--rail li{border-bottom:0;border-top:1px solid var(--line);
  padding:18px 0 0;align-items:start}

/* 05 SEQUENCE -- the job as an ordered strip, one photograph per stage.
   The connecting rule sits behind the numerals, drawn with a pseudo-element on
   the list so it never appears before the first or after the last step. */
.pf-seq{position:relative;list-style:none;margin:0;padding:0;display:grid;
  grid-template-columns:repeat(var(--pf-n,3),minmax(0,1fr));gap:30px}
.pf-step{position:relative;display:flex;flex-direction:column;align-items:flex-start}
.pf-step::before{content:"";position:absolute;top:21px;left:44px;right:-30px;
  height:1px;background:var(--line)}
.pf-step:last-child::before{display:none}
.pf-step__n{display:grid;place-items:center;width:44px;height:44px;border-radius:50%;
  background:var(--card);border:1px solid var(--line);color:var(--ink);
  font-family:var(--disp);font-weight:800;font-size:.78rem;margin-bottom:22px;
  position:relative;z-index:1;transition:.25s}
.pf-step:hover .pf-step__n{background:var(--p);border-color:var(--p);
  color:var(--on-accent)}
.pf-step__im{display:block;width:100%;overflow:hidden;margin-bottom:20px;
  border:1px solid var(--line);border-radius:var(--radius)}
.pf-step__im img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;
  filter:grayscale(.4);transition:filter .55s ease,transform .7s cubic-bezier(.2,.7,.3,1)}
.pf-step:hover .pf-step__im img{filter:grayscale(0);transform:scale(1.04)}
@media(hover:none){.pf-step__im img{filter:none}}
.pf-step h3{margin:0 0 8px;font-size:clamp(1.05rem,1.5vw,1.24rem)}
.pf-step p{margin:0;color:var(--muted);font-size:.96rem;line-height:1.55}

@media(max-width:900px){
  .pf-detail,.pf-cine{grid-template-columns:1fr;gap:26px}
  .pf-detail__img img{aspect-ratio:16/10}
  .pf-cine__img,.pf-points--rail,.pf-cine__hd{grid-column:1}
  .pf-points--rail{grid-template-columns:1fr;gap:0}
  .pf-points--rail li{border-top:0;border-bottom:1px solid var(--line);
    padding:16px 0}
  .pf-points--rail li:last-child{border-bottom:0}
  .pf-cine__img img{aspect-ratio:16/10}
  .pf-tech{grid-template-columns:1fr;gap:26px}
  .pf-tech__img,.pf-tech__b{grid-column:1}
  /* the strip becomes a vertical spine rather than three squeezed columns */
  .pf-seq{grid-template-columns:1fr;gap:0}
  .pf-step{display:grid;grid-template-columns:44px minmax(0,1fr);
    column-gap:18px;padding-bottom:30px}
  .pf-step::before{top:52px;bottom:-8px;left:21px;right:auto;width:1px;height:auto}
  .pf-step:last-child{padding-bottom:0}
  .pf-step__n{grid-column:1;grid-row:1;margin-bottom:0}
  .pf-step__im{grid-column:2;grid-row:1;margin-bottom:14px}
  .pf-step__im img{aspect-ratio:16/10}
  .pf-step h3{grid-column:2}
  .pf-step p{grid-column:2}
}
@media(prefers-reduced-motion:reduce){
  .pf-detail__img img,.pf-tech__img img,.pf-cine__img img,.pf-step__im img,
  .pf-ic,.pf-step__n,.pf-go svg{transition:none!important;transform:none!important}
  .pf-step__im img{filter:none!important}
}
.splitfeat{display:grid;grid-template-columns:1fr 1fr;gap:52px;align-items:center}
.splitfeat--flip .splitfeat__img{order:2}
.splitfeat__img img{width:100%;aspect-ratio:4/3;object-fit:cover;
  border-radius:calc(var(--radius) + 4px);box-shadow:var(--shadow-lg)}
.splitfeat__b h2{margin:0 0 12px}
.splitfeat__b>p{color:var(--muted);font-size:1.06rem;margin:0 0 20px}
.splitfeat .checklist{list-style:none;padding:0;margin:0;display:grid;gap:12px}
.splitfeat .checklist li{display:flex;gap:11px;align-items:flex-start;color:var(--ink);
  font-size:1rem}
.splitfeat .checklist svg{width:21px;height:21px;color:var(--accent-lt);flex:0 0 auto;
  margin-top:2px}
/* pull quote -- a change of typographic register, using the site's own words */
.pullq{max-width:820px;margin:0 auto;text-align:center;border:0;padding:0}
.pullq p{font-family:var(--disp);font-weight:600;line-height:1.34;
  font-size:clamp(1.35rem,3vw,2rem);color:var(--ink);margin:0 0 18px}
.pullq p::before{content:"\\201C";color:var(--accent-lt);margin-right:2px}
.pullq p::after{content:"\\201D";color:var(--accent-lt)}
.pullq cite{font-style:normal;font-size:.85rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted);font-weight:700}
/* reviews -- rendered only from real supplied data, never generated */
.revs{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}
.rev{margin:0;background:var(--card);border:1px solid var(--line);
  border-radius:var(--radius);padding:26px;box-shadow:var(--shadow)}
.rev blockquote{margin:0 0 16px;font-size:1.02rem;line-height:1.6;color:var(--ink)}
.rev figcaption{font-family:var(--disp);font-weight:700;font-size:.95rem;color:var(--p)}
.rev figcaption span{display:block;font-weight:500;font-size:.85rem;color:var(--muted)}
@media(max-width:860px){
  .splitfeat{grid-template-columns:1fr;gap:28px}
  .splitfeat--flip .splitfeat__img{order:0}
  .photoband__in{padding:64px 20px}
}

/* shaped local-content components -- see shape_section() */
.areagrid{list-style:none;padding:0;margin:0;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px 14px}
.areagrid li{display:flex}
.areagrid a{display:flex;align-items:baseline;justify-content:space-between;gap:12px;
  width:100%;min-height:46px;padding:11px 15px;background:var(--card);
  border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);
  text-decoration:none;transition:.16s}
.areagrid a:hover{border-color:var(--p);transform:translateY(-1px);
  box-shadow:var(--shadow-lg);text-decoration:none}
.areagrid .nolink{display:flex;align-items:baseline;justify-content:space-between;
  gap:12px;width:100%;min-height:46px;padding:11px 15px;background:var(--soft);
  border:1px dashed var(--line);border-radius:var(--radius)}
.areagrid .nolink .an{color:var(--muted)}
.areagrid .an{font-family:var(--disp);font-weight:700;font-size:.97rem;color:var(--ink)}
.areagrid .ad{font-size:.82rem;font-weight:700;color:var(--accent-lt);
  white-space:nowrap;flex:0 0 auto}
.areagrid__note{max-width:70ch;margin:22px auto 0;text-align:center;color:var(--muted);
  font-size:.98rem}
.lstats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:16px;margin-bottom:34px}
.lstat{text-align:center;padding:22px 16px;background:var(--card);
  border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
.lstat b{display:block;font-family:var(--disp);font-weight:800;line-height:1.05;
  font-size:clamp(1.5rem,3.1vw,2.1rem);color:var(--p);margin-bottom:6px}
.lstat span{font-size:.86rem;color:var(--muted);letter-spacing:.01em}
.lead-para{font-size:1.15rem;line-height:1.62;color:var(--ink);margin-bottom:1.1rem}
/* stack: numbered editorial rows, no imagery */
.srows{display:grid;gap:0;border-top:1px solid var(--line)}
.srow{display:grid;grid-template-columns:64px minmax(150px,1.05fr) 2fr 34px;
  align-items:center;gap:18px;padding:22px 6px;border-bottom:1px solid var(--line);
  text-decoration:none;transition:.16s}
.srow:hover{background:var(--soft);padding-left:14px;text-decoration:none}
.srow__n{font-family:var(--disp);font-weight:800;font-size:1.15rem;color:var(--accent-lt)}
.srow__t{font-family:var(--disp);font-weight:700;font-size:1.12rem;color:var(--ink)}
.srow__d{color:var(--muted);font-size:.96rem}
.srow__a svg{width:19px;height:19px;color:var(--p)}
.srow:hover .srow__a svg{transform:translateX(4px);transition:transform .18s}
@media(max-width:760px){
  .srow{grid-template-columns:44px 1fr;gap:6px 14px;padding:18px 4px}
  .srow__d{grid-column:2}
  .srow__a{display:none}
}
.splitcopy{display:grid;grid-template-columns:260px 1fr;gap:44px;align-items:start;
  max-width:1000px;margin:0 auto}
.splitcopy .localcopy{max-width:none;margin:0}
.ranklist{list-style:none;padding:0;margin:0;position:sticky;top:96px}
.ranklist li{display:flex;align-items:center;gap:11px;padding:11px 0;
  border-bottom:1px solid var(--line);font-family:var(--disp);font-weight:700;
  font-size:.99rem;color:var(--ink)}
.ranklist li:last-child{border-bottom:0}
.ranklist .rk{flex:0 0 26px;height:26px;border-radius:8px;display:flex;
  align-items:center;justify-content:center;background:var(--accent);
  color:var(--on-accent);font-size:.8rem}
.ranklist:not(.ranklist--n) li::before{content:"";flex:0 0 7px;height:7px;
  border-radius:50%;background:var(--accent)}
@media(max-width:860px){
  .splitcopy{grid-template-columns:1fr;gap:26px}
  .ranklist{position:static;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
    gap:0 18px}
}
@media(max-width:560px){
  .areagrid{grid-template-columns:1fr}
  .lstats{grid-template-columns:1fr 1fr;gap:12px}
  .lstat{padding:16px 10px}
}
.localcopy{max-width:780px;margin:0 auto}
.localcopy h2{margin-top:1.7em;font-size:clamp(1.35rem,2.4vw,1.8rem)}
.localcopy h2:first-child{margin-top:0}
.localcopy p{color:var(--muted);font-size:1.03rem}
.localcopy ul{padding-left:1.15em;color:var(--muted)}
.localcopy li{margin-bottom:.4em}
.sec--soft .localcopy p,.sec--soft .localcopy ul{color:#4a5561}

/* ---------------------------------------------------------- sticky call bar
   Shown at exactly the widths where the header's "Free Quote" button is hidden
   (<=1120px, see build_site.py). Above that the header CTA is always on screen,
   so a fixed bar would just be a fifth CTA; below it, the top-bar phone link
   scrolls away and the burger is the only thing left.

   --callbar-h drives BOTH the bar height and the space reserved for it, so they
   cannot drift apart. The reservation goes on .gfooter, not body: body is white
   and .gfooter is #0e141b, so body padding would paint a white strip under the
   dark footer whenever the two numbers disagreed by even a pixel.

   z-index must stay BELOW header.site's 60. The header has a backdrop-filter and
   so forms a stacking context; the open mobile nav panel is its child and
   therefore paints above this bar and covers it, which is what we want. */
.callbar{display:none}
@media(max-width:1120px){
  /* Must be >= the bar's own content height, which is fixed at 75.39px:
     26.4px line box + 24px anchor padding + 4px anchor border (border-box)
     + 20px bar padding + 1px border-top. 78 leaves a small margin and keeps
     the reservation an exact match rather than a 0.39px-short guess. */
  :root{--callbar-h:78px}
  .callbar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:55;gap:10px;
    align-items:center;box-sizing:border-box;min-height:var(--callbar-h);
    padding:10px 12px calc(10px + env(safe-area-inset-bottom,0px));
    background:rgba(255,255,255,.97);backdrop-filter:blur(10px);
    border-top:1px solid var(--line);box-shadow:0 -6px 24px rgba(16,32,48,.13)}
  /* fixed padding so a CTA preset cannot change the bar's height out from under
     the reservation above */
  .callbar a{display:flex;align-items:center;justify-content:center;gap:8px;
    min-height:52px;padding:12px 16px;box-sizing:border-box;
    border-radius:var(--btn-r);border:2px solid transparent;
    font-family:var(--disp);font-weight:700;font-size:1rem;
    text-decoration:none;white-space:nowrap}
  .callbar__call{flex:1 1 auto;background:var(--accent);color:var(--on-accent)}
  .callbar__call svg{width:19px;height:19px;flex:0 0 auto}
  .callbar__call:active{filter:brightness(.94)}
  /* never .btn--ghost here: it is color:#fff, invisible on this light bar */
  .callbar__quote{flex:0 1 38%;background:#fff;color:var(--p);border-color:var(--p)}
  .callbar__quote:active{background:var(--soft)}
  .callbar__icon{flex:0 0 auto;width:52px;padding:12px;background:#fff;
    color:var(--p);border-color:var(--p)}
  .callbar__icon svg{width:21px;height:21px}
  .gfooter{padding-bottom:calc(var(--callbar-h) + env(safe-area-inset-bottom,0px))}
}
@media(max-width:380px){
  .callbar{gap:8px;padding-left:10px;padding-right:10px}
  .callbar a{padding:12px 10px;font-size:.95rem}
}
/* a fixed bar otherwise prints on the first page of every sheet */
@media print{.callbar{display:none}}
"""

# ---------------------------------------------------------------- CTA styles
# Six button treatments, harvested from the four designs already in this repo so
# the vocabulary stays coherent: "solid" is the historical default, "glow" is
# nimbus's soft-shadow lift, "press" is volt's hard offset shadow, "edge" is
# ironclad's hairline uppercase outline; "raised" and "cut" fill the gaps.
#
# Each preset owns radius, padding, border weight, type treatment and the
# primary/outline fills, and renders against the site's own theme tokens -- so
# two sites sharing a preset but not a theme still don't look alike.
#
# Every preset MUST set transform and filter on :hover. The base rules at
# build_site.py:441-442 apply both `filter:brightness(1.06)` and
# `translateY(-1px)`; a preset that only redefines `background` inherits them.
#
# ORDER IS AN APPEND-ONLY CONTRACT. Selection is digest % len(BUTTON_STYLES), so
# inserting, removing or reordering a preset re-rolls the assignment for nearly
# all 1001 domains. Add new presets at the end only.
BUTTON_STYLES = {
    "solid": {
        "r": None, "pad": "14px 26px", "bw": "2px", "fs": "1rem",
        "tt": "none", "ls": "0", "icon": "18px",
        "pri":  "background:var(--accent);color:var(--on-accent);"
                "border-color:transparent;box-shadow:none",
        "prih": "filter:brightness(1.06);transform:translateY(-1px);box-shadow:none",
        "out":  "background:#fff;color:var(--p);border-color:var(--line);box-shadow:none",
        "outh": "border-color:var(--p);filter:none;transform:none",
    },
    "glow": {
        "r": "999px", "pad": "14px 30px", "bw": "0", "fs": "1rem",
        "tt": "none", "ls": "0", "icon": "18px",
        "pri":  "background:var(--accent);color:var(--on-accent);border-color:transparent;"
                "box-shadow:0 10px 22px color-mix(in srgb,var(--accent) 42%,transparent)",
        "prih": "filter:none;transform:translateY(-3px) scale(1.02);"
                "box-shadow:0 16px 30px color-mix(in srgb,var(--accent) 52%,transparent)",
        "out":  "background:#fff;color:var(--p);border-color:transparent;"
                "box-shadow:0 6px 18px rgba(16,32,48,.13)",
        "outh": "filter:none;transform:translateY(-3px);box-shadow:0 14px 26px rgba(16,32,48,.18)",
    },
    "press": {
        "r": "0", "pad": "15px 26px", "bw": "2px", "fs": ".86rem",
        "tt": "uppercase", "ls": ".06em", "icon": "17px",
        "pri":  "background:var(--accent);color:var(--on-accent);"
                "border-color:var(--p);box-shadow:5px 5px 0 var(--p)",
        "prih": "filter:none;transform:translate(3px,3px);box-shadow:2px 2px 0 var(--p)",
        "out":  "background:#fff;color:var(--p);border-color:var(--p);"
                "box-shadow:5px 5px 0 color-mix(in srgb,var(--p) 22%,#fff)",
        "outh": "filter:none;transform:translate(3px,3px);"
                "box-shadow:2px 2px 0 color-mix(in srgb,var(--p) 22%,#fff)",
    },
    "edge": {
        "r": "2px", "pad": "16px 30px", "bw": "1px", "fs": ".76rem",
        "tt": "uppercase", "ls": ".18em", "icon": "15px",
        "pri":  "background:transparent;color:var(--p);border-color:var(--p);box-shadow:none",
        "prih": "background:var(--p);color:#fff;filter:none;transform:none;box-shadow:none",
        "out":  "background:transparent;color:var(--p);border-color:var(--line);box-shadow:none",
        "outh": "border-color:var(--p);filter:none;transform:none",
        # this is the one preset whose primary is an outline. On the sticky bar
        # that would make the call button indistinguishable from the secondary,
        # so the bar uses the solid inversion (which is edge's own hover state).
        "barpri": "background:var(--p);color:#fff;border-color:var(--p);box-shadow:none",
    },
    "raised": {
        "r": "10px", "pad": "15px 28px", "bw": "0", "fs": "1rem",
        "tt": "none", "ls": "0", "icon": "18px",
        "pri":  "background:var(--accent);color:var(--on-accent);border-color:transparent;"
                "box-shadow:0 2px 0 var(--pd),0 6px 14px rgba(16,32,48,.18)",
        "prih": "filter:none;transform:translateY(-2px);"
                "box-shadow:0 4px 0 var(--pd),0 10px 20px rgba(16,32,48,.22)",
        "out":  "background:#fff;color:var(--p);border-color:transparent;"
                "box-shadow:0 2px 0 var(--line),0 4px 10px rgba(16,32,48,.10)",
        "outh": "filter:none;transform:translateY(-2px);"
                "box-shadow:0 4px 0 var(--line),0 8px 16px rgba(16,32,48,.14)",
    },
    "cut": {
        "r": "3px", "pad": "15px 28px", "bw": "2px", "fs": "1rem",
        "tt": "none", "ls": ".01em", "icon": "18px",
        "pri":  "background:var(--p);color:#fff;border-color:var(--p);"
                "border-left:4px solid var(--accent);box-shadow:none",
        "prih": "background:var(--pd);filter:none;transform:none;box-shadow:none",
        "out":  "background:#fff;color:var(--p);border-color:var(--line);"
                "border-left:4px solid var(--accent);box-shadow:none",
        "outh": "border-color:var(--p);border-left-color:var(--accent);"
                "filter:none;transform:none",
    },
}
_BTN_ORDER = list(BUTTON_STYLES)

def button_style(t):
    """Preset name for this site. An explicit sites.json "buttons" wins; otherwise
    pick by digest. Unknown names warn and fall back rather than raising midway
    through a 1001-site build (mirrors get_renderer)."""
    pinned = (t.get("buttons") or "").strip()
    if pinned:
        if pinned in BUTTON_STYLES:
            return pinned
        print(f"  ! unknown button style '{pinned}' for {t['domain']} -> using solid")
        return "solid"
    return _BTN_ORDER[_hash_idx(t["domain"] + "|buttons", len(_BTN_ORDER))]

def btn_css(t):
    """Per-site CTA stylesheet, appended after GD_CSS so equal-specificity rules
    win on source order.

    Known rules that still outrank this block (left deliberately):
      .hd .btn                 build_site.py:486  (0,2,0) keeps its compact padding
      .lay-nav-center .hd>.btn build_site.py:537  (0,3,0) keeps absolute placement
      .qcard .btn / .hero .cta .btn  -- width/layout only, no property overlap
    """
    name = button_style(t)
    s = BUTTON_STYLES[name]
    radius = f":root{{--btn-r:{s['r']}}}\n" if s["r"] is not None else ""
    return f"""
/* ================= CTA style: {name} ================= */
{radius}.btn{{padding:{s['pad']};border-width:{s['bw']};font-size:{s['fs']};
  text-transform:{s['tt']};letter-spacing:{s['ls']}}}
.btn svg{{width:{s['icon']};height:{s['icon']}}}
.btn--primary{{{s['pri']}}}
.callbar__call{{{s.get('barpri', s['pri'])}}}
.btn--primary:hover{{{s['prih']}}}
.btn--outline,.callbar__quote,.callbar__icon{{{s['out']}}}
.btn--outline:hover{{{s['outh']}}}
/* The bar takes the preset's fill and radius, but deliberately NOT its type:
   the uppercase + .18em-tracked presets push "Call (469) 555-0142" + "Free
   Quote" past 420px, which overflows a 390px phone. Geometry on the primary
   mobile CTA beats the typographic echo. It also keeps its own padding so the
   bar height stays fixed at the reserved value, and drops the decorative shadow
   -- an offset shadow clips against the bar's edge, and a fixed element that
   shifts under the thumb reads as broken. */
.callbar a,.callbar a:hover,.callbar a:active{{box-shadow:none;transform:none}}
/* The borderless presets (glow, raised) define their secondary purely by shadow,
   which the reset above removes -- leaving a white-on-white button with no
   affordance. Force an outline on the bar's secondary so it always reads as a
   control. Needs the .callbar prefix to outrank ".callbar a"'s border shorthand. */
.callbar a.callbar__quote,.callbar a.callbar__icon{{border:2px solid var(--p)}}
/* Keyboard focus. The shared design system defines no :focus state at all, so
   without this every CTA falls back to a UA ring that is invisible on a filled
   accent button. */
.btn:focus-visible,.callbar a:focus-visible,nav.main>a:focus-visible,
.nav-item>button:focus-visible,.burger:focus-visible,.scard:focus-visible,
.svc-card:focus-visible,.areas a:focus-visible,.feat:focus-visible,
.faq summary:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}
@media(prefers-reduced-motion:reduce){{
  .btn{{transition:none}}
  .btn:hover{{transform:none}}
}}
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
            # empty phone must yield an empty tel, not the bare country code:
            # "+1" + "" produced href="tel:+1" on the 998 sites with no number
            "phone": phone, "tel": ("+1" + re.sub(r"\D", "", phone)) if phone else "",
            "content": s.get("content", s["city"].lower()),
            "ghl_form_id": s.get("ghl_form_id", ""),
            "port": s.get("port"),
            # design template ("garage" default; ironclad/volt/nimbus are full alt designs)
            "template": s.get("template", "garage"),
            # per-slot copy-deck pins, e.g. {"cta": 2}; empty = digest pick
            "copy": s.get("copy", {}),
            # Services archetype pin; "" = choose from site signals (services_archetype)
            "services": s.get("services", ""),
            # Visual-proof variant pin; "" = per-domain digest (see proof_section)
            "proof": s.get("proof", ""),
            # CTA preset name; "" = pick one per-domain by digest (see button_style).
            # This dict is a whitelist -- a sites.json key absent here is silently
            # dropped, so the override only works because it is listed.
            "buttons": s.get("buttons", ""),
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
    """Trim to <=60 chars, dropping the " | Brand" suffix first.

    Only append an ellipsis when the string was actually cut. The previous version
    appended one unconditionally after dropping the brand, so 56 of 202 built
    titles advertised a truncation that never happened ("Garage Door Noises and
    What They Mean..." is 37 characters)."""
    raw = (raw or "").strip()
    if len(raw) <= 60:
        return raw
    head = raw.split(" | ")[0].strip()
    if len(head) <= 60:
        return head
    return head[:57].rstrip() + "…"

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
        except Exception as e:
            print(f"  ! {t['content']}/{fn}: unreadable JSON, skipped ({e})")
            continue
        if not isinstance(data, dict):
            print(f"  ! {t['content']}/{fn}: not a JSON object, skipped")
            continue
        if "sections" not in data:
            # this used to drop the file silently, taking its h1/title/meta/faq
            # with it -- a homepage that merely lacked `sections` vanished whole
            print(f"  ! {t['content']}/{fn}: no 'sections' key, page skipped "
                  f"(its title/meta/faq are lost too)")
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
    # Omit rather than fake. streetAddress fell back to the *city name*, publishing
    # a wrong street for every site with no address on file, and an empty
    # telephone property is worse than no telephone property.
    addr = {"@type": "PostalAddress", "addressLocality": t["city"], "addressRegion": t["st"]}
    if t["street"]:
        addr["streetAddress"] = t["street"]
    if t["zip"]:
        addr["postalCode"] = t["zip"]
    node = {"@type": ["LocalBusiness", "HomeAndConstructionBusiness"],
            "@id": f"https://{t['domain']}/#business", "name": t["brand"],
            "url": f"https://{t['domain']}/", "priceRange": "$$",
            "address": addr, "areaServed": {"@type": "City", "name": f"{t['city']}, {t['st']}"}}
    if t.get("phone"):
        node["telephone"] = t["phone"]
    return node

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
               f'btn-{button_style(t)}')
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
</head><body class="{bodycls}">
<a class="skiplink" href="#main">Skip to content</a>"""

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
        nav += f'<div class="nav-item"><button type="button" aria-expanded="false">Services</button>{mega(nav_svc, "/services/", "All Services")}</div>'
    if areas:
        nav += f'<div class="nav-item"><button type="button" aria-expanded="false">Service Areas</button>{mega(areas[:18], "/service-areas/", "All Service Areas", " mega--areas")}</div>'
    if guides:
        nav += f'<div class="nav-item"><button type="button" aria-expanded="false">Guides</button>{mega(guides, "/guides/", "All Guides")}</div>'
    # About / Contact promoted to real navbar links (visible on desktop and in the mobile menu)
    nav += '<a href="/about/">About</a><a href="/contact/">Contact</a>'
    nav += '<a class="nav-quote" href="/request-a-quote/">Request a Quote</a>'

    return f"""<div class="top"><div class="wrap"><span>Serving {esc(t['city'])} &amp; the surrounding metro</span><span class="dot">&bull;</span><span>Same-day service available</span><span class="tsp"></span>{f'<a href="tel:{t["tel"]}">{icon("phone")}{esc(t["phone"])}</a>' if t.get('phone') else ''}</div></div>
<header class="site"><div class="wrap hd">
<a class="brand" href="/"><span class="brand__chip">{brand_chip(t, 40)}</span><span>{esc(t['brand'])}<small>{esc(t['tagline'])}</small></span></a>
<button class="burger" aria-label="Menu" aria-expanded="false" aria-controls="mainnav"><span></span><span></span><span></span></button>
<nav class="main" id="mainnav">{nav}</nav>
<a class="btn btn--primary" href="/request-a-quote/">Free Quote</a>
</div></header><main id="main">"""

# ---- phone CTAs -------------------------------------------------------------
# 998 of 1001 registered sites have no phone on file. Every call-to-action below
# has to degrade to the quote page rather than emit a dead tel: link, so the
# policy lives here instead of being re-guarded at each of the ten call sites.

def call_btn(t, cls="btn btn--primary", fallback_label="Get a Free Quote"):
    """Primary call CTA; falls back to the quote page when there is no number."""
    if t.get("phone"):
        return (f'<a class="{cls}" href="tel:{t["tel"]}">{icon("phone")}'
                f'Call {esc(t["phone"])}</a>')
    return f'<a class="{cls}" href="/request-a-quote/">{icon("phone")}{fallback_label}</a>'

def reach_phrase(t):
    """"one call away" only if there is actually a number to call."""
    return "one call away" if t.get("phone") else "ready to help"

def tel_link(t, cls=""):
    """Bare phone-number link. Empty string when the site has no number, so the
    surrounding markup can drop the whole row rather than render an empty link."""
    if not t.get("phone"):
        return ""
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="tel:{t["tel"]}">{esc(t["phone"])}</a>'

CALLBAR_VARIANTS = ["call", "split", "icon"]

def call_bar(t, is_quote=False):
    """Sticky call bar for phones and tablets.

    Rendered from footer(), which every page renderer appends immediately before
    </body>. That placement is load-bearing: position:fixed resolves against the
    nearest *transformed* ancestor, and the scroll-reveal system puts
    transform:translateY(22px) on .reveal elements (build_site.py). Keep this at
    body level or the bar will anchor to a section instead of the viewport.

    Three layouts, picked per-domain by digest. The call action is always present
    and always primary; only the secondary slot varies."""
    if not t.get("phone"):
        return ""            # never emit a tel: link to an empty number
    if is_quote:
        return ""            # already on the quote page; the form is the CTA there
    variant = CALLBAR_VARIANTS[_hash_idx(t["domain"] + "|callbar", len(CALLBAR_VARIANTS))]
    call = (f'<a class="callbar__call" href="tel:{t["tel"]}">{icon("phone")}'
            f'<span>Call {esc(t["phone"])}</span></a>')
    if variant == "split":
        second = '<a class="callbar__quote" href="/request-a-quote/">Free Quote</a>'
    elif variant == "icon":
        second = ('<a class="callbar__icon" href="/request-a-quote/" '
                  f'aria-label="Request a free quote">{icon("calendar")}</a>')
    else:
        second = ""
    return (f'<div class="callbar callbar--{variant}" role="region" '
            f'aria-label="Contact {esc(t["brand"])}">{call}{second}</div>')

def footer(t, pages, is_quote=False):
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
    addr_tel = f"<br>{tel_link(t)}" if t.get("phone") else ""
    brand_block = (f'<div class="gf-brand"><a class="gf-logo" href="/">{logo}</a><p>{blurb}</p>'
                   f'<address class="gf-addr">{addr}{addr_tel}</address></div>')
    cols = (f'<div><h4>Services</h4>{services}</div><div><h4>Company</h4>{company}</div>'
            f'<div><h4>Service Areas</h4>{area_links}</div>')
    # The footer used to repeat the trust bar's four claims verbatim, so every
    # page said the same thing twice. Show the *other* deck variant here instead.
    decks = COPY["trust"]
    alt = decks[(_hash_idx(f'{t["domain"]}|copy|trust', len(decks)) + 1) % len(decks)]
    trust = ('<div class="gf-trust">'
             + "".join(f'<div>{icon(ic)}<span>{_city(txt, t)}</span></div>' for ic, txt in alt)
             + '</div>')
    legal_tel = f' &middot; {tel_link(t)}' if t.get("phone") else ""
    legal = (f'<div class="gf-legal"><span>&copy; {date.today().year} {esc(t["brand"])}. All rights reserved.</span>'
             f'<span>{addr}{legal_tel}</span></div>')
    js = '<script src="/assets/nav.js" defer></script>'
    # layout.footer has been assigned per site in layouts.json all along and was
    # simply never read here
    variant = t.get("layout", {}).get("footer", "dark")
    strip = footer_cta(t) if variant == "cta" else ""
    # </main> closes here rather than in each of the four page renderers -- they
    # all compose as header(...) + body + footer(...), so opening the landmark in
    # header() and closing it here covers every page from one place.
    return (f'</main><footer class="gfooter gf--{variant}">{strip}<div class="gf-main"><div class="wrap">'
            f'<div class="gf-cols">{brand_block}{cols}</div>{trust}{legal}</div></div></footer>'
            f'{call_bar(t, is_quote)}{js}')

def footer_cta(t):
    """Gradient CTA strip above the footer columns.

    The .gf-cta CSS -- including its mobile rule -- shipped in every stylesheet
    from the start, but no code ever emitted the markup for it."""
    head, sub = copy_deck(t, "footer_cta")
    second = ('<a class="btn btn--ghost" href="/services/">See Our Services</a>'
              if t.get("phone") else "")
    return (f'<div class="gf-cta"><div class="wrap gf-cta__in">'
            f'<div><h3>{_city(head, t)}</h3><p>{_city(sub, t)}</p></div>'
            f'<div class="gf-cta__btns">{call_btn(t, "btn btn--primary", "Request a Quote")}'
            f'{second}</div></div></div>')

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
    call = call_btn(t, "btn btn--primary", "Get a Free Quote")
    # when there is no phone the primary already points at the quote page, so the
    # ghost button would be a duplicate link -- send it to services instead
    quote = ('<a class="btn btn--ghost" href="/request-a-quote/">Get a Free Quote</a>'
             if t.get("phone") else
             '<a class="btn btn--ghost" href="/services/">See Our Services</a>')
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

def trust_bar(t):
    """Previously took no arguments at all -- it structurally could not vary, and
    shipped the same four strings to every site."""
    cells = "".join(f'<div>{icon(ic)}<span>{_city(txt, t)}</span></div>'
                    for ic, txt in copy_deck(t, "trust"))
    return f'<section class="trust"><div class="wrap">{cells}</div></section>'

# Words that mark a state the CUSTOMER observes, as opposed to a service the
# business performs. "Stuck open, stuck shut, or off the track" is a symptom;
# "Motors, travel limits and rolling-code remotes reprogrammed" is a task list.
# Only the former belongs in a problem-first row, and only the author's own
# wording is ever used -- nothing here invents a complaint.
_SYMPTOM_MARKERS = ("stuck", "won't", "wont", "off the track", "off its track",
                    "jumped off", "broken", "snapped", "frayed", "bent",
                    "grinding", "noisy", "noise", "past saving", "sagging",
                    "crooked", "dented", "damaged")

_SERVICE_VERBS = ("re-set", "re-tensioned", "retensioned", "replaced", "straightened",
                  "reprogrammed", "fitted", "installed", "checked", "swapped",
                  "serviced", "sized", "diagnosed", "adjusted", "aligned")

def _symptom_lead(blurb):
    """The customer-facing symptom a blurb opens with, or None.

    Returns None freely: a service with no symptom language in its copy is
    presented service-first instead, rather than having a complaint invented for
    it or -- as an earlier version did -- echoing its own title back."""
    # split on sentence punctuation and spaced dashes only. Splitting on a bare
    # hyphen cut "rolling-code" and produced the nonsense "...and rolling?"
    first = re.split(r"[.;:]|\s[\u2013\u2014-]\s", blurb.strip())[0].strip()
    if not (3 <= len(first.split()) <= 13):
        return None
    low = first.lower()
    if not any(m in low for m in _SYMPTOM_MARKERS):
        return None
    # Reject clauses that describe the FIX rather than the fault. Several blurbs
    # mention symptom words inside a task description -- "frayed cables re-set
    # and re-tensioned" contains "frayed" but is not something a customer thinks.
    if any(v in low for v in _SERVICE_VERBS):
        return None
    return first.rstrip(" ,;")

def _symptom_phrase(sym):
    """Render a symptom the way the visitor would think it: conditional clauses
    stay statements, observed-state lists become questions."""
    return sym if re.match(r"^(when|if)\b", sym, re.I) else sym + "?"

def _svc_items(t, pages, tiles, cap):
    """Normalise tiles into render-ready items, priority-ordered, capped.

    Priority = tiles that resolve to a real service page first. Those are the
    pages the section exists to feed, so they earn the larger cells; the rest
    keep their authored order. Anything beyond `cap` is not dropped -- it stays
    reachable through the section's "all services" link, so the homepage helps
    the visitor choose instead of dumping the catalogue."""
    imgs = t.get("card_imgs") or CARD_IMGS
    items = []
    for i, (ic, title, blurb, slug) in enumerate(tiles):
        url = f"/services/{slug}/" if slug and f"/services/{slug}/" in pages else "/request-a-quote/"
        items.append({"ic": ic, "title": title, "blurb": blurb, "url": url,
                      "img": imgs[i % len(imgs)], "real": bool(slug and url.startswith("/services/")),
                      "sym": _symptom_lead(blurb)})
    items.sort(key=lambda x: not x["real"])          # stable: real pages first
    return items[:cap], len(items) > cap

def services_archetype(t, pages, tiles):
    """Choose the Services composition from signals already in the site data.

    Deterministic: the same site always resolves to the same archetype. The
    inputs are real design signals, not a coin flip --

      * how many services there are (few -> each can have space; many -> needs
        hierarchy),
      * whether service-specific imagery exists,
      * whether the copy actually contains symptom language,
      * and what the HERO already did. A photo-dominant hero (banner/center/
        overlap) is followed by a typographic Services section so the two read
        as different moments; a text-led hero is followed by an image-led one.

    A site can pin one explicitly with "services" in sites.json."""
    pinned = (t.get("services") or "").strip()
    if pinned:
        if pinned in SERVICE_ARCHETYPES:
            return pinned
        print(f"  ! unknown services archetype '{pinned}' for {t['domain']} -> auto")
    n = len(tiles)
    has_img = bool(t.get("card_imgs"))
    symptoms = sum(1 for x in tiles if _symptom_lead(x[2]))
    photo_hero = t.get("layout", {}).get("hero") in ("banner", "center", "overlap")

    # Every archetype now carries imagery, so image availability is a floor
    # rather than a differentiator; without photos the section falls back to the
    # editorial list, which is the only one that still reads without them.
    if not has_img:
        # Every archetype anchors on an image; with none available the numbered
        # list is the only composition that still reads, so it degrades to that
        # with the panel omitted rather than rendering an empty frame.
        return "editorial"
    eligible = ["featured", "editorial", "spotlight", "accordion"]   # n >= 3
    if n >= 3:
        eligible.append("tabs")
    if n >= 3:
        # the giant-type treatment needs names short enough to set large; one
        # long service name wrecks the whole composition, so measure first
        if max(len(_plain(x[1])) for x in tiles) <= 22:
            eligible.append("typo")
    if n >= 4:
        eligible += ["floating", "bento", "overlay", "timeline"]
    if n >= 4:
        # a ring reads as a ring from four nodes up; three is a triangle
        eligible.append("orbit")
    if symptoms >= 3:
        eligible.append("problem")

    # Hero contrast: the Services section should read as a new visual moment.
    # "Quiet" archetypes hold the image in a contained panel or reveal and let
    # type lead; the others let the image carry the section. A photo-dominant
    # hero is followed by a quiet one, and vice versa.
    # "quiet" = type leads and the photograph is held in a contained panel;
    # these follow a photo-dominant hero. The rest let the image carry the
    # section and follow a type-led hero.
    quiet = {"editorial", "accordion", "bento", "problem", "typo", "timeline",
             "tabs"}
    preferred = [a for a in eligible if (a in quiet) == photo_hero]
    pool = preferred or eligible
    return pool[_hash_idx(f'{t["domain"]}|services', len(pool))]

SERVICE_ARCHETYPES = ["featured", "editorial", "spotlight", "floating",
                      "bento", "overlay", "accordion", "problem",
                      "timeline", "typo", "orbit", "tabs"]

# Archetypes that compose the section heading INTO their own layout rather than
# taking the centred stack above. A centred eyebrow/h2/blurb on top of every
# composition is the strongest "template" tell there is.
_SVCX_OWN_HEAD = {"featured", "editorial", "spotlight", "floating", "overlay",
                  "accordion", "timeline", "typo", "orbit", "tabs"}

def services_grid(t, pages):
    """The Services section: one of eight art-directed compositions.

    Each anchors on ONE primary image and uses it structurally -- as the
    dominant plane, a sticky panel, a section ground, an offset feature or an
    accordion reveal. The active service drives the image where the composition
    supports it, so the picture is part of the interaction rather than
    decoration parked above a list."""
    tiles = service_tiles(t)
    arch = services_archetype(t, pages, tiles)
    cap = {"featured": 4, "editorial": 5, "spotlight": 5, "floating": 4,
           "bento": 5, "overlay": 6, "accordion": 5, "problem": 5,
           # the ring holds 6 comfortably; the journey and the giant words
           # lose their point past 5 -- a 6-step route is a list again
           "timeline": 5, "typo": 5, "orbit": 6,
           # a six-tab bar stops reading as tabs and starts reading as nav
           "tabs": 5}[arch]
    items, overflow = _svc_items(t, pages, tiles, cap)
    body = globals()[f"_svcx_{arch}"](t, items, overflow)
    head = "" if arch in _SVCX_OWN_HEAD else _svcx_head(t) + _svcx_more(t, items, overflow)
    outer = "" if arch in _SVCX_OWN_HEAD else ""
    return (f'<section class="sec sec--soft svcx-sec svcx-sec--{arch}"><div class="wrap">'
            f'{_svcx_head(t) if arch not in _SVCX_OWN_HEAD else ""}{body}'
            f'{_svcx_more(t, items, overflow) if arch not in _SVCX_OWN_HEAD else ""}'
            f'</div></section>')

# ---- shared primitives -----------------------------------------------------

def _svcx_head(t, cls=""):
    """Section heading. `cls` lets an archetype place it inside its own grid."""
    eyebrow, h2, blurb = copy_deck(t, "services_head")
    return (f'<div class="sec-head {cls}"><p class="eyebrow">{_city(eyebrow, t)}</p>'
            f'<h2>{_city(h2, t)}</h2><p>{_city(blurb, t)}</p></div>')

def _svcx_more(t, items, overflow):
    if not (overflow or len(items) > 2):
        return ""
    return f'<a class="svcx-all" href="/services/">All services {icon("arrow")}</a>'

def _svcx_primary(t, items):
    """The resting frame: the highest-priority service's own photo."""
    return items[0]["img"] if items else None

def _svcx_stack(t, items, mod=""):
    """The image plane, holding one photograph per service.

    select_photos already gives every service tile its own shot, drawn from that
    service's matching pool and salted by domain, so this shows the visitor the
    actual work rather than re-cropping a single picture. Layers are stacked and
    cross-faded by :has(); the first is the resting frame."""
    if not items:
        return ""
    # only the resting frame competes for bandwidth; the rest arrive behind it,
    # so the section paints at the same weight it did with a single photograph
    low = ' fetchpriority="low"'          # 3.10 f-strings reject backslashes
    layers = "".join(
        f'<img src="/assets/photos/{it["img"]}" loading="lazy" decoding="async"'
        f'{"" if i == 0 else low} '
        f'alt="{it["title"]} in {esc(t["city"])}, {esc(t["st"])}">'
        for i, it in enumerate(items))
    return f'<div class="svcx-vis svcx-vis--swap {mod}">{layers}</div>'

def _svcx_visual(t, img, mod="", label=None):
    if not img:
        return ""
    what = label or "Garage door service"
    return (f'<div class="svcx-vis {mod}"><img src="/assets/photos/{img}" loading="lazy" '
            f'alt="{what} in {esc(t["city"])}, {esc(t["st"])}"></div>')

def _plain(t):
    """Visible length of a pre-escaped title: "Openers &amp; Remotes" is 17
    characters on screen, not 21."""
    return html.unescape(t or "")

def _svcx_group(t):
    """Radio-group name. Unique per site so two sections never share state."""
    return f'svcx-pick-{slugify(t["domain"])}'

def _svcx_radio(group, i, first):
    """Committed selection. Touch has no hover, so without this the visitor can
    only change the picture by navigating away from it."""
    return (f'<input class="svcx-sel svcx-sel--{i} svcx-r" type="radio" '
            f'name="{group}" id="{group}-{i}"{" checked" if first else ""}>')

def _svcx_pick(group, i, title):
    """Overlay that turns the whole step into the selection target. Sits UNDER
    .svcx-nav, so the service name still navigates."""
    return (f'<label class="svcx-sel svcx-sel--{i} svcx-pick" for="{group}-{i}">'
            f'<span class="svcx-sr">Preview {title}</span></label>')

def _svcx_dot(group, i, title, cls):
    """Explicit 44px numbered control, for compositions where the service name
    fills the whole item and would leave a touch user nothing to preview with.
    Name navigates, dot previews -- two targets, neither ambiguous."""
    return (f'<label class="svcx-sel svcx-sel--{i} {cls}" for="{group}-{i}">'
            f'<span class="svcx-sr">Preview {title}</span>{i:02d}</label>')

def _svcx_nav(it, label="View service", sel=None):
    """The service link. `sel` also makes it a transient selector, so hovering
    the link previews instead of doing nothing -- without it the link sits above
    the selection overlay and creates a dead patch inside the item."""
    cls = f" svcx-sel svcx-sel--{sel}" if sel else ""
    return (f'<a class="svcx-nav svcx-go{cls}" href="{it["url"]}">{label} '
            f'{icon("arrow")}</a>')

def _svcx_h3(it):
    return f'<h3>{it["title"]}</h3>'

def _svcx_copystack(t, items, nav=True, heads=True):
    """The copy panel that tracks the active service -- one layer per service,
    swapped by the same :has() mechanism that drives the photograph."""
    lis = "".join(
        f'<li>{_svcx_h3(it) if heads else ""}<p>{esc(clean_text(it["blurb"]))}</p>'
        f'{_svcx_nav(it) if nav else ""}</li>' for it in items)
    return f'<ul class="svcx-cs">{lis}</ul>'

def _svcx_rail(t, items, numbered=False, big=False, thumbs=False):
    """Ruled service rows -- deliberately NOT boxes. A stack of white rectangles
    with border+radius+shadow is what makes a section read as a database dump.

    The whole row is the link, so navigation is never in competition with the
    hover state that drives the image."""
    rows = []
    for i, it in enumerate(items):
        num = f'<span class="svcx-num">{i+1:02d}</span>' if numbered else ""
        if thumbs:
            num = (f'<span class="svcx-thumb"><img src="/assets/photos/{it["img"]}" '
                   f'loading="lazy" alt="{it["title"]} in {esc(t["city"])}, '
                   f'{esc(t["st"])}"></span>')
        rows.append(f'<li><a class="svcx-sel svcx-sel--{i+1}" href="{it["url"]}">{num}'
                    f'<span class="svcx-txt"><b>{it["title"]}</b>'
                    f'<em>{esc(clean_text(it["blurb"]))}</em></span>'
                    f'<span class="svcx-go">{icon("arrow")}</span></a></li>')
    cls = ("svcx-rail" + (" svcx-rail--num" if numbered else "")
           + (" svcx-rail--big" if big else "") + (" svcx-rail--thumb" if thumbs else ""))
    return f'<{"ol" if numbered else "ul"} class="{cls}">{"".join(rows)}</{"ol" if numbered else "ul"}>'

# ---- archetypes ------------------------------------------------------------

def _svcx_featured(t, items, overflow):
    """01. Dominant image carrying the primary service; supporting rail beside."""
    lead, rest = items[0], items[1:]
    return (f'<div class="svcx svcx--featured">'
            f'<div class="svcx-col">{_svcx_head(t, "sec-head--left")}'
            f'<a class="svcx-leadlink" href="{lead["url"]}">'
            f'{_svcx_visual(t, lead["img"], "svcx-vis--hero", lead["title"])}'
            f'<span class="svcx-leadcap"><b>{lead["title"]}</b>'
            f'<span class="svcx-go">View service {icon("arrow")}</span></span></a></div>'
            f'<div class="svcx-col svcx-col--side">{_svcx_rail(t, rest, thumbs=True)}'
            f'{_svcx_more(t, items, overflow)}</div></div>')

def _svcx_editorial(t, items, overflow):
    """02. Numbered editorial list beside a large panel; the active row swaps
    the panel to that service's own photograph."""
    return (f'<div class="svcx svcx--editorial">'
            f'<div class="svcx-col">{_svcx_head(t, "sec-head--left")}'
            f'{_svcx_rail(t, items, numbered=True, big=True)}'
            f'{_svcx_more(t, items, overflow)}</div>'
            f'{_svcx_stack(t, items, "svcx-vis--tall svcx-vis--sticky")}'
            f'</div>')

def _svcx_spotlight(t, items, overflow):
    """08. Sticky visual anchored while the service list advances beside it."""
    return (f'<div class="svcx svcx--spotlight">'
            f'{_svcx_stack(t, items, "svcx-vis--tall svcx-vis--sticky")}'
            f'<div class="svcx-col">{_svcx_head(t, "sec-head--left")}'
            f'{_svcx_rail(t, items, big=True)}{_svcx_more(t, items, overflow)}</div></div>')

def _svcx_floating(t, items, overflow):
    """10. Offset image plane with the service stack layered across it.

    Replaces the old text-chip carousel: under a one-image rule those cards had
    no imagery and read as exactly the boxed grid this section should avoid."""
    return (f'<div class="svcx svcx--floating">'
            f'{_svcx_stack(t, items, "svcx-vis--float")}'
            f'<div class="svcx-stack">{_svcx_head(t, "sec-head--left")}'
            f'{_svcx_rail(t, items, big=True)}{_svcx_more(t, items, overflow)}</div></div>')

def _svcx_bento(t, items, overflow):
    """03. The image sets the hierarchy; supporting blocks stay unequal."""
    lead, rest = items[0], items[1:]
    blocks = []
    for i, it in enumerate(rest):
        size = "b" if i == 0 else "c"
        blocks.append(f'<a class="svcx-blk svcx-blk--{size}" href="{it["url"]}">'
                      f'<span class="svcx-blk__im"><img src="/assets/photos/{it["img"]}" '
                      f'loading="lazy" alt="{it["title"]} in {esc(t["city"])}, '
                      f'{esc(t["st"])}"></span>'
                      f'<span class="svcx-blk__t"><h3>{it["title"]}</h3>'
                      f'<p>{esc(clean_text(it["blurb"]))}</p>'
                      f'<span class="svcx-go">{icon("arrow")}</span></span></a>')
    return (f'<div class="svcx svcx--bento">'
            f'<a class="svcx-blk svcx-blk--img" href="{lead["url"]}">'
            f'{_svcx_visual(t, lead["img"], "", lead["title"])}'
            f'<span class="svcx-blk__cap"><b>{lead["title"]}</b>'
            f'<span class="svcx-go">View service {icon("arrow")}</span></span></a>'
            f'{"".join(blocks)}</div>')

def _svcx_overlay(t, items, overflow):
    """06. The photograph is the section; navigation sits in a controlled layer."""
    pills = "".join(f'<a class="svcx-pill svcx-sel svcx-sel--{i+1}" href="{it["url"]}">'
                    f'{it["title"]}{icon("arrow")}</a>' for i, it in enumerate(items))
    eyebrow, h2, blurb = copy_deck(t, "services_head")
    return (f'<div class="svcx svcx--overlay">'
            f'{_svcx_stack(t, items, "svcx-vis--fill")}'
            f'<div class="svcx-over"><p class="eyebrow">{_city(eyebrow, t)}</p>'
            f'<h2>{_city(h2, t)}</h2><p class="svcx-over__p">{_city(blurb, t)}</p>'
            f'<div class="svcx-pills">{pills}</div></div></div>')

def _svcx_accordion(t, items, overflow):
    """07. One service open at a time; the open panel carries the visual.

    Native <details name=...> so the group is mutually exclusive and keyboard
    operable with no JS."""
    group = f'svcx-acc-{slugify(t["domain"])}'
    rows = []
    for i, it in enumerate(items):
        openattr = " open" if i == 0 else ""
        rows.append(
            f'<details class="svcx-acc" name="{group}"{openattr}>'
            f'<summary><span class="svcx-num">{i+1:02d}</span>'
            f'<span class="svcx-txt"><b>{it["title"]}</b></span>'
            f'<span class="svcx-caret">{icon("arrow")}</span></summary>'
            f'<div class="svcx-acc__b">'
            f'{_svcx_visual(t, it["img"], "svcx-vis--hero", it["title"])}'
            f'<div class="svcx-acc__t"><p>{esc(clean_text(it["blurb"]))}</p>'
            f'<a class="btn btn--primary" href="{it["url"]}">'
            f'View service {icon("arrow")}</a></div></div></details>')
    return (f'<div class="svcx svcx--accordion">'
            f'{_svcx_head(t, "sec-head--left svcx-hd")}'
            f'<div class="svcx-accs">{"".join(rows)}'
            f'{_svcx_more(t, items, overflow)}</div></div>')

def _svcx_timeline(t, items, overflow):
    """11. Service journey. The steps read as an ordered route through the work
    rather than a menu, and the step you are on owns the photograph.

    The numbering is sequence, not ranking -- _svc_items already orders real
    service pages first, so the route follows the business's own priorities. No
    stage names are invented; every step is a real service."""
    group, n = _svcx_group(t), len(items)
    steps = "".join(
        f'<li class="svcx-step">{_svcx_radio(group, i + 1, i == 0)}'
        f'{_svcx_pick(group, i + 1, it["title"])}'
        f'<span class="svcx-step__n">{i + 1:02d}</span>'
        f'<span class="svcx-step__t">{it["title"]}</span>'
        f'<span class="svcx-step__d">{esc(clean_text(it["blurb"]))}</span>'
        f'{_svcx_nav(it, "Service", sel=i + 1)}</li>'
        for i, it in enumerate(items))
    return (f'<div class="svcx svcx--timeline" style="--svcx-n:{n}">'
            f'{_svcx_head(t, "sec-head--left svcx-hd")}'
            f'{_svcx_stack(t, items, "svcx-vis--journey")}'
            f'<ol class="svcx-steps">{steps}</ol>'
            f'{_svcx_more(t, items, overflow)}</div>')

def _svcx_typo(t, items, overflow):
    """12. The service names ARE the artwork. Type carries the section and the
    photograph reveals behind the engaged word.

    The names are the headline, so the section heading is demoted to a kicker
    bar -- a 40px h2 above a 56px list of the same words is two headlines
    fighting, which is what made the first cut of this read badly. The index is
    set to the LEFT as part of the type, not as a floating circle to the right.

    Editorial rather than four large buttons: the words are unboxed, ruled only
    by hairlines, and the active one is the only thing that gains weight."""
    group = _svcx_group(t)
    eyebrow, h2, blurb = copy_deck(t, "services_head")
    head = (f'<div class="svcx-kick"><div><p class="eyebrow">{_city(eyebrow, t)}</p>'
            f'<h2>{_city(h2, t)}</h2></div>'
            f'<p class="svcx-kick__p">{_city(blurb, t)}</p></div>')
    words = "".join(
        f'<li class="svcx-word">{_svcx_radio(group, i + 1, i == 0)}'
        f'{_svcx_pick(group, i + 1, it["title"])}'
        f'{_svcx_dot(group, i + 1, it["title"], "svcx-word__i")}'
        f'<a class="svcx-nav svcx-sel svcx-sel--{i + 1} svcx-word__t" '
        f'href="{it["url"]}">{it["title"]}</a></li>'
        for i, it in enumerate(items))
    return (f'<div class="svcx svcx--typo">{head}'
            f'<ul class="svcx-words">{words}</ul>'
            f'<div class="svcx-reveal">'
            f'{_svcx_stack(t, items, "svcx-vis--reveal")}'
            f'{_svcx_copystack(t, items)}</div>'
            f'{_svcx_more(t, items, overflow)}</div>')

def _svcx_orbit(t, items, overflow):
    """13. Services arranged around the work itself. Art-directed, not a
    compass rose: the nodes sit on an ellipse that is deliberately off-centre,
    and the count decides the arc rather than forcing a perfect diagram.

    Below 900px the ring is abandoned entirely for a scroll-snap selector -- a
    circle of tap targets on a phone is a worse control, not a smaller one."""
    group, n = _svcx_group(t), len(items)
    nodes = "".join(
        f'<li class="svcx-node svcx-node--{i + 1}" style="--i:{i + 1}">'
        f'{_svcx_radio(group, i + 1, i == 0)}'
        f'{_svcx_dot(group, i + 1, it["title"], "svcx-node__n")}'
        f'<a class="svcx-nav svcx-sel svcx-sel--{i + 1} svcx-node__t" '
        f'href="{it["url"]}">{it["title"]}</a></li>'
        for i, it in enumerate(items))
    return (f'<div class="svcx svcx--orbit" style="--svcx-n:{n}">'
            f'{_svcx_head(t, "sec-head--left svcx-hd")}'
            f'<div class="svcx-ring">'
            f'{_svcx_stack(t, items, "svcx-vis--core")}'
            f'<ul class="svcx-nodes">{nodes}</ul></div>'
            f'<div class="svcx-orbit__b">{_svcx_copystack(t, items)}'
            f'{_svcx_more(t, items, overflow)}</div></div>')

def _svcx_tabs(t, items, overflow):
    """14. Tab bar over a split panel. Adapted from the client's "Services 05:
    Tabs + Image" design.

    The tab is a selector, NOT a link -- a tab that navigates away is the wrong
    affordance. The real link is the panel's "View service", one tap from any
    tab, which is also what the source design does with its CTA button.

    The reference pairs each panel with a 2x2 checklist of sub-features; the
    content model has no per-service sub-features, so that block is dropped
    rather than filled with invented copy."""
    group = _svcx_group(t)
    tabs = "".join(
        f'<li class="svcx-tab">{_svcx_radio(group, i + 1, i == 0)}'
        f'<label class="svcx-sel svcx-sel--{i + 1} svcx-tab__l" '
        f'for="{group}-{i + 1}">{it["title"]}</label></li>'
        for i, it in enumerate(items))
    return (f'<div class="svcx svcx--tabs">'
            f'{_svcx_head(t, "svcx-tabs__hd")}'
            f'<div class="svcx-tabs"><ul class="svcx-tabs__in">{tabs}</ul></div>'
            f'<div class="svcx-panel">'
            f'<div class="svcx-panel__t">{_svcx_copystack(t, items)}'
            f'{_svcx_more(t, items, overflow)}</div>'
            f'{_svcx_stack(t, items, "svcx-vis--tab")}</div></div>')

def _svcx_problem(t, items, overflow):
    """09. Symptom -> service, with the image as the anchor. Only reachable when
    the copy genuinely carries symptom language; nothing is invented."""
    rows = "".join(
        f'<a class="svcx-pc" href="{it["url"]}">'
        f'<b>{esc(clean_text(_symptom_phrase(it["sym"])))}</b>'
        f'<span class="svcx-ans">{icon("arrow")}{it["title"]}</span></a>'
        for it in items if it["sym"])
    return (f'<div class="svcx svcx--problem">'
            f'{_svcx_visual(t, _svcx_primary(t, items), "svcx-vis--hero")}'
            f'<div class="svcx-col"><div class="svcx-pcs">{rows}</div></div></div>')

def why_us(t):
    cells = "".join(f'<div class="feat"><div class="ic">{icon(ic)}</div><div class="feat__b"><h3>{h}</h3><p>{d}</p></div></div>'
                    for ic, h, d in copy_deck(t, "why_items"))
    eyebrow, h2 = copy_deck(t, "why_head")
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">{_city(eyebrow, t)}</p><h2>{_city(h2, t)}</h2></div>'
            f'<div class="grid g3 feats feats--{t["layout"]["feats"]}">{cells}</div></div></section>')

def how_it_works(t):
    style = t["layout"]["steps"]
    eyebrow, h2 = copy_deck(t, "steps_head")
    steps = "".join(f'<div class="step"><div class="step__b"><h3>{_city(h, t)}</h3>'
                    f'<p>{_city(p, t)}</p></div></div>' for h, p in copy_deck(t, "steps"))
    return (f'<section class="sec sec--soft"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">{_city(eyebrow, t)}</p><h2>{_city(h2, t)}</h2></div>'
            f'<div class="steps steps--{style}">{steps}</div></div></section>')

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
            + (f'<a class="btn btn--ghost" href="tel:{t["tel"]}">{icon("phone")}Call now</a>'
               if t.get("phone") else "")
            + '</div></div></section>')

def areas_band(t, pages):
    areas = [p for u, p in pages.items() if p["cat"] == "area"]
    if not areas:
        return ""
    chips = "".join(f'<a href="{p["url"]}">{esc(area_label(p))}</a>' for p in areas[:16])
    eyebrow, h2, blurb = copy_deck(t, "areas_head")
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">{_city(eyebrow, t)}</p><h2>{_city(h2, t)}</h2>'
            f'<p>{_city(blurb, t)}</p></div>'
            f'<div class="areas">{chips}<a class="areas__all" href="/service-areas/">View all areas {icon("arrow")}</a></div></div></section>')

def cta_band(t, heading=None):
    ch, with_phone, without_phone = copy_deck(t, "cta")
    # heading is raw here -- the caller may pass one, and it is esc()'d below,
    # so substitute the unescaped city rather than going through _city()
    heading = heading or ch.replace("{city}", t["city"])
    lead = _city(with_phone if t.get("phone") else without_phone, t)
    second = ('<a class="btn btn--ghost" href="/request-a-quote/">Request a Quote</a>'
              if t.get("phone") else
              '<a class="btn btn--ghost" href="/services/">See Our Services</a>')
    return (f'<section class="sec"><div class="wrap"><div class="cta-band"><h2>{esc(heading)}</h2>'
            f'<p>{lead}</p>'
            f'<div class="cta">{call_btn(t, "btn btn--primary", "Request a Quote")}'
            f'{second}</div></div></div></section>')

def home_faqs(t):
    """Fallback FAQ when the content pack supplies none.

    Currently fires on 0 of the 10 built sites, but it is what the other 991
    registered domains will show the moment they get thin content -- so it is
    decked like everything else rather than being one fixed set."""
    c = t["city"]
    decks = [
        [(f"Do you offer same-day garage door repair in {c}?",
          f"Yes — most repair calls in {c} are handled the same or next day. Broken springs and doors stuck open are prioritized."),
         ("How much does a garage door repair cost?",
          "It depends on the part — a spring, cable, roller or opener are all different jobs. You get a written price on site before any work starts."),
         ("Should I replace or repair an older door?",
          "If the door is original to a house from the 80s or 90s and the panels or track are failing, replacement often makes more sense than repeated repairs. We'll tell you honestly which one fits."),
         ("Is replacing a garage door spring something I can do myself?",
          "No. Torsion springs are wound under high tension and can cause serious injury. It's the one job we always recommend leaving to a tech with the right tools.")],
        [("How fast can someone get out to me?",
          f"Most {c} repair calls are same or next day. A door stuck open is treated as urgent — it's a security problem, not just an inconvenience."),
         ("Will I know the price before you start?",
          "Yes. The tech diagnoses the door, writes down the price for parts and labour, and waits for you to agree before opening a toolbox."),
         ("My door is noisy but still works. Worth a call?",
          "Usually yes, and it's cheaper then. Grinding or banging is normally rollers, hinges or tension — all far less work to fix before something snaps."),
         ("Do you charge extra for weekends?",
          "No. A Saturday call is priced the same as a weekday one.")],
        [("What's actually wrong when the door won't lift?",
          "Most often a broken torsion spring — the opener can't lift the door's full weight on its own. Sometimes it's a snapped cable or a jammed roller."),
         (f"Do you cover the whole {c} area?",
          f"We work across {c} and the surrounding suburbs daily. If you're not sure your street is in range, call and ask."),
         ("Can you match a single damaged panel?",
          "Sometimes. It depends on the door's make and age — older profiles get discontinued. We'll check before recommending a full replacement."),
         ("How long does a new door take to fit?",
          "Most single-door installs are a few hours once the door is in stock, including removing and disposing of the old one.")],
    ]
    return decks[_hash_idx(f'{t["domain"]}|copy|home_faqs', len(decks))]

# ---------------------------------------------------------------- pages
def home_sections(t, home, pages=None):
    """Render the homepage content JSON's `sections` array.

    This was the single largest source of sameness below the hero: every
    homepage JSON carries a `sections` array, `load_content()` parses it into
    pages["/"]["sections"], and `home_page()` then read only h1/title/meta/faq
    and dropped it. 1,786 words across the 9 content packs reached no built page
    -- including 927 words of researched, neighbourhood-level Dallas copy that
    appeared nowhere in dist/.

    Reuses the same helpers inner_page() already uses, so the markup and the
    heading humanisation match the rest of the site."""
    covered = set()
    if not home or not home.get("sections"):
        return "", covered
    blocks = []
    for i, s in enumerate(home["sections"]):
        h2 = humanize_heading(s.get("h2", ""))
        raw = s.get("body", "")
        if not raw.strip():
            continue
        html, concept = shape_section(t, h2, raw, i, pages)
        blocks.append(html)
        if concept:
            covered.add(concept)
    return "".join(blocks), covered


# ---- shaped rendering of the per-city prose -------------------------------
# These sections carry the only genuinely local material on the page -- named
# neighbourhoods with bearings and distances, household counts, median income,
# build-year windows, a call walkthrough. Rendering all of it as an
# undifferentiated column of grey paragraphs buried the data and read as a
# draft. Each block below detects the SHAPE of the prose and renders it with a
# component that already exists in the design system, falling back to prose
# whenever the shape isn't recognised.

_AREA_RE = re.compile(r"([A-Z][\w'’.-]*(?:\s+[A-Z][\w'’.-]*){0,3})\s*"
                      r"\((\d+)\s*(?:mi|mile|miles)\b[^)]*\)")

# (pattern, label) -- deliberately a small explicit table rather than generic
# number-scraping, so a figure never gets an invented label.
_FIGURES = [
    (re.compile(r"between\s+(\d{4})\s+and\s+(\d{4})"), "typical build years", "{0}–{1}"),
    (re.compile(r"([\d,]{4,})\s+households"), "households served", "{0}"),
    (re.compile(r"([\d,]{4,})\s+of those are owner-occupied"), "owner-occupied", "{0}"),
    # [\d,]*\d, not [\d,]{4,} -- the greedy form swallowed the sentence comma
    # after the figure and rendered "$83,256,"
    (re.compile(r"\$(\d[\d,]*\d)"), "median household income", "${0}"),
    (re.compile(r"(\d+)\s+named areas"), "neighbourhoods covered", "{0}"),
]

def _areas_block(t, h2, raw, pages=None):
    """Neighbourhood list -> a distance-ordered grid of links.

    Built from the site's actual area PAGES, not from names scraped out of the
    prose. The prose is the wrong source of truth twice over: it names places
    that have no page (Dallas mentions Farmers Branch, Sunnyvale, Wilmer, Heath
    and Oak Leaf, all of which truncated during generation and exist only as
    .partial.txt), and it omits places that do have one. Driving off `pages`
    guarantees every cell resolves, and gives all 26 Dallas area pages a
    homepage link -- 8 of them previously had exactly one inbound link, from the
    /service-areas/ index.

    Distances come from the prose where a name matches; cells without one simply
    show no badge."""
    dist = {n.strip().lower(): int(m) for n, m in _AREA_RE.findall(raw)}
    # Two separate conditions, and both matter. The prose must actually BE a
    # neighbourhood list (>=5 "Name (N mi)" mentions) -- guarding only on "this
    # site has area pages" made every section on the page render as an area
    # grid and silently dropped four sections' worth of copy.
    if len(dist) < 5:
        return None
    area_pages = [p for p in (pages or {}).values() if p["cat"] == "area"]
    if len(area_pages) < 5:
        return None
    found, claimed = [], set()
    for p in area_pages:
        label = area_label(p)
        low = label.lower()
        mi = dist.get(low)
        if mi is None:
            mi = next((v for k, v in dist.items() if k in low or low in k), None)
        found.append((label, mi, p["url"]))
        claimed.add(low)
    # Places the copy says we serve but that have no page yet (for Dallas these
    # are the 5 suburbs whose generation truncated into .partial.txt). Keep them
    # listed -- dropping them would quietly retract a coverage claim the business
    # makes -- but unlinked, so nothing points at a page that isn't there.
    for name, mi in sorted({(n.strip(), int(m)) for n, m in _AREA_RE.findall(raw)},
                           key=lambda x: x[1]):
        low = name.lower()
        if not any(low in c or c in low for c in claimed):
            found.append((name, mi, None))
            claimed.add(low)
    # nearest first; anything without a distance sorts to the end, alphabetically
    found.sort(key=lambda x: (x[1] is None, x[1] if x[1] is not None else 0, x[0]))
    # The grid replaces the enumeration, but keep the author's framing sentence --
    # dropping it lost the only human line in the section.
    intro = raw.split(":")[0].strip() if ":" in raw.split("\n\n")[0] else ""
    lead = (f'<p class="areagrid__lead">{esc(clean_text(intro))}.</p>'
            if 4 < len(intro.split()) < 40 else "")
    tail = _AREA_RE.sub("", raw).split("\n\n")[-1].strip(" .,-")
    def _cell(n, m, url):
        inner = (f'<span class="an">{esc(n)}</span>'
                 + (f'<span class="ad">{m} mi</span>' if m is not None else ""))
        # no page yet -> a plain span, never a link to a 404
        body = f'<a href="{url}">{inner}</a>' if url else f'<span class="nolink">{inner}</span>'
        return f"<li>{body}</li>"
    cells = "".join(_cell(n, m, url) for n, m, url in found)
    note = f'<p class="areagrid__note">{esc(clean_text(tail))}.</p>' if len(tail.split()) > 6 else ""
    return (f'<section class="sec sec--soft"><div class="wrap">'
            f'<div class="sec-head"><p class="eyebrow">{_city("Around {city}", t)}</p>'
            f'<h2 id="{slugify(h2)}">{esc(h2)}</h2>{lead}</div>'
            f'<ul class="areagrid">{cells}</ul>{note}</div></section>')

def _figures_block(t, h2, raw):
    """Pull the hard numbers out of the paragraph and lead with them."""
    tiles = []
    for rx, label, fmt in _FIGURES:
        m = rx.search(raw)
        if m:
            tiles.append((fmt.format(*m.groups()), label))
    if len(tiles) < 3:
        return None
    cells = "".join(f'<div class="lstat"><b>{esc(v)}</b><span>{esc(l)}</span></div>'
                    for v, l in tiles)
    return (f'<section class="sec"><div class="wrap">'
            f'<div class="sec-head"><p class="eyebrow">{_city("{city} housing stock", t)}</p>'
            f'<h2 id="{slugify(h2)}">{esc(h2)}</h2></div>'
            f'<div class="lstats">{cells}</div>'
            f'<div class="localcopy">{render_body(raw)}</div></div></section>')

def _process_block(t, h2, raw):
    """A walkthrough -> the numbered step component the engine already ships."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    if not (2 < len(paras) <= 5):
        return None
    style = t["layout"]["steps"]
    lead = ["What you tell us", "What we check on site", "What happens next",
            "If a part has to come in", "Before we leave"]
    steps = "".join(f'<div class="step"><div class="step__b"><h3>{esc(lead[i])}</h3>'
                    f'<p>{esc(clean_text(p))}</p></div></div>'
                    for i, p in enumerate(paras))
    return (f'<section class="sec sec--soft"><div class="wrap">'
            f'<div class="sec-head"><p class="eyebrow">{_city("A {city} call, start to finish", t)}</p>'
            f'<h2 id="{slugify(h2)}">{esc(h2)}</h2></div>'
            f'<div class="steps steps--{style}">{steps}</div></div></section>')

# Vocabularies for the two remaining prose shapes. Terms are only surfaced when
# they actually appear in the copy -- nothing is invented, and the order follows
# the order the author mentioned them, which in this corpus is deliberate
# ("the most common call ... behind that ...").
_PARTS = [("torsion spring", "Torsion springs"), ("extension spring", "Extension springs"),
          ("roller", "Rollers"), ("cable", "Cables"), ("circuit board", "Opener boards"),
          ("opener", "Openers"), ("panel", "Panels"), ("track", "Track"),
          ("hinge", "Hinges"), ("sensor", "Safety sensors"), ("drum", "Drums")]
_FACTORS = [("door weight", "Door weight"), ("spring size", "Spring size"),
            ("cable condition", "Cable condition"), ("door's age", "Door age"),
            ("age of the stock", "Door age"), ("normal supply", "Parts availability"),
            ("track needs adjustment", "Track alignment"),
            ("one spring is going or both", "One spring or two"),
            ("opener is original", "Original vs replaced opener")]

def _terms_in(raw, vocab, minimum):
    """Vocabulary terms present in the copy, in order of first mention."""
    hits = []
    low = raw.lower()
    for needle, label in vocab:
        i = low.find(needle)
        if i >= 0 and label not in [h[1] for h in hits]:
            hits.append((i, label))
    hits.sort()
    return [l for _, l in hits] if len(hits) >= minimum else []

def _ranked_block(t, h2, raw, vocab, eyebrow, numbered, minimum=3):
    """Surface the named items as a scannable list beside the prose.

    Rendering these as a solid paragraph buried the actual answer -- a reader
    scanning for "what breaks on my door" had to read 210 words to find it."""
    terms = _terms_in(raw, vocab, minimum)
    if not terms:
        return None
    items = "".join(
        f'<li>{f"<span class=rk>{i+1}</span>" if numbered else ""}'
        f'<span>{esc(x)}</span></li>' for i, x in enumerate(terms))
    return (f'<section class="sec"><div class="wrap">'
            f'<div class="sec-head"><p class="eyebrow">{_city(eyebrow, t)}</p>'
            f'<h2 id="{slugify(h2)}">{esc(h2)}</h2></div>'
            f'<div class="splitcopy">'
            f'<ul class="ranklist{" ranklist--n" if numbered else ""}">{items}</ul>'
            f'<div class="localcopy">{render_body(raw)}</div></div></div></section>')

def photo_band(t):
    """Full-bleed image band with an overlaid claim.

    Between the services grid and the footer the page ran eleven consecutive
    text sections with no imagery at all -- a wall no one scrolls. This is the
    visual beat that breaks it, and it uses photos that were already being
    copied into every site and never referenced."""
    gal = t.get("gallery") or []
    if len(gal) < 3:
        return ""
    head, sub = copy_deck(t, "photo_band")
    # A strip, not a single full-bleed background. The pool is close-up work
    # shots; cropping one of those to a 1280x420 banner reliably produced a wall
    # and the back of someone's head. Three images at a sane aspect ratio are
    # forgiving of composition and show more of the work besides.
    shots = "".join(
        f'<figure><img src="/assets/photos/{g}" loading="lazy" '
        f'alt="Garage door work in {esc(t["city"])}, {esc(t["st"])}"></figure>'
        for g in gal[:3])
    return (f'<section class="sec sec--soft"><div class="wrap">'
            f'<div class="sec-head"><p class="eyebrow">{_city("On the tools", t)}</p>'
            f'<h2>{_city(head, t)}</h2><p>{_city(sub, t)}</p></div>'
            f'<div class="shots">{shots}</div></div></section>')

# ---- VISUAL PROOF: the slot directly after the services grid ---------------
# Adapted from the client's "visual proof" design set. One variant renders per
# site, chosen deterministically, so 1000 homepages do not all show the same
# three-up photo strip. Each variant declares which downstream copy deck it
# consumes so the page never makes the same claim twice.

PROOF_VARIANTS = ["photoband", "detail", "technician", "cinematic", "sequence"]
# variant -> the slot it eats further down the page
_PROOF_EATS = {"technician": "split", "cinematic": "split", "sequence": "process"}

def _gal(t, n=1):
    """(filename, truthful category label) pairs from the gallery pool."""
    g = t.get("gallery") or []
    c = t.get("gallery_cat") or []
    out = [(g[i], c[i] if i < len(c) else "Garage door work") for i in range(len(g))]
    return out[:n]

def _pf_shell(inner, cls=""):
    """Must open with the literal `<section class="sec` -- band() rewrites the
    tint by page position and skips anything that does not match."""
    return (f'<section class="sec"><div class="wrap{(" " + cls) if cls else ""}">'
            f'{inner}</div></section>')

def _pf_alt(t, label):
    return f'{esc(label)} work in {esc(t["city"])}, {esc(t["st"])}'

def _pf_photoband(t):
    """00. The original three-up strip, kept as one variant of five."""
    shots = "".join(
        f'<figure><img src="/assets/photos/{g}" loading="lazy" '
        f'alt="{_pf_alt(t, lab)}"></figure>' for g, lab in _gal(t, 3))
    head, sub = copy_deck(t, "photo_band")
    return _pf_shell(
        f'<div class="sec-head"><p class="eyebrow">{_city("On the tools", t)}</p>'
        f'<h2>{_city(head, t)}</h2><p>{_city(sub, t)}</p></div>'
        f'<div class="shots">{shots}</div>')

def _pf_detail(t):
    """03. One large photograph beside a short editorial column."""
    g, lab = _gal(t, 1)[0]
    head, sub = copy_deck(t, "photo_band")
    return _pf_shell(
        f'<div class="pf-detail__img"><img src="/assets/photos/{g}" loading="lazy" '
        f'alt="{_pf_alt(t, lab)}"></div>'
        f'<div class="pf-detail__b"><p class="eyebrow">{_city("On the tools", t)}</p>'
        f'<h2>{_city(head, t)}</h2><span class="pf-rule"></span>'
        f'<p>{_city(sub, t)}</p>'
        f'<a class="pf-go" href="/services/">See what we work on {icon("arrow")}</a>'
        f'</div>', "pf-detail")

def _pf_points(t, points):
    return "".join(
        f'<li><span class="pf-ic">{icon("check")}</span>'
        f'<span class="pf-pt"><b>{_city(p, t)}</b></span></li>' for p in points)

def _pf_technician(t):
    """04. Wide photograph with the claim column offset into the last columns."""
    g, lab = _gal(t, 1)[0]
    head, sub, points = copy_deck(t, "split_feature")
    return _pf_shell(
        f'<div class="pf-tech__img"><img src="/assets/photos/{g}" loading="lazy" '
        f'alt="{_pf_alt(t, lab)}"></div>'
        f'<div class="pf-tech__b"><h2>{_city(head, t)}</h2>'
        f'<p>{_city(sub, t)}</p>'
        f'<ul class="pf-points">{_pf_points(t, points)}</ul></div>', "pf-tech")

def _pf_cinematic(t):
    """01. Tall photograph carrying the section, claims as a ruled rail."""
    g, lab = _gal(t, 1)[0]
    head, sub, points = copy_deck(t, "split_feature")
    return _pf_shell(
        f'<div class="sec-head sec-head--left pf-cine__hd"><h2>{_city(head, t)}</h2>'
        f'<p>{_city(sub, t)}</p></div>'
        f'<div class="pf-cine__img"><img src="/assets/photos/{g}" loading="lazy" '
        f'alt="{_pf_alt(t, lab)}"></div>'
        f'<ul class="pf-points pf-points--rail">{_pf_points(t, points)}</ul>',
        "pf-cine")

def _pf_sequence(t):
    """05. The job as an ordered strip, one photograph per stage.

    Three stages, not the reference's four: COPY["steps"] holds three
    (title, body) pairs and no fourth stage is invented to fill the grid."""
    eyebrow, h2 = copy_deck(t, "steps_head")
    steps = copy_deck(t, "steps")
    shots = _gal(t, len(steps))
    if len(shots) < len(steps):
        return ""
    cells = "".join(
        f'<li class="pf-step"><span class="pf-step__n">{i + 1:02d}</span>'
        f'<span class="pf-step__im"><img src="/assets/photos/{shots[i][0]}" '
        f'loading="lazy" alt="{_pf_alt(t, shots[i][1])}"></span>'
        f'<h3>{_city(title, t)}</h3><p>{_city(body, t)}</p></li>'
        for i, (title, body) in enumerate(steps))
    return _pf_shell(
        f'<div class="sec-head sec-head--left"><p class="eyebrow">{_city(eyebrow, t)}</p>'
        f'<h2>{_city(h2, t)}</h2></div>'
        f'<ol class="pf-seq" style="--pf-n:{len(steps)}">{cells}</ol>')

def proof_section(t):
    """Pick the visual-proof variant. Returns (html, decks_consumed).

    Deterministic on the domain, and gated on how many gallery photographs the
    site actually has -- the strip needs three, everything else needs one."""
    gal = t.get("gallery") or []
    if not gal:
        return "", set()
    pinned = (t.get("proof") or "").strip()
    if pinned and pinned in PROOF_VARIANTS:
        arch = pinned
    else:
        ok = [v for v in PROOF_VARIANTS
              if not (v == "photoband" and len(gal) < 3)
              and not (v == "sequence" and len(gal) < len(copy_deck(t, "steps")))]
        arch = ok[_hash_idx(f'{t["domain"]}|proof', len(ok))] if ok else "detail"
    html = globals()[f"_pf_{arch}"](t)
    if not html:
        return "", set()
    eats = _PROOF_EATS.get(arch)
    return html, ({eats} if eats else set())

def split_feature(t):
    """Image beside a short claim + checklist. A second, quieter visual beat."""
    gal = t.get("gallery") or []
    if len(gal) < 2:
        return ""
    img = gal[_hash_idx(f'{t["domain"]}|split', len(gal))]
    head, sub, points = copy_deck(t, "split_feature")
    lis = "".join(f'<li>{icon("check")}<span>{_city(p, t)}</span></li>' for p in points)
    flip = " splitfeat--flip" if _hash_idx(f'{t["domain"]}|splitside', 2) else ""
    return (f'<section class="sec"><div class="wrap splitfeat{flip}">'
            f'<div class="splitfeat__img"><img src="/assets/photos/{img}" '
            f'alt="Garage door work in {esc(t["city"])}, {esc(t["st"])}" loading="lazy"></div>'
            f'<div class="splitfeat__b"><h2>{_city(head, t)}</h2><p>{_city(sub, t)}</p>'
            f'<ul class="checklist">{lis}</ul></div></div></section>')

def pull_quote(t, home):
    """An editorial pull-quote lifted from the site's OWN copy.

    Deliberately not a testimonial: no customer is quoted, nothing is invented.
    It gives the page the change of typographic register a testimonial would,
    using a sentence the business actually wrote about itself."""
    if not home or not home.get("sections"):
        return ""
    cands = []
    for s in home["sections"]:
        for sent in re.split(r"(?<=[.!?])\s+", str(s.get("body", ""))):
            w = len(sent.split())
            if 12 <= w <= 32 and not _AREA_RE.search(sent) and "$" not in sent:
                cands.append(sent.strip())
    if not cands:
        return ""
    q = cands[_hash_idx(f'{t["domain"]}|pullquote', len(cands))]
    return (f'<section class="sec sec--soft"><div class="wrap"><blockquote class="pullq">'
            f'<p>{esc(clean_text(q))}</p><cite>{esc(t["brand"])}</cite></blockquote></div></section>')

def reviews_band(t):
    """Customer reviews -- rendered ONLY from real supplied data.

    sites.json may carry a `reviews_list` of {quote, name, area}. Nothing is
    generated: fabricating reviews for a local trade business misleads consumers
    and is exactly the kind of claim these sites cannot back up. 0 of 1001 sites
    supply this today, so the section renders nowhere until real data exists."""
    items = t.get("reviews_list") or []
    if not items:
        return ""
    cards = "".join(
        f'<figure class="rev"><blockquote>{esc(r.get("quote", ""))}</blockquote>'
        f'<figcaption>{esc(r.get("name", ""))}'
        + (f'<span>{esc(r["area"])}</span>' if r.get("area") else "")
        + "</figcaption></figure>" for r in items[:3])
    return (f'<section class="sec"><div class="wrap"><div class="sec-head">'
            f'<p class="eyebrow">In their words</p>'
            f'<h2>What {esc(t["city"])} customers say</h2></div>'
            f'<div class="revs">{cards}</div></div></section>')

def _prose_block(t, h2, raw, idx):
    """Fallback. Still not a plain column: the opening paragraph is set as a
    lead, and the rest sits in a measured column."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    if not paras:
        return ""
    lead = f'<p class="lead-para">{esc(clean_text(paras[0]))}</p>'
    rest = render_body("\n\n".join(paras[1:])) if len(paras) > 1 else ""
    return (f'<section class="sec"><div class="wrap"><div class="localcopy">'
            f'<h2 id="{slugify(h2)}">{esc(h2)}</h2>{lead}{rest}</div></div></section>')

def shape_section(t, h2, raw, idx, pages=None):
    """Pick a component for this section based on what the prose actually is.

    Returns (html, concept). The concept lets home_page() drop the generic band
    that would otherwise say the same thing again -- the page was rendering
    "Around Dallas / Areas We Cover" and "Coverage / Around Dallas" as two
    separate sections, and both a "How a Call Goes" and a "How It Works"."""
    out = _areas_block(t, h2, raw, pages)
    if out:
        return out, "areas"
    out = _figures_block(t, h2, raw)
    if out:
        return out, "housing" 
    if re.search(r"how .*(call|it works|we work)|call goes|what happens|the process|step",
                 h2, re.I):
        out = _process_block(t, h2, raw)
        if out:
            return out, "process" 
    if re.search(r"fix|repair|common|problem|fail|see most", h2, re.I):
        out = _ranked_block(t, h2, raw, _PARTS, "Most common {city} calls", True)
        if out:
            return out, "faults" 
    if re.search(r"cost|price|pricing|quote|charge", h2, re.I):
        out = _ranked_block(t, h2, raw, _FACTORS, "What moves the price", False)
        if out:
            return out, "pricing" 
    return _prose_block(t, h2, raw, idx), None

def home_page(t, pages):
    home = pages.get("/")
    h1 = (home["h1"] if home else "") or f"Garage Door Repair & Installation in {t['city']}, {t['st']}"
    lead = (home["meta"] if home else "") or (
        f"Local garage door repair, spring and opener service and new-door installation across {t['city']} "
        f"and the surrounding metro — same-day service, licensed techs, upfront pricing.")
    local, local_covered = home_sections(t, home, pages)
    faqs = home["faq"] if (home and home["faq"]) else home_faqs(t)
    faq_eyebrow, faq_h2 = copy_deck(t, "faq_head")
    faq_html = (f'<section class="sec sec--soft"><div class="wrap"><div class="sec-head">'
                f'<p class="eyebrow">{_city(faq_eyebrow, t)}</p><h2>{_city(faq_h2, t)}</h2></div>'
                f'<div class="faq">{faq_accordion(faqs)}</div></div></section>')
    title = seo_title((home["title"] if home else "") or f"Garage Door Repair in {t['city']}, {t['st']} | {t['brand']}")
    desc = (home["meta"] if home else "") or lead
    schemas = [org_schema(t), faq_schema(faqs)]
    hero_img = t.get("hero_img") or HERO_IMG
    top = (head_html(t, title, desc, "/", schemas, og_image=hero_img) + header(t, pages)
           + hero(t, h1, lead, img=hero_img) + trust_bar(t))
    # Section ORDER was identical on all 1001 sites -- the strongest structural
    # fingerprint left after the copy decks. Each running order below keeps the
    # page coherent (services before the proof points that justify them, FAQ and
    # CTA last) while genuinely changing what you meet first.
    # Section order follows the buyer's questions rather than a free shuffle.
    # Someone with a door stuck open at 8am asks, in this order: can you fix
    # this / does the work look competent / why you / what will actually happen
    # to me / do you know my area / will I be overcharged / what do others say /
    # my specific worry / how do I start. Earlier versions shuffled all seven
    # slots freely, which produced pages that opened on a price explainer.
    #
    # Variation now happens WITHIN compatible slots, and the visual beats are
    # fixed points -- the page previously ran eleven straight text sections
    # after the services grid with no imagery at all.
    # the visual-proof variant is chosen ONCE, before the block map, because
    # some variants consume a copy deck a later slot would otherwise repeat --
    # the same claim twice on one page is the defect this guards against
    proof_html, proof_eats = proof_section(t)
    covered = local_covered | proof_eats
    blocks = {
        "services": lambda: services_grid(t, pages),
        "band":     lambda: proof_html,
        "why":      lambda: (why_us_split(t) if t.get("home") == "showcase" else why_us(t)),
        "steps":    lambda: "" if "process" in covered else how_it_works(t),
        "split":    lambda: "" if "split" in covered else split_feature(t),
        "local":    lambda: local,
        "areas":    lambda: "" if "areas" in covered else areas_band(t, pages),
        "quote":    lambda: pull_quote(t, home),
        "reviews":  lambda: reviews_band(t),
        "contact":  lambda: contact_band(t),
        "faq":      lambda: faq_html,
    }
    # (slot, [interchangeable options]) -- the sequence is fixed, the content of
    # a few slots rotates per domain.
    # "" means the slot may be skipped on this domain. Fixing the sequence
    # outright made every page structurally near-identical (DOM similarity rose
    # to 76%), so variation now comes from which optional beats appear and from
    # two swaps that are defensible either way -- never from moving a slot
    # somewhere that breaks the reasoning above.
    plan = [
        ["services"],
        ["band"],                                   # visual proof
        ["why", "split"],                           # differentiation
        ["steps"],                                  # what will happen to me
        ["split", "quote", ""],                     # second visual / tonal beat
        ["local"],                                  # genuine local expertise
        ["areas"],                                  # NOT optional: "where do you
                                                    # work" is the second thing a
                                                    # local customer checks. Making
                                                    # this skippable dropped the
                                                    # coverage section from 5 of 7
                                                    # sites entirely.
        ["reviews", "quote", ""],                   # social proof, data-gated
        ["faq"],                                    # objection handling
        ["contact", ""],                            # convert (cta_band always follows)
    ]
    order, used = [], set()
    for i, options in enumerate(plan):
        pick = options[_hash_idx(f'{t["domain"]}|slot{i}', len(options))]
        if pick in used:                            # never render a slot twice
            pick = next((o for o in options if o and o not in used), "")
        if pick:
            order.append(pick); used.add(pick)
    # Two swaps that do not change the argument the page makes: whether the
    # differentiation or the walkthrough comes first, and whether the local
    # detail or the coverage list leads the "do you know my area" pair.
    def _swap(a, b, salt):
        if a in order and b in order and _hash_idx(f'{t["domain"]}|{salt}', 2):
            i, j = order.index(a), order.index(b)
            order[i], order[j] = order[j], order[i]
    _swap("why", "steps", "swap1")
    _swap("local", "areas", "swap2")
    if t.get("home") == "showcase" and "why" in order:
        order = ["why"] + [k for k in order if k != "why"]
    mid = band(t, [blocks[k]() for k in order]) + cta_band(t)
    return top + mid + footer(t, pages) + "</body></html>"

def band(t, sections):
    """Apply the tinted/plain rhythm positionally.

    Each renderer used to hardcode whether its section was tinted, which made
    the sequence identical everywhere *and* breaks once sections are reordered
    (two tinted bands land next to each other). Deciding here keeps the rhythm
    correct for any order, and the starting parity varies per site."""
    flat = t.get("layout", {}).get("bands") == "flat"
    out, i = [], _hash_idx(f'{t["domain"]}|bandstart', 2)
    for s in sections:
        if not s:
            continue
        if s.startswith('<section class="sec'):
            tinted = (not flat) and (i % 2 == 1)
            s = s.replace('<section class="sec sec--soft"', '<section class="sec"', 1)
            if tinted:
                s = s.replace('<section class="sec"', '<section class="sec sec--soft"', 1)
            i += 1
        out.append(s)
    return "".join(out)

ARTICLE_LAYOUTS = ["", "article--left", "article--wide"]

def article_layout(t):
    """Prose/sidebar arrangement for inner and trust pages."""
    return ARTICLE_LAYOUTS[_hash_idx(f'{t["domain"]}|article', len(ARTICLE_LAYOUTS))]

def quote_card(t):
    """Sidebar quote card, shared by inner and trust pages.

    Was two near-identical hardcoded blocks, so every inner page on every site
    carried the same three lines."""
    head, sub, second_label, second_href = copy_deck(t, "qcard")
    return (f'<aside class="aside"><div class="qcard">{icon("phone")}<h3>{_city(head, t)}</h3>'
            f'<p>{_city(sub, t)}</p>'
            f'{tel_link(t, "tel")}'
            f'<a class="btn btn--primary" href="/request-a-quote/">Request a Quote</a>'
            f'<a class="btn btn--outline" href="{second_href}">{second_label}</a></div></aside>')

def inner_page(t, p, pages):
    h1 = p["h1"] or area_label(p)
    img = (t.get("inner_imgs") or {}).get(p["url"]) or INNER_IMGS[_stable_idx(p["slug"] or p["url"], len(INNER_IMGS))]
    parts = []
    # the photo used to sit after the first section on every page of every site
    img_after = _hash_idx(f'{t["domain"]}|innerimg', max(1, min(3, len(p["sections"]))))
    for idx, sec in enumerate(p["sections"]):
        h2 = sec.get("h2", "")
        parts.append(f'<h2 id="{slugify(h2)}">{esc(humanize_heading(h2))}</h2>{render_body(sec.get("body", ""))}')
        if idx == img_after:
            parts.append(f'<img src="/assets/photos/{img}" alt="{esc(h1)}" loading="lazy">')
    if not any("<img" in x for x in parts):
        parts.append(f'<img src="/assets/photos/{img}" alt="{esc(h1)}" loading="lazy">')
    if p["faq"]:
        _, faq_h2 = copy_deck(t, "faq_head")
        parts.append(f'<h2 id="faq">{_city(faq_h2, t)}</h2><div class="faq">{faq_accordion(p["faq"])}</div>')

    label = {"service": "Services", "area": "Service Areas", "guide": "Guides"}.get(p["cat"], "")
    parent = {"service": "/services/", "area": "/service-areas/", "guide": "/guides/"}.get(p["cat"], "/")
    crumb = f'<div class="crumb"><a href="/">Home</a> › <a href="{parent}">{label}</a> › {esc(h1)}</div>'
    aside = quote_card(t)
    art = article_layout(t)
    body = (f'<section class="page-hero"><div class="wrap">{crumb}<h1>{esc(h1)}</h1></div></section>'
            f'<div class="wrap"><div class="article {art}"><div class="body">{"".join(parts)}</div>{aside}</div></div>'
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
            f'<div class="grid g3 feats feats--{t["layout"]["feats"]}">{cards}</div></div></section>'
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
    aside = quote_card(t)
    body = (f'<section class="page-hero"><div class="wrap">{crumb}<h1>{esc(h1)}</h1></div></section>{embed}'
            f'<div class="wrap"><div class="article {article_layout(t)}"><div class="body">{parts}</div>{aside}</div></div>'
            + cta_band(t))
    schemas = [org_schema(t), breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (head_html(t, seo_title(f"{h1} | {t['brand']}"), f"{h1} — {t['brand']}, {t['city']}, {t['st']}.", url, schemas,
                       og_image=t.get("hero_img") or HERO_IMG)
            + header(t, pages) + body + footer(t, pages, is_quote) + "</body></html>")

# ---------------------------------------------------------------- renderer dispatch
# The default "garage" design is the module functions above. Alternate full designs
# (ironclad / volt / nimbus) live in templates.py and expose the same interface.
GARAGE = {"css": lambda t: css(t) + GD_CSS + btn_css(t), "navjs": NAVJS,
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

def build(only=None):
    """Render every registered domain that has content.

    `only` (a list of domains) rebuilds just those and leaves the rest of dist/
    in place -- otherwise every verification run wipes all 202 pages to inspect
    one of them."""
    targets = {d: t for d, t in SITES.items() if not only or d in only}
    if only:
        for d in only:
            if d not in SITES:
                print(f"  ! unknown domain '{d}' (not in config/sites.json)")
        for d in targets:
            shutil.rmtree(os.path.join(DIST, d), ignore_errors=True)
    elif os.path.exists(DIST):
        shutil.rmtree(DIST)
    for domain, t in targets.items():
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
        (t["hero_img"], t["card_imgs"], t["inner_imgs"],
         t["gallery"], t["gallery_cat"]) = select_photos(t, pages, photos)
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
             f"Whether it's a door that won't open this morning or a replacement you've been putting off, {t['brand']} is {reach_phrase(t)}. "
             + (f"Reach us at {t['phone']} for same-day service on most repairs, or request a written quote"
                if t.get("phone") else
                "Request a written quote for same-day service on most repairs")
             + " and we'll tell you honestly what your door needs - nothing more."),
        ]))
        write(out, "/contact/", R["trust"](t, pages, "/contact/", f"Contact {t['brand']}", [
            ("Get in touch",
             (f"Call {t['phone']} to reach {t['brand']} for garage door repair, service or a new-door quote in {t['city']}, {t['st']}."
              if t.get("phone") else
              f"Request a quote to reach {t['brand']} for garage door repair, service or a new-door quote in {t['city']}, {t['st']}.")),
            ("Service area",
             f"We serve {t['city']} and the surrounding suburbs. Not sure if you're in range? "
             + ("Call and ask — we'll tell you straight." if t.get("phone")
                else "Ask when you request a quote — we'll tell you straight."))]))
        write(out, "/request-a-quote/", R["trust"](t, pages, "/request-a-quote/", f"Request a Garage Door Quote in {t['city']}", [
            # No site has a form (`ghl_form_id` is unset on all 1001), so the copy
            # must not promise one, and with no phone on file it must not render
            # "Call  or use the form." with an empty gap where the number should be.
            ("Tell us what the door is doing",
             "Describe the problem — noise, off-track, a broken spring, or a door you want replaced — and we'll give you a written price."
             + (f" Call {t['phone']} to get started." if t.get("phone") else "")),
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
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    print(f"Building {', '.join(only) if only else 'garage-door sites'}...")
    build(only)
