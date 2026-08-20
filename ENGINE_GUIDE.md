# Garage Door Site Engine — Guide & Folder Structure

A data-driven static-site generator that turns per-city JSON content into a full,
SEO-optimized garage-door-company website. One engine, one command, hundreds of
domains — each with its own theme, layout, logo and content.

This doc replaces the old scattered docs (`ENGINE_GUIDE.md`, `QUICK_START.md`,
`DELIVERABLES.md`, etc.) with one accurate reference, audited directly against the
current code (2026-08-17).

> **Before you deploy anything:** set a lead-capture path. 999 of 1001 domains have a
> blank `phone`, and `form_action` is unset, so `build.py` prints a warning naming every
> site a visitor cannot contact. See §10.

---

## 1. Repo folder structure

```
garagedoorsites/
├── domains.csv                  1000 purchased domains: Domain, Business Name, City, State, Primary Color
├── _demo5.json                  domains that have generator-created demo content (see §5.2)
│
├── brand/
│   ├── logos/                   200 pre-made 200x200 PNG emblems, named "<row#>_<business_slug>.png"
│   │                            (row# = its line in domains.csv). Now also holds a
│   │                            "<domain>-emblem.png" + "<domain>-favicon.png" copy per mapped
│   │                            domain, written by the new `logo_prep.py` (see §8) so build.py
│   │                            picks them up. Only domains.csv rows 1-200 have a source emblem;
│   │                            the other 800 still fall back to the generated SVG mark.
│   └── photos/                  the real photo source (265 .webp). GD HERO/v1 = 30 city-named
│                                heroes (matched by city slug), GD HERO/v2 = 20 generic heroes
│                                (fallback pool, picked by domain hash) + per-service pools
│                                (GD REPAIR / INSTALLATION / SERVICE / MAINTENNANCE — sic) + 5
│                                per-guide-topic pools under GD GUIDE/. build.py's
│                                select_photos() picks the hero, 6 service cards, 6 door-style
│                                tiles, 1 local-conditions shot and one photo per inner page.
│                                engine/assets_shared/photos/gd-*.jpg is only the fallback.
│                                NOTE: build.py resolves brand/ at either <repo>/brand or
│                                <repo>/engine/brand and says which it used — keep ONE copy.
│
├── <city>-tx/, dallas-tx/...    raw content drops at repo root (zip extractions with __MACOSX/ junk) —
│                                a staging area content is copied FROM into engine/content/<slug>/
│
├── variants/                    5 hand-built, standalone alt-design HTML mockups (site1..site5 +
│                                ironclad/volt/nimbus). Static reference files, not part of the
│                                JSON→build pipeline. Not domain-registered or servable via engine.py.
│
└── engine/                      *** the actual engine — everything below lives here ***
    ├── engine.py                 CLI entrypoint (build / serve / logos / audit / new / bulk)
    ├── build.py                  *** the real renderer for garage-door sites (JSON content) ***
    ├── build_site.py              legacy renderer inherited from a sibling "Porta Pros" (portable
    │                              toilet rental) engine — markdown-content based. build.py imports
    │                              only its shared CSS/nav-JS/icon helpers; it does not render
    │                              garage-door pages itself. See §7.
    ├── templates.py               9 selectable alt full-site designs (ironclad / nimbus /
    │                              forge / coastline / beacon / atlas / hearth / quarry /
    │                              verdant), selected per-site via sites.json "template".
    │                              Plus the shared chrome + page skeleton + section blocks
    │                              every design is built from. See §4.2. ("garage", the 10th
    │                              design, is the default and lives in build.py. volt was
    │                              retired and removed.)
    ├── layouts.py                 layout-rotation helper for `engine.py bulk` — dead/orphaned,
    │                              see §7
    ├── scaffold.py                leftover from the porta-potty sibling project (hardcoded path to
    │                              a different repo's ledger file) — do not use, see §7
    ├── logo_gen.py                generates a unique geometric SVG→PNG logo per domain from its
    │                              name (deterministic hash) — a fallback generator, not what's
    │                              actually used today (see §8)
    ├── logo_prep.py               maps the 200 pre-made brand/logos/<row#>_<slug>.png files to
    │                              the per-domain names build.py looks for (<domain>-emblem.png,
    │                              <domain>-favicon.png), knocking out the white background and
    │                              tight-cropping to the artwork, and writes _logo_manifest.json
    │                              ({domain: kind,w,h}) so the header can size each mark by its
    │                              real aspect ratio. This is what `engine.py logos` calls.
    ├── make_demo_content.py       one-off script that fills content/ for the domains listed in
    │                              ../_demo5.json with placeholder copy (used to seed the 10 demo
    │                              sites — see §5.2)
    ├── audit_seo.py                SEO/AEO/GEO signal report over dist/
    ├── serve.py                    local preview server: portal on :8000 (directory listing — see
    │                               §7) + each site on its own config port
    │
    ├── config/
    │   ├── sites.json             *** the registry — one entry per domain *** (1001 entries;
    │   │                          domain, city, st, content, brand, tagline, area, street, zip,
    │   │                          phone, theme, layout, port[, template][, home][, form_action]).
    │   │                          Also a top-level "defaults" object merged underneath every
    │   │                          entry — set form_action there once for all 1000+ domains (§10.1).
    │   ├── themes.json             1097 named colour+font themes: {p, pd, accent, on_accent,
    │   │                          display, body, fonts}. Looked up by sites.json "theme" key.
    │   └── layouts.json             6 named structural layouts (aurora / meridian / cobalt /
    │                                harbor / summit / monarch): hero/nav/shape/bands/footer/
    │                                cards/feats/steps. Looked up by sites.json "layout" key.
    │
    ├── content/<slug>/            *** per-city JSON content, one folder per unique "content" value
    │   │                          in sites.json ***. Only 9 of 1001 registered domains (10 site
    │   │                          entries — Dallas content is reused by 2 domains) currently have
    │   │                          a content folder; build.py skips every other domain.
    │   └── <prefix>-{home,svc-*,nb-*,sub-*,top-*}.json   (see §6 for the schema)
    │
    ├── assets_shared/photos/      gd-1.jpg … gd-9.jpg — the actual stock photo pool build.py
    │                              copies into every built site's /assets/photos/
    │
    └── dist/<domain>/             *** build output (gitignored, regenerated every build) ***
        ├── index.html, /services/, /service-areas/, /guides/, /about/, /contact/,
        │   /request-a-quote/       — all root-relative static HTML
        ├── assets/site.css, nav.js, favicon.svg, photos/
        └── sitemap.xml, robots.txt
```

### The two-tier config model

Nothing about an individual city is hard-coded in the renderer. Three JSON files
compose into one render:

