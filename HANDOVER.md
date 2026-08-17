# Handover

Written for whoever picks this up next. Read this before touching `engine/build.py`.

---

## 1. What this repo is

A static-site generator that produces garage-door company websites. **1001 sites
are configured**; 9 content packs exist, so **10 domains currently build** (202
pages). The rest are waiting on content.

```
engine/build.py            the active renderer — ~3,300 lines, everything lives here
engine/build_site.py       the shared design system: css(), CSS_TMPL, NAVJS, icon()
engine/templates.py        3 full alternate designs (ironclad / volt / nimbus)
engine/measure_similarity.py   the quality gate — run this before you ship
engine/config/sites.json   1001 site rows: domain, city, theme, layout, pins
engine/config/themes.json  colour + font palettes
engine/config/layouts.json 6 layout families (hero/nav/shape/bands/cards/…)
engine/content/<city>/     the authored prose per content pack
brand/photos/              150 category photos + 50 guide + 30 city heroes
```

Build everything:

```bash
cd engine && python3 build.py
```

Output lands in `engine/dist/<domain>/` (gitignored).

---

## 2. What we are trying to achieve

**One renderer, a thousand sites that do not look like one renderer.**

The original failure mode: every page was structurally identical. Below the hero,
text similarity ran at **78.7% median**, DOM at **90.2%**, with 7 site pairs above
95%. Google treats that as a doorway-page network, and a human reads it as spam.

The strategy is **deterministic variant libraries**, not randomness:

- The same domain always resolves to the same design on every rebuild.
- Different domains resolve differently.
- Selection is driven by **real signals first** (service count, whether photos
  exist, what the hero already did), and a `blake2s` digest of the domain only
  breaks the remaining tie.

Where it stands now:

| Metric | Was | Now |
|---|---|---|
| Text similarity, median | 78.7% | **49.1%** |
| DOM similarity, median | 90.2% | **57.4%** |
| Pairs above 95% text | 7 | **0** |
| WCAG AA contrast failures | 982 | **0** |

---

## 3. The rules. Do not break these.

These came from the client directly and have been enforced throughout.

**Never invent business facts.** No reviews, ratings, certifications,
guarantees, warranties, pricing, years in business, project counts, case
studies, durations, or customer problems. If a design needs data we do not
have, the block gets **dropped**, not filled. Precedents in the code:

- `reviews_band()` — refuses to generate reviews
- `_svcx_tabs()` — dropped the reference design's 2×2 checklist
- `proof_section` — dropped two of six supplied designs (a case study needing a
  project narrative, and a before/after needing paired photography)
- `_FIGURES` — an explicit table, so a figure never gets an invented label

**Never hardcode** a city, a domain, or "garage door". No per-domain special
cases in the renderer.

**Never hardcode a colour.** Everything is a token — `--ink --p --pd --accent
--accent-lt --accent-dk --on-accent --muted --line --soft --soft2 --card
--radius --btn-r --disp`. A hex value makes 1001 sites identical *and* fails the
contrast gate.

**Do not touch the Hero, the footer, or global architecture** without being
asked. (See §7 — there is an open hero question.)

**No second animation framework, no CDN, no npm.** Output is fully static and
offline. Interaction is CSS-first; the only JS is `NAVJS` (an IntersectionObserver
reveal + nav toggles).

**Respect `prefers-reduced-motion`.** Note the trap: `.svcx *` matches *elements
only* — a pseudo-element's transition is not inherited and needs its own rule.

**Deterministic.** Same site → same output. Never `random`. Note that
`Date.now()`-style nondeterminism would also break the byte-identical rebuild
gate.

---

## 4. What has been built

### Services section — 12 archetypes, 11 reachable

`SERVICE_ARCHETYPES` in `build.py`. Chosen by `services_archetype()`.

`featured · editorial · spotlight · floating · bento · overlay · accordion ·
problem · timeline · typo · orbit · tabs`

**`problem` never fires.** It requires ≥3 services whose copy carries genuine
symptom language; the content yields 1. That is the no-inventing rule holding,
not a bug. Leave it unless you add symptom data.

Selection narrows by real signals before the digest:

| Signal | Effect |
|---|---|
| ≥3 services | `featured editorial spotlight accordion tabs` |
| ≥3 services **and** longest title ≤22 visible chars | adds `typo` (long names wreck giant type) |
| ≥4 services | adds `floating bento overlay timeline orbit` |
| ≥3 symptom-bearing blurbs | adds `problem` (never met) |
| **Hero contrast** | a photo-led hero is followed by a *quiet* archetype and vice versa, so the two read as different moments |

`quiet = {editorial, accordion, bento, problem, typo, timeline, tabs}`.
Everything else is image-led.

**Every service carries its own photograph.** `select_photos()` already drew one
per service from that service's own pool, salted by domain. The renderer used to
show `items[0]` and discard the rest — fixed. The active service now drives the
image.

