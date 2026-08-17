#!/usr/bin/env python
"""Measure how alike the built sites are below the hero.

    python measure_similarity.py            # report
    python measure_similarity.py --gate     # report + exit 1 if a target is missed

Diagnosing "every site looks the same below the hero" needs a number, not an
impression, and the fix needs a gate that fails loudly if it regresses. Only the
sites on the default "garage" design are scored: the three alt-template sites
(ironclad/volt/nimbus) are genuinely different pages and would flatter the
average.

Similarity is measured after normalising away the tokens that are *supposed* to
differ -- brand, city, state, phone, zip, domain -- so a high score means the
pages really are the same page, not just two cities with the same name length.
"""
import difflib
import glob
import html as _html
import json
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
CONFIG = os.path.join(ROOT, "config")

# Fail the gate if any of these regress. Baseline recorded before the
# differentiation work; see the plan for provenance.
TARGETS = {
    "text_median": ("<=", 0.65),
    "text_max": ("<", 0.85),
    "dom_median": ("<=", 0.75),
    "pairs_ge_95_text": ("==", 0),
    "single_value_strings": ("==", 0),
    "dead_axis_values": ("==", 0),
    "discarded_home_words": ("==", 0),
    "contrast_failures": ("==", 0),
    "pages_missing_main": ("==", 0),
    "pages_missing_skiplink": ("==", 0),
    "pages_calling_nobody": ("==", 0),
    "sites_missing_essentials": ("==", 0),
}


def missing_essentials():
    """Sites whose homepage lost a section a local-services page must have.

    Added after making section slots optional silently dropped the coverage
    section from 5 of 7 sites -- "where do you work" is the second thing a local
    customer checks, and no similarity metric notices its absence."""
    # The post-Services slot is now a five-variant library (proof_section), so
    # the visual beat can arrive as any of pf-detail / pf-tech / pf-cine /
    # pf-seq as well as the original .shots strip. pf-seq renders the steps
    # deck, so it satisfies "process" too -- and the site that shows it
    # deliberately suppresses how_it_works() rather than saying it twice.
    need = {"coverage": ('class="areagrid"', 'class="areas"'),
            "process":  ('class="steps', "pf-seq"),
            "visual":   ('class="shots"', "splitfeat", "pf-detail", "pf-tech",
                         "pf-cine", "pf-seq"),
            "faq":      ('class="faq"',),
            "cta":      ("cta-band",)}
    sites = {s["domain"]: s for s in
             json.load(open(os.path.join(CONFIG, "sites.json"), encoding="utf-8"))["sites"]}
    bad = {}
    for f in glob.glob(os.path.join(DIST, "*", "index.html")):
        d = os.path.basename(os.path.dirname(f))
        if sites.get(d, {}).get("template", "garage") != "garage":
            continue
        h = open(f, encoding="utf-8").read()
        gone = [k for k, needles in need.items() if not any(n in h for n in needles)]
        if gone:
            bad[d] = gone
    return bad


def contrast_failures():
    """Themes whose accent-derived colours fail WCAG AA where they carry text.

    Three separate surfaces, each previously broken independently:
      * the button label on the accent fill        (was 410 / 1001)
      * accent text on the light bands             (was 410 / 437 / 455)
      * accent text on the dark hero grounds       (was 982, fixed earlier)
    Kept as a gate because every one of these was introduced by a theme
    generator that believed it was already contrast-checking."""
    import build_site as B
    themes = json.load(open(os.path.join(CONFIG, "themes.json"), encoding="utf-8"))
    sites = json.load(open(os.path.join(CONFIG, "sites.json"), encoding="utf-8"))["sites"]
    surfaces = {"#ffffff": (255, 255, 255), "--soft": (245, 247, 249), "--soft2": (238, 242, 246)}
    fails = {}
    for s in sites:
        t = themes[s["theme"]]
        fill, label = B.accent_button(t["accent"])
        if B._cratio(B._rgb(label), B._rgb(fill)) < 4.5:
            fails.setdefault("button label on fill", []).append(s["theme"])
        lt = B.accent_on_light(t["accent"])
        for nm, bg in surfaces.items():
            if B._cratio(B._rgb(lt), bg) < 4.5:
                fails.setdefault(f"accent text on {nm}", []).append(s["theme"])
        dk = B.accent_on_dark(t["accent"], t["pd"])
        if min(B._cratio(B._rgb(dk), B._rgb(t["pd"])),
               B._cratio(B._rgb(dk), B.BANNER_OVERLAY)) < 4.5:
            fails.setdefault("accent text on hero", []).append(s["theme"])
    return sum(len(v) for v in fails.values()), fails, len(sites)