```
sites.json["theme"]   → themes.json[theme]    (colours + fonts)
sites.json["layout"]  → layouts.json[layout]  (hero/nav/card/footer structure)
sites.json[domain]    → content/<content>/*.json   (the actual copy)
```

---

## 2. What actually renders a page (important — the README you might expect is stale)

There are **two renderers** in this folder, both reading `config/sites.json`:

| | `build.py` | `build_site.py` |
|---|---|---|
| Built for | **Garage-door sites (this business)** | A different, sibling niche — portable-toilet rental ("Porta Pros") |
| Content format | Structured **JSON** (`content/<slug>/*.json`) | **Markdown** (`content/<slug>/**/*.md`) |
| Generates `llms.txt` | No | Yes |
| Generates a portal `dist/index.html` | No | Yes |
| Status | **Actively used — this is the real build** | Legacy; only its CSS/nav-JS/icon helper functions are imported by `build.py` for shared styling |

**`python build.py` and `python engine.py build` are now equivalent** — `engine.py`'s
`build` subcommand used to call `build_site.build()` (the old markdown/porta-potty
path), which silently did nothing for JSON content in `content/`. Fixed 2026-08-17;
see §10.4.

`serve.py` and `audit_seo.py` are shared and fine to use via `engine.py serve` /
`engine.py audit` — they just read `dist/` and `config/sites.json`, independent of
which build script produced them.

---

## 3. The 10 sites — built and running now

I built every domain in `config/sites.json` that currently has a `content/` folder
(8 already had real content; I generated 2 more with `make_demo_content.py`,
described in §5.2, to round the demo set out to 10) and started the local preview
server. All 10 returned HTTP 200 and were spot-checked in-browser. Street/zip and
logo come from the two fixes in §8.

| # | Domain | City, ST | Design | Logo | Local URL |
|---|--------|----------|--------|:----:|-----------|
| 1 | dallasgaragedoor.com | Dallas, TX | `garage` (default) | generated mark | http://localhost:8201/ |
| 2 | mesagaragedoorco.com | Mesa, AZ | `verdant` | sheet lockup (3.0:1) | http://localhost:8203/ |
| 3 | napervillegaragedoorpros.com | Naperville, IL | `atlas` | sheet badge | http://localhost:8204/ |
| 4 | auroragaragedoorpros.com | Aurora, CO | `coastline` | sheet lockup (1.9:1) | http://localhost:8207/ |
| 5 | dallasdoorpros.com | Dallas, TX | `forge` | sheet badge | http://localhost:8219/ |
| 6 | boonegaragedoorpros.com | Boone, NC | `hearth` | sheet badge | http://localhost:8226/ |
| 7 | austingaragedoorguys.com | Austin, TX | `beacon` | sheet badge | http://localhost:8258/ |
| 8 | puntagordagaragedoorpros.com | Punta Gorda, FL | `nimbus` | sheet badge | http://localhost:8283/ |
| 9 | richmonddoorpros.com | Richmond, TX | `ironclad` | generated mark (row 758) | http://localhost:8959/ |
| 10 | pickeringtongaragedoorpros.com | Pickerington, OH | `quarry` | generated mark (row 975) | http://localhost:9176/ |

Every site now runs a **different design** (§4.2), and every site has a logo. The three
domains outside the 200-logo range use marks generated by `logo_gen.py`; the other seven
use the hand-made lockups mapped by `logo_prep.py`.

Addresses are unchanged from §8.2 — the rows flagged there still carry the sheet's
`disambiguation_risk: HIGH-use-verify_url` warning and should be verified before deploy.

Also reachable from another device on the same Wi-Fi at `http://192.168.1.64:<port>/`.

The portal at `http://localhost:8000/` is a plain directory listing of the 10 built
folders (not the styled portal page the old README describes — see §7, finding 4).

Server is running in the background (`python serve.py`, no-cache headers, Ctrl+C
equivalent is stopping the background task). Rebuilding (`python build.py`) wipes and
regenerates `dist/`; the running server picks up new files immediately since it
reads straight off disk.

---

## 4. Anatomy of one built page

Every site gets the same page set, generated from whatever `content/<slug>/*.json`
files exist:

- **Homepage** (`<prefix>-home.json`) — sticky header w/ mega-menu → hero → trust bar
  → 6-tile services grid → "why us" → 3-step "how it works" → service-areas list →
  FAQ accordion → CTA band → footer.
- **Service pages** (`<prefix>-svc-*.json` → `/services/<slug>/`)
- **Neighborhood/suburb pages** (`<prefix>-nb-*.json` / `-sub-*.json` → `/service-areas/<slug>/`)
- **Guide pages** (`<prefix>-top-*.json` → `/guides/<slug>/`)
- **Section indexes**: `/services/`, `/service-areas/`, `/guides/` (auto-generated if any pages of that type exist)
- **Trust pages**: `/about/`, `/contact/`, `/request-a-quote/` (copy is hard-coded in `build.py`, personalized with `{brand}`, `{city}`, `{phone}`). `/request-a-quote/` leads with the native lead-capture form when `form_action` is set — see §10.1.
- **`sitemap.xml`** and **`robots.txt`** (auto-generated from the actual page list)

SEO/AEO/GEO baked in automatically: `<title>` ≤ 60 chars, meta description,
canonical URL, OpenGraph + Twitter cards, single `<h1>`/page, `FAQPage` JSON-LD on
the homepage and every service page, `LocalBusiness` + `Service` + `BreadcrumbList`
JSON-LD `@graph`.

2 alternate full visual designs (**ironclad**, **nimbus** — see `templates.py`) can
replace the default "garage" design per-site via a `"template"` field in that site's
`sites.json` entry. A third, **volt** (dark/neon), was retired for reading too far
from the niche: its renderers are still in `templates.py` but it is no longer in
`REGISTRY`, so it can't be selected until that entry is put back.

### 4.1 Homepage stacks

The garage design builds its homepage from one of three stacks, chosen by the
optional `"home"` field in `sites.json`:

| `home` | Sections | Notes |
|---|---|---|
| *(unset)* / `expanded` | **17** | **The default.** Full stack, below. |
| `classic` | 8 | The original short stack (hero, trust, services, why-us, steps, areas, FAQ, CTA). |
| `showcase` | 8 | Swaps the why-us grid for the split+stats treatment. |

The expanded stack, in render order — hero, trust bar, services grid, symptom
finder, local conditions, why-us split, what-we-fix-most, repair-vs-replace,
how-it-works, door styles, emergency strip, maintenance tips, spring-safety
callout, service areas, guides teaser, FAQ, CTA band.

Four of those render the city's **own** copy out of `<city>-home.json`'s
`sections[]`, which the pre-2026-08 homepage loaded and then discarded:

