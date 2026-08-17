# Garage Door Site Engine — Guide & Folder Structure

A data-driven static-site generator that turns per-city JSON content into a full,
SEO-optimized garage-door-company website. One engine, one command, hundreds of
domains — each with its own theme, layout, logo and content.

This doc replaces the old scattered docs (`ENGINE_GUIDE.md`, `QUICK_START.md`,
`DELIVERABLES.md`, etc.) with one accurate reference, audited directly against the
current code (2026-08-11).

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
│   └── photos/                  30 city-branded .webp photos — currently UNUSED (only the legacy
│                                porta-potty renderer references .webp; the real garage build uses
│                                engine/assets_shared/photos/ instead)
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
    ├── templates.py               3 alternate full-site designs (ironclad / volt / nimbus),
    │                              selected per-site via sites.json "template" field
    ├── layouts.py                 layout-rotation helper for `engine.py bulk` — dead/orphaned,
    │                              see §7
    ├── scaffold.py                leftover from the porta-potty sibling project (hardcoded path to
    │                              a different repo's ledger file) — do not use, see §7
    ├── logo_gen.py                generates a unique geometric SVG→PNG logo per domain from its
    │                              name (deterministic hash) — a fallback generator, not what's
    │                              actually used today (see §8)
    ├── logo_prep.py                *** added in this pass *** — maps the 200 pre-made
    │                              brand/logos/<row#>_<slug>.png emblems to the per-domain
    │                              filenames build.py looks for (<domain>-emblem.png,
    │                              <domain>-favicon.png). This is what `engine.py logos` was
    │                              always supposed to call. See §8.
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
    │   │                          phone, theme, layout, port[, template])
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
    ├── brand/                     empty — stray leftover folder, ignore
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

**Run `python build.py`, not `python engine.py build`.** `engine.py`'s `build`
subcommand still calls `build_site.build()` (the old markdown/porta-potty path), which
silently does nothing useful for JSON content in `content/`. This is a leftover from
forking the engine for the garage-door niche that was never updated — see §7.

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

| # | Domain | City, ST | Address | Real logo? | Local URL |
|---|--------|----------|---------|:---:|-----------|
| 1 | dallasgaragedoor.com | Dallas, TX | *(not in the sheet — manually added, see §8.2)* | No | http://localhost:8201/ |
| 2 | mesagaragedoorco.com | Mesa, AZ | 7303 S Hawes Rd, 85212 | Yes | http://localhost:8203/ |
| 3 | napervillegaragedoorpros.com | Naperville, IL | 200-300 E 5th Ave, 60565 | Yes | http://localhost:8204/ |
| 4 | auroragaragedoorpros.com | Aurora, CO | 1550 S Potomac St, 80012 ⚠️ | Yes | http://localhost:8207/ |
| 5 | dallasdoorpros.com | Dallas, TX | 2555 N Stemmons Fwy, 75207 ⚠️ | Yes | http://localhost:8219/ |
| 6 | boonegaragedoorpros.com | Boone, NC | 216 S Main St, 28607 ⚠️ | Yes | http://localhost:8226/ |
| 7 | austingaragedoorguys.com | Austin, TX | 100 Congress Ave, 78701 ⚠️ | Yes | http://localhost:8258/ |
| 8 | puntagordagaragedoorpros.com | Punta Gorda, FL | 25551 Technology Blvd, 33950 | Yes | http://localhost:8283/ |
| 9 | richmonddoorpros.com | Richmond, TX | 500 Commerce Dr, 77469 ⚠️ | No (row 758, outside the 200-logo range) | http://localhost:8959/ |
| 10 | pickeringtongaragedoorpros.com | Pickerington, OH | 500 Center Point Rd, 43147 | No (row 975, outside the 200-logo range) | http://localhost:9176/ |

⚠️ = the source sheet flags this row `disambiguation_risk: HIGH-use-verify_url` — the city name
is shared with other US cities and the address should be spot-checked against the sheet's Google
Maps link before treating it as verified. See §8.3.

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
- **Trust pages**: `/about/`, `/contact/`, `/request-a-quote/` (copy is hard-coded in `build.py`, personalized with `{brand}`, `{city}`, `{phone}`)
- **`sitemap.xml`** and **`robots.txt`** (auto-generated from the actual page list)

SEO/AEO/GEO baked in automatically: `<title>` ≤ 60 chars, meta description,
canonical URL, OpenGraph + Twitter cards, single `<h1>`/page, `FAQPage` JSON-LD on
the homepage and every service page, `LocalBusiness` + `Service` + `BreadcrumbList`
JSON-LD `@graph`.

3 alternate full visual designs (**ironclad**, **volt**, **nimbus** — see
`templates.py`) can replace the default "garage" design per-site via a `"template"`
field in that site's `sites.json` entry.

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

1. **`engine.py build` is wrong for this niche.** It calls `build_site.build()` (the
   markdown-based porta-potty renderer), not `build.py`'s own `build()` (the
   JSON-based garage-door renderer actually used for all 10 live sites). Use
   `python build.py` directly, or fix `engine.py`'s `cmd_build` to
   `import build; build.build()` instead of `import build_site; build_site.build()`.

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

8. **`brand/photos/*.webp`** (30 city-branded photos) aren't referenced by
   `build.py` at all — only the unused `build_site.py` reads `.webp`. The actual
   photo pool every garage-door site uses is `engine/assets_shared/photos/gd-1.jpg`
   … `gd-9.jpg` (generic stock, not city-specific).

9. **`config/themes.json`'s `_comment` field** still says "Design themes for the
   Porta Pros engine" — cosmetic, but another sign large parts of this repo were
   forked from that sibling project without a full pass to re-label things.

None of the above blocks the documented bulk workflow in §5 — `build.py`, `serve.py`,
`audit_seo.py`, `engine.py new`, and `engine.py bulk` all work as described. The
issues are in the parts of `engine.py` (`build`, `logos`) and the logo/photo asset
pipeline that silently do the wrong thing rather than error loudly.

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

# build / preview / audit  — use these three directly, not `engine.py build`
python build.py
python engine.py serve      # or: python serve.py
python engine.py audit      # or: python audit_seo.py
```