def page_checks():
    """Landmark / skip-link coverage, and pages that say "Call" with no number."""
    pages = glob.glob(os.path.join(DIST, "*", "**", "index.html"), recursive=True)
    no_main = no_skip = calling_nobody = 0
    for f in pages:
        h = open(f, encoding="utf-8").read()
        if '<main id="main">' not in h or "</main>" not in h:
            no_main += 1
        if 'class="skiplink"' not in h:
            no_skip += 1
        # Signatures of an empty phone interpolation. Matched narrowly: a deck
        # variant legitimately ends an eyebrow with "Before You Call</p>", so a
        # loose `Call\s*</` pattern produces false positives. The similarity gate
        # cannot see any of this -- normalise() strips the phone before comparing
        # -- so it needs its own check.
        if re.search(r"Call\s{2,}|Call\s+to reach|Call\s+or use|Call\s*</a>"
                     r"|Reach us at\s{2,}", h):
            calling_nobody += 1
    return len(pages), no_main, no_skip, calling_nobody


def load_sites():
    cfg = json.load(open(os.path.join(CONFIG, "sites.json"), encoding="utf-8"))
    return {s["domain"]: s for s in cfg["sites"]}


def default_design_domains():
    """Built domains using the default 'garage' design."""
    sites = load_sites()
    out = []
    for d in sorted(os.listdir(DIST)) if os.path.isdir(DIST) else []:
        s = sites.get(d)
        if s and s.get("template", "garage") == "garage":
            out.append(d)
    return out


def below_hero(htmlstr):
    """Everything after the hero section closes.

    Walks <section>/</section> with a depth counter -- the hero contains nested
    sections in some layout variants, so a regex for the next </section> finds
    the wrong tag."""
    m = re.search(r'<section class="hero', htmlstr)
    if not m:
        return htmlstr
    i, depth = m.start(), 0
    for tag in re.finditer(r"</?section\b", htmlstr[m.start():]):
        depth += 1 if tag.group(0) == "<section" else -1
        if depth == 0:
            i = m.start() + tag.end()
            break
    return htmlstr[i:]


def normalise(text, site):
    """Blank out the tokens that are meant to differ between sites."""
    reps = [site.get("brand", ""), site.get("city", ""), site.get("domain", ""),
            site.get("phone", ""), site.get("zip", ""), site.get("street", ""),
            site.get("st", ""), site.get("area", "")]
    for r in sorted((x for x in reps if x), key=len, reverse=True):
        text = text.replace(r, "@")
    # brand/city also appear slugified and digit-stripped
    for r in sorted((x for x in reps if x), key=len, reverse=True):
        text = text.replace(r.lower().replace(" ", "-"), "@")
    return re.sub(r"\d", "#", text)


def visible_text(htmlstr):
    t = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", htmlstr)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


def dom_tokens(htmlstr):
    """tag.class sequence with all text removed."""
    t = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", htmlstr)
    out = []
    for m in re.finditer(r"<(\w+)([^>]*)>", t):
        cls = re.search(r'class="([^"]*)"', m.group(2))
        out.append(m.group(1) + ("." + "/".join(sorted(cls.group(1).split())) if cls else ""))
    return out