| Section | home JSON `h2` key (first match wins) |
|---|---|
| Local conditions | `the_area_and_its_housing`, else `why_local_matters` |
| What we fix most here | `what_we_fix_most_here` |
| How it works (intro) | `how_a_call_goes` |
| Service areas (prose) | `areas_we_cover` |

Each renders **nothing** when its city's JSON has none of those keys, so a thin
content folder yields a shorter page rather than a broken or padded one — the
demo-seeded cities land on 16 sections, Dallas on the full 17. Nothing in the
static sections invents reviews, counts, awards or certifications; `stats_band()`
and the review badge still render only from configured figures.

`contact_band()` remains in `build.py` but is deliberately unused — it duplicated
the closing CTA.

### 4.2 The ten designs

A site picks a design with `"template"` in `config/sites.json`. Omit the key and it
renders with `garage`, the default design in `build.py`. The other nine live in
`templates.py`:

| Design | Character | Display / body type | Homepage opens with |
|--------|-----------|---------------------|---------------------|
| `garage` | contractor default, image-overlay cards | Urbanist / Open Sans | photo hero, layout-driven |
| `ironclad` | editorial, cream + brass, hairline rules | Playfair Display / Inter | full-bleed photo, manifesto |
| `nimbus` | friendly, rounded, floating pill nav | Baloo 2 / Nunito | soft centred hero |
| `forge` | industrial, near-black steel, square corners | Oswald / Inter | dark photo + spec rail |
| `coastline` | airy editorial, wide margins | Fraunces / Karla | split text + tall photo |
| `beacon` | colour-block, oversized display caps | Anton / Inter | flat brand panel, no photo |
| `atlas` | corporate technical, dense, tabular | Roboto Slab / Roboto | compact banner + at-a-glance table |
| `hearth` | warm residential, rounded photo cards | Bitter / Nunito Sans | rounded hero card |
| `quarry` | utility, hard rules, mono labels | Space Grotesk / IBM Plex Mono | type-led, bordered photo slab |
| `verdant` | fresh geometric, pill accents | Sora / Inter | centred type over a photo band |

Colour is **not** part of the design. Each stylesheet declares `__P__`, `__PD__`,
`__ACCENT__` and `__ONACCENT__`, and `_paint()` substitutes the site's own theme
colours — derived from the brand hex in `domains.csv` — at build time. Two sites on
the same design still read as different companies, and each one matches its own logo.

**Shared chrome.** Every alt design uses one header/footer/nav implementation
(`_chrome_header` / `_chrome_footer` / `CHROME_JS` / `CHROME_CSS`). The design's
stylesheet themes the `.tc-*` classes; it does not re-implement them. This is
deliberate — see §10.6 for what re-typing the nav per design had produced.

**Shared page skeleton.** Designs after `ironclad`/`nimbus` build their inner, index
and trust pages from `_gen_inner` / `_gen_index` / `_gen_trust` (classes `.pg-*`) and
compose their homepages from the section blocks in `templates.py` (`hb_services`,
`hb_steps`, `hb_signals`, `hb_areas`, `hb_guides`, `hb_faq`, `hb_cta`, classes
`.hb-*`). Identity comes from the stylesheet, the chrome, the bespoke hero and the
**order** the blocks are composed in — each design uses a different one.

Adding an eleventh design is: fonts constant + CSS constant + a `*_home()` function,
then one line in `REGISTRY` via `_design(...)`.

---

## 5. How to create sites in bulk

### 5.1 One-time setup

```bash
cd engine
pip install Pillow          # only needed for logo_gen.py
```

### 5.2 The full bulk pipeline

**Step 1 — register domains into `config/sites.json`.**
All 1000 domains from `domains.csv` are already registered (each gets an
auto-derived, contrast-safe theme from its `Primary Color` column, a round-robin
layout, and the next free port). To re-run against an updated sheet:

```bash
python engine.py bulk --sheet ../domains.csv
```
This is idempotent — it skips domains already in `sites.json`. Registering a domain
does **not** build it; `build.py` silently skips any domain with no `content/`
folder.

**Step 2 — get content into `content/<slug>/`.**
This is the actual bottleneck: 991 of the 1001 registered domains have no content
yet, and there's no bulk *real* content generator checked in. Two ways content gets
in today:

- **Placeholder/demo content**, generator-written, good for previews/QA — the
  pattern used for all 10 sites currently live. See `make_demo_content.py`: it
  reads a list of domains from `../_demo5.json` and writes 9 boilerplate JSON files
  per domain (home + 3 services + 3 neighborhoods + 2 guides) using the domain's
  `city`/`st`/`brand` already in `sites.json`. To generate more:
  ```bash
  # add the domains you want to ../_demo5.json (a flat JSON array), then:
  python make_demo_content.py
  ```
  This script is hard-wired to `_demo5.json` — for a real bulk run, copy it and
  point it at whatever domain list you're processing, or extend it to take a CLI arg.

- **Real, per-city written content** (what Dallas has, 41 pages instead of 15) —
  dropped in as a folder of `<prefix>-{home,svc,nb,sub,top}-*.json` files matching
  the schema in §6, one directory per `content` value in `sites.json`. This is how
  the repo's raw `dallas-tx/dallas-tx/*.json` staging drop got copied into
  `engine/content/dallas-tx/`. There's no generator for this in-repo — it's produced
  outside the engine (LLM content generation pipeline, `.partial.txt` files hint at
  an interrupted generation run) and just needs to land in the right folder,
  named right.