### The selection engine (reuse this; do not fork it)

Search `build.py` for **"THE ACTIVE SERVICE DRIVES THE IMAGE"**. Three tiers
share one class family `.svcx-sel--N`:

1. **Committed** — a radio stays `:checked`. This is what makes it work on touch,
   where there is no hover to preview with.
2. **Pointer** — `:hover` / `:active`, overrides the radio while it lasts.
3. **Keyboard** — `:focus-visible`, written last so it beats a mouse left
   resting somewhere else. Without this tier, two layers light at once and the
   copy panel overlaps itself.

Tiers 2 and 3 are padded with `:nth-child(n)` purely to match tier 1's
specificity so source order decides the tie. **Ceiling is 6 layers**, and the
`:has()` selectors need an ancestor with class `.svcx`.

Shared primitives — reuse, don't duplicate: `_svcx_head _svcx_more _svcx_stack
_svcx_visual _svcx_copystack _svcx_rail _svcx_radio _svcx_pick _svcx_dot
_svcx_nav _svcx_group`.

### Visual-proof section — 5 variants

The slot immediately after Services. `PROOF_VARIANTS`, chosen by `proof_section()`.

`photoband · detail · technician · cinematic · sequence`

Each variant **declares what copy deck it consumes**, and the downstream slot
stands down rather than repeating the claim further down the page:

- `technician` / `cinematic` eat the later `split` slot
- `sequence` adds `"process"` to `covered`, so `how_it_works()` stands down
- `photoband` / `detail` use the slot's own deck — no suppression

`select_photos()` returns each gallery pick's source category (Repair /
Installation / Service / Maintenance). That is **the only truthful per-photo
label that exists** — there are no captions, titles or dates anywhere.

### Correctness fixes shipped

- `on_accent` was hardcoded white → **410 of 1001 themes failed AA** on the
  primary button label. Now picked per theme, with the accent nudged where no
  label clears 4.5:1. Added `--accent-lt` for accent text on light bands.
- `trust_page` interpolated a phone unconditionally → *"Call&nbsp; to reach…"* on
  21 pages. **998 of 1001 sites have no phone number.**
- No `<main>` and no skip link on any of 202 pages.
- Footer links and burger below the 44px touch target.
- Alt templates toggled their menu with no `aria-expanded`.
- `.shots` hid its third photo below 760px — a 3-photo section became 2 on every
  phone.
- An f-string backslash blocked **every build** on Python 3.10.

---

## 5. The gate — run this before you ship

```bash
cd engine && python3 measure_similarity.py --gate
```

12 checks, exits non-zero on regression: text/DOM similarity, pairs ≥95%,
single-value strings, dead layout axes, discarded prose, WCAG AA over all 1001
in-use themes, `<main>`, skip links, phone-less "Call" prose, and **missing
essential sections**.

Two things worth understanding:

- `text_max` deliberately **excludes pairs sharing a content pack**. No renderer
  change can separate two domains pointing at the same authored prose, and a
  permanently-red check just gets bypassed.
- `sites_missing_essentials` looks for sections by CSS class. **If you add a new
  section variant, add its class to the `need` dict** or the gate will correctly
  report the section as missing. Do not loosen the check.

Also run `python3 audit_seo.py`. And there is a Services-specific gate used
during development (9 checks incl. a **containment test** that proves the hero
and every other section stay byte-identical when Services is stubbed out) — it
lived in the session scratchpad and is **not committed**. Worth re-creating in
`engine/` if you continue this work.

### Verification approach that actually caught things

Automated checks passed on several designs that looked wrong. **Screenshot it
and look before declaring success.** Real measurement over CDP found:

- a name's anchor box was 725px while its glyphs painted 454px — 270–370px of
  every row was empty *but still clickable*
- a caption measured **1.74:1** contrast against a photo it sat on
- type rendered **larger at 768px than at 1280px** (two competing `clamp()`s)
- a `position:static` mobile override destroyed a containing block, letting
  absolutely-positioned layers escape and add 17px of horizontal scroll

Sweep **360 → 1920** (16 widths), measure contrast on *rendered pixels* (hide
the glyphs to sample the true ground), and check reduced motion on elements
**and** pseudo-elements.

---

## 6. Live review servers

| Port | Domain | Services archetype | Notes |
|---|---|---|---|
| 8201 | dallasgaragedoor.com | `timeline` | **pinned** |
| 8203 | mesagaragedoorco.com | `orbit` | **pinned** |
| 8204 | napervillegaragedoorpros.com | `floating` | auto |
| 8207 | auroragaragedoorpros.com | `tabs` | **pinned** |
| 8219 | dallasdoorpros.com | `typo` | **pinned** |
| 8258 | austingaragedoorguys.com | `featured` | auto |
| 8283 | puntagordagaragedoorpros.com | `editorial` | proof **pinned** to `cinematic` |

**⚠ Remove the review pins before production.** Five rows in `sites.json` carry
`"services"` / `"proof"` keys that override automatic selection. They exist so a
human can click each variant. Left in, those sites never participate in the
rotation.

---

## 7. Open items

### Raised by the client, unresolved

**The hero on `austingaragedoorguys.com` (`:8258`) was rejected.** Traced, not
changed — the standing instruction is not to touch the Hero. Three independent
causes:

1. `themes.json` → `austingaragedoorguys` pairs purple `p:#581c87` with green
   `accent:#51911e`. Near-equal saturation, and the accent drives both the
   button *and* the decorative circle, so green appears twice.