def ratio(a, b):
    # autojunk=False matters: by default SequenceMatcher treats any element
    # appearing in >1% of a sequence longer than 200 items as junk and ignores
    # it. DOM token lists are long and highly repetitive, so the heuristic fires
    # and the score moves non-monotonically as page length changes -- it once
    # reported similarity *rising* after a change that only added variety.
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def pairwise(domains, get):
    vals, pairs = [], []
    for i in range(len(domains)):
        for j in range(i + 1, len(domains)):
            r = ratio(get(domains[i]), get(domains[j]))
            vals.append(r)
            pairs.append((r, domains[i], domains[j]))
    return vals, sorted(pairs, reverse=True)


def count_single_value_strings(domains, texts):
    """Copy fragments that have exactly one distinct value across every site.

    Sentence-level: any normalised sentence present on every site is, by
    definition, copy no site can differentiate itself with."""
    persite = []
    for d in domains:
        sents = {s.strip() for s in re.split(r"(?<=[.?!])\s+", texts[d]) if len(s.strip()) > 25}
        persite.append(sents)
    if not persite:
        return 0, []
    shared = set.intersection(*persite)
    return len(shared), sorted(shared)[:12]


def dead_axis_values():
    """Layout-axis values that emit a class with no CSS rule behind it."""
    css_files = glob.glob(os.path.join(DIST, "*", "assets", "site.css"))
    if not css_files:
        return [], {}
    css = "".join(open(f, encoding="utf-8").read() for f in css_files)
    checks = {
        "cards:classic": ".scards--classic", "cards:overlay": ".scards--overlay",
        "cards:side": ".scards--side",
        "feats:tiles": ".feats--tiles", "feats:list": ".feats--list",
        "feats:bar": ".feats--bar", "feats:minimal": ".feats--minimal",
        "steps:cards": ".steps--cards", "steps:timeline": ".steps--timeline",
        "steps:bignum": ".steps--bignum",
        "bands:alt": ".lay-bands-alt", "bands:flat": ".lay-bands-flat",
    }
    counts = {k: css.count(sel + "{") + css.count(sel + " ") + css.count(sel + ",")
              for k, sel in checks.items()}
    return [k for k, v in counts.items() if v == 0], counts


def discarded_home_words():
    """Words in homepage JSON `sections` that never reach any built page."""
    total = 0
    per = {}
    for folder in sorted(glob.glob(os.path.join(ROOT, "content", "*"))):
        for f in glob.glob(os.path.join(folder, "*-home.json")):
            try:
                data = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            words = sum(len(str(s.get("body", "")).split()) for s in data.get("sections", []))
            if not words:
                continue
            # Does the built output actually carry this section's material?
            # An earlier version probed for the first 8 words verbatim, which
            # broke the moment sections started being rendered as components
            # (a neighbourhood list becomes a grid, so its lead-in prose is
            # legitimately replaced). Check distinctive vocabulary coverage
            # instead: the data survives even when the sentences don't.
            vocab = set(re.findall(r"[A-Za-z']{5,}",
                                   " ".join(str(s.get("body", "")) for s in data["sections"])))
            if not vocab:
                continue
            seen = set()
            for p in glob.glob(os.path.join(DIST, "*", "**", "index.html"), recursive=True):
                txt = visible_text(open(p, encoding="utf-8").read())
                hits = {w for w in vocab if w in txt}
                if len(hits) > len(seen):
                    seen = hits
                if len(seen) / len(vocab) > .8:
                    break
            if len(seen) / len(vocab) <= .8:
                total += words
                per[os.path.basename(folder)] = words
    return total, per