**Step 3 — wire up logos.**
```bash
python engine.py logos      # or: python logo_prep.py
```
Maps the 200 pre-made `brand/logos/<row#>_<slug>.png` emblems to the
`<domain>-emblem.png` / `<domain>-favicon.png` filenames `build.py` looks for
(non-destructive — copies, doesn't rename the originals). Domains outside
rows 1-200 have no source emblem yet; for those, `logo_gen.py ../domains.csv
--out ../brand/logos` generates a unique geometric mark per domain instead — just
note its output filenames (`<domain>-mark.png`, …) don't match `build.py`'s lookup,
so it needs the same kind of copy/rename step `logo_prep.py` does before it'll show
up on a built site. See §8.1 for what was actually fixed here.

**Step 4 — build.**
```bash
python build.py
```
Wipes `dist/` and re-renders every registered domain that has a `content/` folder.
Prints one line per site built and one `skip <domain>: content/... not found` per
domain still missing content — that's expected until content lands for it.

**Step 5 — preview.**
```bash
python engine.py serve
# or: python serve.py
```
Portal-style directory listing on `:8000`, each built site on its own port from
`sites.json`. Reachable on your LAN too (see the printed IP).

**Step 6 — audit.**
```bash
python engine.py audit
```
Prints per-site SEO/AEO/GEO signal counts (title/meta-desc length issues, canonical
+ OG + Twitter coverage, H1 count, alt-text coverage, FAQ page count, JSON-LD types
present, avg words/links per page). Good smoke test after any content or template
change before deploying.

**Step 7 — deploy** (per the original README's convention — verify it still matches
your hosting setup before relying on it):
```bash
git -C <domain> checkout --orphan main
git -C <domain> rm -rf . >/dev/null 2>&1
cp -r dist/<domain>/. <domain>/
git -C <domain> add -A && git -C <domain> commit -m "Deploy site"
git -C <domain> push -u origin main
git -C <domain> checkout content
```
Each `dist/<domain>/` is fully self-contained with root-relative links, so it can be
hosted at the domain root as-is.

### 5.3 Adding a single new site (not bulk)

```bash
python engine.py new somedomain.com --city "Somewhere" --st TX --area 555 \
    --street "1 Main St" --zip 75001 --tagline "Repair · Install · Service"
# --city/--st/--brand/--color auto-fill from domains.csv if the domain is a row there
```
Then add its `content/<slug>/` folder and run `build.py`.

---

## 6. Content JSON schema

Filename encodes the page type: `<prefix>-home.json`, `-svc-<slug>.json`,
`-nb-<slug>.json` / `-sub-<slug>.json`, `-top-<slug>.json`.

```jsonc
{
  "title": "Garage Door Repair in Mesa, AZ | Mesa Garage Door Co",   // <title>, trimmed to ≤60 chars
  "meta": "Local garage door repair...",                             // meta description
  "h1": "Garage Door Repair & Installation in Mesa, AZ",
  "sections": [
    { "h2": "what_we_do", "body": "paragraph text.\n\n- bullet\n- bullet" }
    // h2 keys are snake_case; humanized to Title Case at render time.
    // body: \n\n-separated paragraphs; a block of "- " lines renders as <ul>.
  ],
  "faq": [ { "q": "...", "a": "..." } ],   // → FAQ accordion + FAQPage JSON-LD
  "schema_facts": { "areaServed": "Mesa, AZ and surrounding communities" }
}
```
`_run.json` and any `*.partial.txt` in a content folder are ignored by the build
(the latter are leftover incomplete-generation artifacts, not real content).

---

## 7. Audit findings — things to know before relying on this engine

1. ~~**`engine.py build` is wrong for this niche.**~~ **Fixed 2026-08-17** — `cmd_build`
   called `build_site.build()` (the markdown-based porta-potty renderer) instead of
   `build.py`'s own `build()`. It now does `import build; build.build()`, so
   `engine.py build` and `python build.py` are equivalent.

2. ~~**`engine.py logos` is broken.**~~ **Fixed in this pass** — `cmd_logos` did
   `import logo_prep`, but no `logo_prep.py` existed (only `logo_gen.py`), so it
   raised `ModuleNotFoundError`. Added `engine/logo_prep.py` (see §8.1); `engine.py
   logos` now works.

3. ~~**No built site currently shows a real brand logo.**~~ **Fixed for 200/1000
   domains in this pass** — `build.py` looks for `brand/logos/<domain>-emblem.png`
   (+ `-emblem-light.png`, `-lockup.png`, `-favicon.png`), but the 200 pre-made
   files in `brand/logos/` were named `<row#>_<business-name-slug>.png` (e.g.
   `02_mesa_garage_door_co.png`) with no domain in the filename, and `logo_gen.py`
   (the in-repo generator) used a third naming scheme that *also* didn't match.
   `logo_prep.py` bridges this by copying each numbered emblem to its domain-named
   twin using the `#` column in `domains.csv` as the join key. Domains outside rows
   1-200 (800 of the 1000) still have no source emblem and fall back to the
   generated SVG mark — either get more emblems made, or run `logo_gen.py` for
   them (see §5.2 step 3).

4. **The `:8000` portal page is gone.** The old styled portal (`write_portal()`) is
   part of `build_site.py`, which `build.py` never calls, and `build.py` also
   `shutil.rmtree()`s the whole `dist/` at the start of every build — so any old
   `dist/index.html` from a prior `build_site.py` run gets deleted too. `:8000`
   now serves Python's default directory listing. Harmless for local preview, just
   don't expect the fancy portal.

5. **`llms.txt` isn't generated by the active build.** The README's GEO section
   promises a generated `/llms.txt`; that's implemented only in `build_site.py`
   (`write_llms`), which the garage-door pipeline doesn't call. `audit_seo.py`
   correctly reports `llms.txt=False` for every site as a result — not a bug in the
   audit, just an unshipped README promise.

6. **`scaffold.py` is not usable here.** It hardcodes
   `C:\Users\Masud\Desktop\setu\otofc\portapotty\sites-porta-potty\ledger\brand_ledger.jsonl`
   — a different sibling project's file — and defaults taglines to `"{city}
   Rentals"`. It's a copy-paste leftover from the porta-potty engine. Use
   `engine.py new` / `engine.py bulk` instead, which are written for this niche.

7. **`layouts.py`'s per-domain layout rotation looks disconnected.** Its
   `get_layout_for_site()` produces a `hero/services/testimonials/cta/footer`
   dict with a *different* value vocabulary than what `config/layouts.json`
   actually stores (`hero/nav/shape/bands/footer/cards/feats/steps`, keyed by
   layout *name*, not by domain). `build.py` only ever does
   `layouts.get(site["layout"])` — a name lookup — so even if `engine.py bulk`
   wrote a per-domain `"layouts": [...]` list into `layouts.json` (via
   `layouts.py`), `build.py` would never read it. In practice every site's layout
   comes from the round-robin `LAYOUTS = ["aurora","meridian","cobalt","harbor",
   "summit","monarch"]` list, not from `layouts.py`.

8. ~~**`brand/photos/*.webp`** aren't referenced by `build.py` at all.~~ **Stale —
   they are now the primary photo source.** `select_photos()` maps the 30 city hero
   shots by city slug, and picks per-service, per-guide and per-inner-page images
   deterministically from the category folders (`GD REPAIR`, `GD INSTALLATION`,
   `GD SERVICE`, `GD MAINTENNANCE`, `GD GUIDE/*`). `assets_shared/photos/gd-*.jpg`
   is now only the fallback for a gap — mainly the hero on a city with no matching
   shot, which is still ~970 of the 1000 domains.

9. **`config/themes.json`'s `_comment` field** still says "Design themes for the
   Porta Pros engine" — cosmetic, but another sign large parts of this repo were
   forked from that sibling project without a full pass to re-label things.

10. **`engine.py bulk` crashes on every run — `KeyError: 'layouts'`.** Reproduced
    2026-08-18. `cmd_bulk` loads `config/layouts.json` (which has no `"layouts"`
    key — it is a dict of *named* layout variants) and then does
    `layouts["layouts"].append(...)` for the first unregistered domain. It raises
    before writing anything, so `sites.json` and `themes.json` are left untouched:
    the command is a total no-op, not a partial one. This is the documented path
    for registering the remaining ~990 domains, so it blocks bulk onboarding.
    Fix is a `setdefault("layouts", [])` — but see finding 7 first: the per-domain
    list it wants to write is read by nothing.

None of the above blocks the documented bulk workflow in §5 except finding 10 —
`build.py`, `serve.py`, `audit_seo.py` and `engine.py new` all work as described. The
remaining issues are in the parts of the asset pipeline that silently do the wrong
thing rather than error loudly.

---

## 10. The 2026-08-17 fix pass

A full audit of the built output (10 sites, 202 pages, verified in-browser at 375 /
700 / 1000 / 1280 px) found the engine structurally sound — 0 broken internal links,
one `<h1>` per page, alt text on every image, complete JSON-LD, and all 54
layout × home-stack × template combinations rendering without exception — but with a
set of real defects, all fixed below.

### 10.1 Conversion — the blocking one

**Nothing on any built site could capture a lead.** 999 of 1001 registered domains
have a blank `phone`, and `build.py` built its dial link as `"+1" + digits(phone)` with
no guard, so every page carried ~6 `<a href="tel:+1"></a>` links — empty, unlabelled,
dialling nothing. Separately, `<form>` count across all 202 pages was **zero**: the
quote page only emitted an embed when `ghl_form_id` was set, and that key was absent
from every entry.

Now:

- **`has_phone()` / `phone_link()` / `call_cta()` in `build.py`** gate every call
  affordance. With no number, the dial links are omitted and the primary CTA becomes
  the quote form. Prose that named the number (`"Call {phone} to reach…"`) routes
  through `_reach()` so it never renders a dangling "Call  .". The same guard was
  applied to `templates.py` (`_tel()` / `_quote()`), which had six unguarded `tel:`
  links of its own.
- **`quote_form()`** renders a real, native, accessible form — labelled fields, two
  required, a hidden `site`/`city` pair so you can tell which of 1000 domains a
  submission came from, and a `company` honeypot that only bots fill. No JS needed.
  It's shared by all four designs via `QFORM_CSS` (every custom property carries a
  fallback, because ironclad/volt/nimbus each define a different variable set).