2. `build_site.py:597` — `.hero::after` puts a 420px accent circle on **every**
   hero on all 1001 sites. Invisible on most palettes at 14% opacity; a green
   blob on this one.
3. `layouts.json` → `harbor` sets `"hero": "stacked"`, the least art-directed of
   the six variants (`build.py:2053`, styled in four lines at
   `build_site.py:614-617`).

Fix levels, smallest first: change this site's `theme`/`layout` (1 line, 1
site) → retune the palette (all sites on that theme) → rework the `stacked`
variant or `hero::after` (**all 1001 sites, needs a full contrast re-run**).
Ask which, and whether the objection is the colour pairing or the layout.

### Product gaps that limit everything else

- **998 of 1001 sites have no phone number. None has a form. There is no
  analytics.** Most sites give a visitor no way to make contact, and nobody
  could tell if they did. Needs real data and a form backend from the client.
- **8 of 9 content packs are 99.4–100% identical after the city swap.** This is
  a content problem the renderer cannot fix; it is why `text_max` excludes
  same-pack pairs.

### Engineering debt

- No tests against ~6,000 lines.
- `dist/` projects to **~3.70 GB at 1000 sites**, 99.5% duplicated images. A
  hardlink pass takes it to ~50 MB.
- 202 pages share one `lastmod`; zero contextual in-body links.
- Schema gaps: `image`, `geo`, `openingHours`, `sameAs`, hardcoded `priceRange`,
  and city-level `areaServed` on 76 neighbourhood pages despite per-page data
  being loaded and discarded.
- 72% of images ship without dimensions; 132 alts duplicate their own H1.
- No 404 page, no `llms.txt`.
- **`engine/README.md` is false** in every substantive claim. `ENGINE_GUIDE.md`
  is the accurate one.
- Dead code: `.photoband__in` CSS, `scaffold.py`'s unused `make_accent()`.

---

## 8. Working notes that will save you time

- **`band()` rewrites section tint by position.** A new section must open with
  the literal `<section class="sec` prefix or it is skipped by the parity
  counter, and whatever `sec--soft` you write will be overwritten. Return `""`
  to drop out of the rhythm cleanly.
- **Deck titles are pre-escaped.** Calling `esc()` again yields `&amp;amp;`.
  This has bitten twice.
- **`sec-head--left` is scoped to `.svcx-sec`.** It does nothing outside the
  Services section.
- **Guard every scripted edit.** A patch script that prints "MISS" but still
  writes will splice code into the wrong place — that happened, and put a mobile
  media block inside the wrong query so mobile rules applied at 1280px.
- **`difflib` needs `autojunk=False`** for long sequences, or similarity numbers
  are quietly wrong.
- `_hash_idx()` is blake2s (chosen over md5 for FIPS safety). `_stable_idx()` is
  a legacy sum-of-ord, retained for existing photo picks — do not "fix" it or
  every site's photos change.
- Chrome clamps `--window-size`; use `Emulation.setDeviceMetricsOverride` for
  real viewport testing.
- `html{scroll-behavior:smooth}` is set globally — a rect read in the same tick
  as `scrollIntoView` is stale, and synthetic clicks land on the wrong element.

---

## 9. How the client works

Designs arrive as zips (Tailwind CDN showcase pages + a `DESIGN.md`). The
established process:

1. **Assess before building.** Report what ports 1:1, what must be rewired, and
   what cannot be built because the data does not exist.
2. Expect the markup to be **non-functional** — states are usually simulated as
   sibling divs, and there is often no JavaScript at all.
3. Check whether the design **already exists**. Two of the last three supplied
   were archetypes we already shipped.
4. Everything external gets replaced: Tailwind → plain CSS in `GD_CSS`; Google
   Fonts → `var(--disp)`; Material Symbols → `icon()`; remote images →
   `select_photos`; fixed palette → tokens.
5. Cap display type **below the page H1 (53px)**. A supplied `display-lg` of
   72px inverts the hierarchy and has been rejected once already.

The client reviews visually and will reject work that passes every automated
check. Budget for iteration, and look at the render yourself first.