def main():
    gate = "--gate" in sys.argv
    sites = load_sites()
    domains = default_design_domains()
    if len(domains) < 2:
        print("! need at least 2 built default-design sites; run build.py first")
        return 1

    texts, doms = {}, {}
    for d in domains:
        h = open(os.path.join(DIST, d, "index.html"), encoding="utf-8").read()
        region = below_hero(h)
        texts[d] = normalise(visible_text(region), sites[d])
        doms[d] = dom_tokens(region)

    tvals, tpairs = pairwise(domains, lambda d: texts[d].split())
    dvals, dpairs = pairwise(domains, lambda d: doms[d])
    n_single, examples = count_single_value_strings(domains, texts)
    dead, axis_counts = dead_axis_values()
    disc_words, disc_per = discarded_home_words()

    # text_max is gated only across pairs with DIFFERENT content folders. Two
    # domains pointing at one pack render the same authored prose by definition;
    # no renderer change can separate them, so gating on it would leave a
    # permanently-red check that everyone learns to bypass. The pair is still
    # reported and annotated above.
    cross_vals = [r for r, a, b in tpairs
                  if sites[a].get("content") != sites[b].get("content")] or tvals
    res = {
        "text_median": statistics.median(tvals),
        "text_max": max(cross_vals),
        "dom_median": statistics.median(dvals),
        "pairs_ge_95_text": sum(1 for v in tvals if v >= .95),
        "single_value_strings": n_single,
        "dead_axis_values": len(dead),
        "discarded_home_words": disc_words,
    }
    cfails, cdetail, ntheme = contrast_failures()
    ess = missing_essentials()
    npages, no_main, no_skip, calling_nobody = page_checks()
    res.update({"contrast_failures": cfails, "pages_missing_main": no_main,
                "pages_missing_skiplink": no_skip, "pages_calling_nobody": calling_nobody,
                "sites_missing_essentials": len(ess)})

    print("=" * 68)
    print(f"BELOW-HERO SIMILARITY  ({len(domains)} default-design sites, "
          f"{len(tvals)} pairs)")
    print("=" * 68)
    for d in domains:
        print(f"    {d}")
    print()
    print(f"  text  similarity  min {min(tvals):.1%}  median {res['text_median']:.1%}  max {res['text_max']:.1%}")
    print(f"  DOM   similarity  min {min(dvals):.1%}  median {res['dom_median']:.1%}  max {max(dvals):.1%}")
    print(f"  pairs >=95% text  {res['pairs_ge_95_text']} / {len(tvals)}")
    print()
    print("  most-alike pairs (text):")
    for r, a, b in tpairs[:5]:
        same = sites[a].get("content") == sites[b].get("content")
        note = f"   [same content pack: {sites[a]['content']}]" if same else ""
        print(f"    {r:6.1%}  {a}  <->  {b}{note}")
    print()
    # Pairs sharing a content folder render the same authored prose by
    # definition -- no renderer change can separate them. Report the two
    # populations so a content-pack problem isn't mistaken for a template one.
    cross = [r for r, a, b in tpairs if sites[a].get("content") != sites[b].get("content")]
    if cross and len(cross) < len(tvals):
        print(f"  excluding {len(tvals) - len(cross)} pair(s) that share a content pack:")
        print(f"    text median {statistics.median(cross):.1%}   max {max(cross):.1%}")
        print()
    print(f"  sentences identical on EVERY site: {n_single}")
    for s in examples[:6]:
        print(f"    - {s[:88]}")
    print()
    print(f"  layout-axis values with no CSS: {len(dead)}  {dead}")
    print(f"  homepage words discarded by the renderer: {disc_words}  {disc_per}")
    print()
    print(f"  contrast (WCAG AA) over {ntheme} in-use themes: {cfails} failures")
    for k, v in sorted(cdetail.items()):
        print(f"    {k}: {len(v)}")
    print(f"  landmarks: {npages - no_main}/{npages} have <main>, "
          f"{npages - no_skip}/{npages} have a skip link")
    print(f"  pages saying 'Call' with no number: {calling_nobody}")
    print(f"  sites missing an essential section: {len(ess)} {ess or ''}")
    print()

    ok = True
    print("  gate:")
    for k, (op, target) in TARGETS.items():
        v = res[k]
        passed = (v <= target if op == "<=" else v < target if op == "<" else v == target)
        ok &= passed
        shown = f"{v:.1%}" if isinstance(v, float) else str(v)
        tgt = f"{target:.0%}" if isinstance(target, float) else str(target)
        print(f"    {'PASS' if passed else 'FAIL'}  {k:24} {shown:>8}  (target {op} {tgt})")
    print("=" * 68)
    if gate and not ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