- **`"defaults"` in `config/sites.json`** is a new top-level object merged underneath
  every site entry, so one `form_action` gives all 1000+ domains a working form
  instead of editing each. Any endpoint accepting a normal HTML POST works
  (Formspree, Netlify Forms, a GHL inbound webhook, your own handler).
- **`build.py` warns**, per build, naming every site with neither a phone nor a form
  endpoint.

`form_action` is deliberately left empty — the endpoint is yours to choose. Set it and
rebuild; verified working end to end (10/10 sites render the form, native validation
blocks an empty submit, single column and no horizontal overflow at 375px).

### 10.2 Navigation

- **Dropdowns were dead between 961px and 1120px.** The CSS switches to the burger
  panel at `max-width:1120px`, but `NAVJS` gated the submenu click-toggle on
  `matchMedia('(max-width:960px)')`. In that band the menu opened but Services /
  Service Areas / Guides could not be expanded at all. Both now read 1120px.
- **The header lost its gutter at two different widths** — `.hd` is also a `.wrap`, and
  both rules declared `padding` at equal specificity, so whichever came later in source
  won outright: below 561px the media-query `.wrap` stripped the 12px vertical padding,
  and between 561–1180px `.hd` stripped the 24px horizontal one (the logo sat flush at
  `left: 0`). A single `.wrap.hd` compound selector now states all four sides.
- The burger and the three dropdown triggers gained `aria-expanded` / `aria-controls`,
  kept in sync by `NAVJS`; Escape closes the panel and returns focus.

**The sticky navbar itself was already correct** and needed no change — `header.site`
(garage), `header` (ironclad) and `.navwrap` (nimbus) are all `position:sticky`, at
every breakpoint, on mobile and desktop. `html,body{overflow-x:clip}` is deliberate:
`clip` preserves sticky where `overflow-x:hidden` would break it. Don't "fix" that.

### 10.3 Alt templates (ironclad / nimbus / retired volt)

- Footers hard-coded **`© 2024`** while the garage design used `date.today().year`.
  Now `_year()`.
- They hard-coded three generic `gd-*.jpg` stock photos and never called
  `select_photos()`, so those sites shipped generic imagery while every garage-design
  site got the curated per-city set. Now `_hero()` / `_card()` / `_inner()`.
- They now render the shared quote form on `/request-a-quote/` too.

### 10.4 Tooling, SEO and a11y

- **`engine.py audit` crashed** on the first domain: `audit_seo.py` collected `@type`
  into a `set()`, but `org_schema()` emits a *list* (`["LocalBusiness",
  "HomeAndConstructionBusiness"]`) — `TypeError: unhashable type`. It printed nothing
  at all. Fixed, plus it now skips registered-but-unbuilt domains (was 991 empty
  blocks) and unescapes entities before measuring title/description length, which had
  been counting `&amp;` as five characters.
- **`engine.py build`** now calls the right renderer (see §7.1).
- **Duplicate `<title>` on 6 of 10 sites** — the homepage and
  `/services/garage-door-repair/` shipped identical titles, competing for the same
  query. `home_title()` picks the first non-colliding candidate that survives the
  60-char trim. 0 duplicates now, 0 length issues across all 10 sites.
- **`LocalBusiness` schema** no longer emits `"telephone": ""`, and no longer puts the
  city name in `streetAddress` when no street is on file — both are omitted instead.
- **A11y:** `<main id="main">` landmark and a skip link on all four designs, focus-visible
  rings, and the footer column headings are `<h3>` (they were `<h4>` directly after an
  `<h2>` — the one heading-level skip on every page).
- **Perf:** `width`/`height` on every photo (CLS), `decoding="async"`, `rel=preload` for
  the hero on all four designs, and `scroll-padding-top` so in-page anchors clear the
  sticky header. The mobile nav panel uses `100dvh` with a `100vh` fallback.

### 10.5 Known, not fixed — needs your input

- **Duplicate content.** `dallasgaragedoor.com` and `dallasdoorpros.com` build from the
  same content folder: 84.6% mean 8-word-shingle overlap across 41 shared URLs. The six
  demo-seeded cities are ~80% identical to each other. This is a content problem, not an
  engine one — see §5.2 step 2.
- **Phone numbers.** Only two domains have one, and both are placeholders
  (`(214) 000-0000` and a `555-` number).
- **Address quality.** Unchanged from §8.3 — 292 rows flagged `disambiguation_risk`, 46
  street addresses reused across different cities.
- **`llms.txt`** is still only in `build_site.py` (§7.5).

---

## 10.6 The 2026-08-18 pass — logos, ten designs, working navigation

### Logos: the 200 new files, rendered at their real shape

The refreshed `brand/logos/` set arrived as 200 numbered PNGs; the domain-named twins
`build.py` looks up did not exist, so every site had silently fallen back to the
generated SVG mark again. `logo_prep.py` was re-run, and rewritten while there:

- **Tight-crops to the alpha bounding box.** These arrive as artwork floating in a
  200×200 field of white. Cropping to the real ink is what lets the header size a logo
  by its artwork rather than its padding.
- **Writes `_logo_manifest.json`** — `{domain: {kind, w, h}}` — read once by `build.py`.
- **Knockout is vectorised** over channels instead of a 40 000-iteration Python loop
  per file.
- **Favicons are squared**, not stretched.

The rendering side then had to stop forcing every mark into a 40×40 box. The 200 files
range from **0.99:1 to 3.44:1**, and all of them draw the business name into the
artwork — so the header was showing a squashed, illegible wordmark *next to a text
repeat of the same name*. Now:

- `logo_box()` sizes from the file's real aspect ratio.
- A **horizontal lockup** (≥1.6:1 — Mesa, Aurora) stands alone; the text is dropped.
- A **square badge** (Naperville, Boone, Austin, Dallas Door Pros, Punta Gorda) is
  illegible at header height, so it keeps the text label and acts as the emblem —
  with the white chip box dropped, since a finished badge does not need one.
- `width`/`height` attributes carry real dimensions, so nothing reflows on load.

Three of the ten domains sit outside the 200-logo range (`dallasgaragedoor.com` is not
in the sheet at all); marks for those were generated with `logo_gen.py`.

### Photography

`select_photos()` already mapped `brand/photos/` correctly (finding 8 above is stale).
What was missing was the **homepages using it**: the new designs rendered as walls of
text, and `nimbus` used a repeated 🔧 emoji where a service photo belonged. Service
cards, guide cards and `ironclad`'s service rows now all carry the per-city, per-service
image `select_photos()` picked. Homepage image counts went from 2–3 to 9–20.

### The variants were mockups, and the designs inherited that

`variants/site1,3,4,5` are **single-page mockups** — every nav link is an in-page
`#anchor`, the phone numbers are hard-coded, and there are no inner pages. `ironclad`
and `nimbus` were ported from them and inherited mockup-grade chrome:

- dropdowns opened on `:hover` only — **no touch device could open a menu**
- the mobile panel linked to the three index pages, leaving ~30 pages per site
  unreachable on a phone
- burgers were inline `onclick` with no `aria-expanded`, `aria-controls` or label
- `_iron_js()` was a script that did nothing at all
- footers used `<a>f</a>`, `<a>IG</a>` — anchors with no `href`

**The default `garage` design had the same defect**, found while verifying: its mega
menus were `:hover`-only above 1120px, and `nav.js` only bound the trigger click below
that breakpoint. The triggers are `<button aria-haspopup>` elements, so a keyboard user
could tab to one, press Enter, and get nothing — and a desktop click did nothing either.
Fixed in `build_site.py` (`.open`/`:focus-within` rules, click bound at every width,
outside-click closes).

The alt designs now share **one** chrome (§4.2). It guarantees, for every design: every
content page reachable from the nav on desktop *and* mobile, dropdowns that open on
hover *and* click/tap/keyboard, correct aria throughout, Escape-to-close with focus
return, and no anchor without an `href`. A new design cannot reintroduce the mockup nav
without deliberately overriding structural CSS.

`volt` was deleted rather than left retired-in-place — it carried the pre-chrome markup
and would have been a working example of the pattern the module exists to prevent.

### Invented trust signals removed

`ironclad` hard-coded **"Est. 2004"** into every header, and rendered two five-star
"customer quotes" — one of which was the text of an FAQ answer, attributed to a
homeowner. Nobody said either. Both are gone; the block now renders the FAQ as an FAQ,
which is also what its `FAQPage` schema claims. The new section blocks assert no review
score, count, founding year, award or certification. The pre-existing
"Licensed & fully insured" / "Parts and labor warranty" lines in `build.py` are
untouched and still unverified per-site — see §7.

### Asset refresh (same day) — new photo set, and a caveat on the logos

`brand/` was replaced with a zip dropped in `photos/`. Two things came out of that:

- **The zip contains no logos** — 265 files, all `.webp`. Deleting `brand/` also removed
  the 200 logo PNGs, so they were restored from git (`git checkout -- brand/logos`) and
  re-derived with `logo_prep.py`. The numbered source files were never modified.
- **Photos are now foldered**, and heroes have their own directory:

      brand/photos/GD HERO/v1/     30 city-named shots  (<city>_garage_door.webp)
      brand/photos/GD HERO/v2/     20 generic shots     (garage-door-hero NN.webp)
      brand/photos/GD GUIDE/<topic>/   5 topics x 10
      brand/photos/GD REPAIR|INSTALLATION|SERVICE|MAINTENNANCE/   38-49 each

  `_CITY_HERO` now reads `GD HERO/v1`, and `HERO_POOL` holds the 20 generic shots.
  A city with its own photo gets it; every other city draws from the generic pool by a
  hash of its domain. That is the fix for the old behaviour where ~970 of the 1000
  domains would all have opened on the same `gd-4.jpg`.

  Note: one zip folder is named `"Noises "` with a trailing space, which Windows cannot
  create. The extractor strips whitespace from each path segment — which also matches
  the folder names `GUIDE_PHOTO_DIRS` already expects.

**Three of the ten domains have no logo in the 200-file set** — `dallasgaragedoor.com`
(not in `domains.csv` at all), `richmonddoorpros.com` (row 758) and
`pickeringtongaragedoorpros.com` (row 975). They render the engine's built-in SVG door
mark. Marks generated for them by `logo_gen.py` were deleted: a generated hexagon is not
this business's logo, and shipping one is worse than an honest placeholder.

### The quote form always renders

`quote_form()` used to return `""` when `form_action` was unset, so `/request-a-quote/`
was a page promising a written price with no form on it. It now always renders, on all
ten designs. Until an endpoint is configured the form is **inert**: no `action`
attribute, and submitting shows an inline notice instead of posting. That is deliberate
— a form that silently POSTs into the void is indistinguishable from a working one while
dropping every lead. Setting `form_action` (per site, or once in `defaults`) makes the
same markup live with no other change.

Two knock-on fixes came with it: the GHL-embed branch tested `not form` first and would
never have fired once the form always rendered, and the "What happens next" card — which
only ever appeared alongside a configured form — was an `h3` directly under the page
`h1`, so it started reporting as a heading-level skip the moment it began rendering.

### Brand asset location, logo visibility and the quote-form container

**One brand folder, resolved not assumed.** `brand/` existed at both `<repo>/brand/`
and `<repo>/engine/brand/`, which is a nasty trap: dropping a new logo into the copy
the build does *not* read is indistinguishable from the build ignoring your file.
`build.py` now resolves the location (`_brand_root`), prefers whichever copy holds more
files, breaks ties toward the repo root, and prints which one it used when both exist.
The duplicate `engine/brand/` (identical logos, plus a stale 200-file photo set with no
`GD HERO`) has been deleted.

**Logos on dark chrome.** The 200 logos are dark artwork on transparency, so on a dark
header or footer they disappeared into the background — `beacon`'s purple bar and
`forge`'s near-black footer both rendered an apparently empty space. Designs with dark
chrome now append `DARK_BAR_LOGO` / `DARK_FOOT_LOGO`, which put a white plate behind the
artwork. The plate targets `.tc-brand--lockup` / `.tc-brand__mark`, never `.tc-brand`
itself: those bars set `color:#fff`, so plating the whole link would have put white text
on a white box. The default design gets the same treatment via `.gf-logo:has(...)`.

**Footer brand.** `_chrome_brand(t, h, text=False)` renders the mark alone at 104px
(78px on mobile) with no business name beside it — the logo is legible at that size and
the name is already drawn into the artwork. The accessible name comes from the image's
alt text.

**The quote form had no container on seven designs.** `_quote_block` wraps itself in
`.wrap`, a class only `ironclad` and `nimbus` define. On the seven block-composed
designs `.wrap` resolved to `max-width:none; padding:0`, so the form ran the full
viewport width on desktop and sat flush against the screen edge on a phone. `PAGE_CSS`
now aliases `.wrap` to the same box as `.pg-wrap`. Measured after the fix: the form's
container starts at the same x as the page container (1180px, both at x=43 on a 1280px
viewport) and keeps a 28px gutter at 375px.

### Page FX: reveal on scroll, smooth scrolling, back to top

All three live in one shared module in `build.py` (`fx_css` / `FX_JS` / `FX_HEAD`,
`TOTOP_HTML`) and are injected by `write()`, the same way the action bar is. The
scroll-reveal previously sat inside the default design's `nav.js`, which meant the
nine alt designs had no entrance animation at all and no smooth scrolling; that copy
has been removed, so there is exactly one implementation.

- **Reveal.** An IntersectionObserver adds `.in` to elements tagged `.fx-r`, staggered
  up to 6 deep inside grids and lists. The selector list covers the default design's
  markup, the shared section blocks and page skeleton, and ironclad/nimbus's own
  sections.
- **Smooth scrolling** with `scroll-padding-top: 96px`, so an anchor target is never
  hidden behind the sticky header.
- **Back to top** appears past 600px, uses the site's brand colour, and sits above the
  mobile action bar via `body:has(.abar) .totop`. Clicking it also moves focus to the
  skip link -- scrolling a keyboard user to the top while leaving focus mid-page is a
  well-known trap.

Three properties that matter more than the effect itself:

1. `prefers-reduced-motion: reduce` disables **both** the reveal and the smooth scroll.
2. Content is only ever hidden when JS is actually running. The reveal styles are gated
   on `html.anim`, set by an inline `<head>` script, so with JS off or broken nothing is
   stuck at `opacity: 0`.
3. A 2.6s timeout calls `showAll()` regardless, so a failed observer cannot leave a page
   blank.

Verified across 202 pages: every page has the gate, exactly one back-to-top button and
one reveal pass, and zero elements left hidden. In-browser: the button appears on
scroll, is hit-testable, calls `scrollTo({top:0, behavior:'smooth'})`, hides again at
the top, and clears the mobile bar by 15px at 375px.

### Local conditions — the duplicate-content fix

`config/conditions.json` is the answer to the finding that has sat at the top of §10.5
since the first audit: a Boone page and a Mesa page saying the same thing with the city
name swapped. Conditions fix it at the source rather than by paraphrasing — an Arizona
site writes about heat and dust, a Minnesota site about freeze-thaw, so the pages differ
because the *subject* differs.

**Keyed by state, deliberately.** A state-level climate claim ("Arizona summers run long
and hot") holds for every city in that state. A city-level claim ("this town is in a Very
High Fire Hazard Severity Zone") is not something the engine can know for 1000 cities
without inventing it — so those live in the `cities` override block and appear only where
someone has actually checked. Two are seeded (`punta-gorda-fl` → coastal, `boone-nc` →
freeze); unlisted states fall back to `_default`.

Seven conditions ship: heat, freeze, storm, humidity, coastal, dust, seasonal. Each
carries a title, summary, four body paragraphs and two FAQ entries, with `{city}`/`{st}`
substituted at build time.

`condition_pages()` emits them in exactly the shape `load_content()` produces, so
navigation, the guides index, the sitemap, internal linking and FAQPage schema pick them
up with no special-casing. They are added with `setdefault`, so a hand-written page on
the same topic always wins.

**Measured effect.** Boone vs Mesa on the same generic guide: **96% similar**. Their
closest-matching condition guides: **4%**. Across the ten built homepages, pairs above
90% similarity went to **0 of 45**, the closest now 43%. Each site also gained three
~990-word guides (202 → 232 pages).

To extend: add a state to `states`, a condition to `conditions`, or a verified city to
`cities`. No code change.

### Per-site composition at scale

With ~1000 sites over ten designs, about a hundred sites share each design — and a shared
section order would make them the same page in different colours. `hb_stack()` orders the
explanatory middle of the homepage by a hash of the domain: deterministic, so a domain
always builds identically and diffs stay reviewable, but different from its neighbours.

Anchors stay fixed because they are not decoration — services near the top because it is
what the visitor came for, and areas → FAQ → CTA closing every page because that is the
conversion path. Each design also pins two blocks that suit it (atlas leads with
at-a-glance stats, hearth with a warm intro, quarry with symptoms and the safety notice),
so the shuffle never erases a design's identity. `drop` lets ironclad and nimbus skip the
blocks they render in their own markup.

### Verified

Rebuilt and checked in-browser at 375 px and 1280 px. Across 202 pages: **0 broken
internal links, 0 duplicate IDs, exactly one `<h1>` per page, 0 heading-level skips,
0 anchors without `href`, 0 unnamed buttons, 0 images without `alt` or dimensions, 0
horizontal overflow.** On every one of the ten sites each nav group was opened and a
menu link confirmed **hit-testable** via `elementFromPoint` — not merely present in the
DOM. Mobile: burger opens, all three accordion groups expand, 14–40 links reachable,
no tap target under 32 px.

`audit_seo.py` was also corrected: it counted a deliberate `alt=""` (a decorative image,
correct for the brand mark beside the visible business name) as a missing alt, and so
reported 30–82 false failures per site against markup that was already right.

---

## 8. Logo + address fixes applied in this pass, and an audit of the source sheet

### 8.1 Logos: `logo_prep.py`

Added `engine/logo_prep.py` (this is the module `engine.py logos` already tried, and
failed, to import). It joins `domains.csv`'s `#` column to the numbered files in
`brand/logos/` and copies each one to `<domain>-emblem.png` + `<domain>-favicon.png`
— the filenames `build.py` actually looks up. Ran it, then rebuilt: **7 of the 10
live sites now render their real brand emblem** (header, nav, favicon) instead of
the generated SVG door icon — see the table in §3. The other 3 (`dallasgaragedoor.com`,
`richmonddoorpros.com` row 758, `pickeringtongaragedoorpros.com` row 975) have no
source emblem because only `domains.csv` rows 1-200 have one made; they correctly
fall back to the SVG mark. Nothing was overwritten or renamed — the original
numbered files are untouched.

### 8.2 Addresses: found the real source

`domains.csv` has no address column, and there's no address data anywhere else in
this repo. The real source is a Google Sheet: **"Site Build Sheet"**
(`docs.google.com/spreadsheets/d/1WPfUt3ocl5VHaCVBG4cE8E4nIbi8SW8p`), which has two tabs:

- **Site Build Sheet** — `#, Domain (Purchased), Business Name, City, Address, State,
  Primary Color, Swatch`. 1000 rows, one per domain, `Address` as a single string
  (`"7303 S Hawes Rd, Mesa, AZ 85212"`).
- **GDR-1000-TAB1-CITIES** — a much richer *site-selection research* sheet, same
  1000 rows keyed by serial #, with `population`, `lat/lng`, a Google Maps
  `verify_url`, `disambiguation_risk`, `status` (research progress), `demand_per_mo`,
  `winnability`, and the two candidate `.com` names that were considered before one
  was purchased. This is clearly the working sheet the 1000 domains were originally
  picked from; the Site Build Sheet is a flattened export of the columns needed to
  build a site.

I parsed both tabs (1000/1000 rows each — see §8.3 for two parsing snags), split
`Address` into `street` + `zip` (dropping the redundant city/state, which sites.json
already carries separately), and **wrote `street`/`zip` into all 1000 matching
entries in `config/sites.json`** (not just the 10 built ones — every registered
domain has this data now, ready for whenever it builds). Rebuilt afterward, so the
`LocalBusiness` JSON-LD on the 9 sites with sheet data now carries a real
`streetAddress`/`postalCode` instead of falling back to `t["street"] or t["city"]`
(which had literally been putting the city name in the street-address field).
`dallasgaragedoor.com` isn't in the sheet (it was added manually, outside the
1000-domain batch) and was correctly left blank rather than guessed.

**Before treating any of this as production-ready NAP data**, read §8.3 — a
meaningful chunk of these addresses are flagged by the sheet's own QA column as
needing manual verification, and some are reused across multiple different cities.

### 8.3 Auditing the sheet itself

- **292 of 1000 rows (29.2%) are flagged `disambiguation_risk: HIGH-use-verify_url`.**
  This means the city name is shared with other US cities/places and the
  geocoded address may not be reliable without checking the sheet's own
  `verify_url` (a Google Maps link at the row's lat/lng). 5 of our 9 addressed demo
  sites fall in this bucket (marked ⚠️ in §3's table) — worth a manual check before
  this goes anywhere public, since a wrong `LocalBusiness` address is a real local-SEO
  and trust problem, not just cosmetic.
- **46 distinct street addresses are reused across 2+ different city/domain rows**
  (e.g. `7303 S Hawes Rd, Mesa, AZ 85212` and `16225 park ten Pl, Houston, TX
  77084` each appear twice, for two different businesses). Combined with several
  addresses being well-known civic buildings (e.g. Renton, WA's row resolves to
  Renton City Hall's address), this strongly suggests these are **representative/
  nominal addresses for local-SEO geographic relevance, not verified unique mailing
  addresses per business** — worth confirming your intent before treating them as
  ground truth in public-facing `LocalBusiness` schema (Google's guidelines
  require a real, staffed location for that markup).
- **12 rows (serials 39-50) have `"DONE "` with a trailing space** in the `status`
  column instead of `"DONE"`. Harmless if you always `.strip()`, but a naive
  spreadsheet filter or `status = "DONE"` equality check would silently drop these
  12 rows from a "completed" count.
- **10 rows (serials 51-60) have a completely blank `status`** — neither `DONE` nor
  `PENDING`. Likely a copy/paste gap when the sheet was extended; worth backfilling
  so status-based filtering doesn't silently miscount them.
- **Overall progress**: only 50/1000 rows (5%) are `status: DONE` (suburbs/
  neighborhoods researched); 940 are still `PENDING` and 10 are blank. This tracks
  with §1's observation that only 9 of 1000 domains have actual page content —
  the two gaps (content research and site content) are consistent with each other.
- **No drift found** between `domains.csv`, `config/sites.json`, and the sheet's
  `Purchased Domain` column — all 1000 domains match exactly, and the Site Build
  Sheet tab and the research tab agree with each other on every domain/address/
  business-name triple (0 mismatches across 1000 rows). The registry is not stale
  relative to its source.

---

## 9. Command reference

```bash
cd engine

# registry
python engine.py new <domain> --city X --st ST --area 000 [--street ...] [--zip ...] [--theme ...] [--tagline ...]
python engine.py bulk [--sheet ../domains.csv] [--tagline "..."]     # register every sheet domain

# content
python make_demo_content.py           # placeholder content for domains listed in ../_demo5.json

# assets
python engine.py logos                                                        # or: python logo_prep.py
python logo_gen.py ../domains.csv --out ../brand/logos [--only domain ...]    # for domains outside rows 1-200

# build / preview / audit
python build.py             # or: python engine.py build   (equivalent since 2026-08-17)
python engine.py serve      # or: python serve.py
python engine.py audit      # or: python audit_seo.py
```

### Before deploying: wire up lead capture

```bash
# one endpoint for every domain — edit config/sites.json:
#   "defaults": { "form_action": "https://formspree.io/f/xxxxxxx" }
# then rebuild; build.py names any site still without a phone or a form.
python build.py
```
Any endpoint that accepts a normal HTML POST works. Posted fields: `site`, `city`,
`name`, `phone`, `email`, `address`, `service`, `notes`, plus a `company` honeypot —
**reject submissions where `company` is non-empty**, they're bots.
