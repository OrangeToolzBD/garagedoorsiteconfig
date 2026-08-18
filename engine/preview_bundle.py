#!/usr/bin/env python
"""Bundle several built sites under ONE origin, behind a single landing page.

Why this exists: each site normally gets its own port, and a landing page that links
to http://localhost:8219/ only works on this machine -- follow it through a tunnel and
it dies. ngrok's free plan also allows a single tunnel, so five ports is five tunnels
is a paid plan.

This copies each site into preview/<slug>/ and rewrites its root-relative URLs to sit
under that prefix, so the whole set is reachable from one port:

    preview/
      index.html          landing page linking the bundled sites
      dallas-door-pros/   a full copy of dist/dallasdoorpros.com with /x -> /dallas-door-pros/x
      ...

Only `href="/..."` and `src="/..."` are rewritten. Absolute `https://` URLs are left
alone, which means canonical/og:url still point at the real production domain -- correct
for a preview, and the reason this is a preview bundle and not a deployable artifact.

Usage:
  python preview_bundle.py [domain ...]      # default: the five review sites
  python serve_preview.py                    # serve it on one port
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
OUT = os.path.join(ROOT, "preview")

DEFAULT = ["dallasdoorpros.com", "austingaragedoorguys.com",
           "pickeringtongaragedoorpros.com", "richmonddoorpros.com",
           "auroragaragedoorpros.com"]

# href="/x" / src="/x" -> href="/<prefix>/x". The negative lookahead keeps it from
# double-prefixing on a re-run, and `https://` never starts with `/` so it is untouched.
def _rewrite(html, prefix):
    def sub(m):
        attr, url = m.group(1), m.group(2)
        if url.startswith(f"/{prefix}/") or url == f"/{prefix}":
            return m.group(0)
        return f'{attr}="/{prefix}{url}"'
    return re.sub(r'\b(href|src)="(/[^"]*)"', sub, html)


def bundle(domains):
    cfg = json.load(open(os.path.join(ROOT, "config", "sites.json"), encoding="utf-8"))
    sites = {s["domain"]: s for s in cfg["sites"]}
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    made = []
    for domain in domains:
        src = os.path.join(DIST, domain)
        if not os.path.isdir(src):
            print(f"  skip {domain}: not built (run build.py first)")
            continue
        slug = domain.rsplit(".", 1)[0]
        dst = os.path.join(OUT, slug)
        shutil.copytree(src, dst)
        n = 0
        for dp, _, files in os.walk(dst):
            for fn in files:
                if not fn.endswith(".html"):
                    continue
                p = os.path.join(dp, fn)
                html = open(p, encoding="utf-8").read()
                open(p, "w", encoding="utf-8").write(_rewrite(html, slug))
                n += 1
        s = sites.get(domain, {})
        made.append({"domain": domain, "slug": slug, "pages": n,
                     "brand": s.get("brand", domain), "city": s.get("city", ""),
                     "st": s.get("st", ""), "design": s.get("template", "garage"),
                     "p": s.get("p", "#12213a")})
        print(f"  {domain} -> preview/{slug}/  ({n} pages rewritten)")
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(landing(made))
    print(f"\nBundled {len(made)} sites -> {OUT}")
    return made


def landing(sites):
    cards = ""
    for s in sites:
        logo = os.path.exists(os.path.join(OUT, s["slug"], "assets", "logo-emblem.png"))
        mark = (f'<img class="c__logo" src="/{s["slug"]}/assets/logo-emblem.png" alt="">'
                if logo else '<span class="c__logo c__logo--none">no logo in set</span>')
        cards += f"""
    <a class="c" href="/{s['slug']}/">
      <span class="c__shot"><img src="/{s['slug']}/assets/photos/hero.webp" alt="" loading="lazy"></span>
      <span class="c__body">
        <span class="c__head">{mark}<span class="c__design">{s['design']}</span></span>
        <strong class="c__name">{s['brand']}</strong>
        <span class="c__meta">{s['city']}, {s['st']} &middot; {s['pages']} pages</span>
        <span class="c__go">Open site &rarr;</span>
      </span>
    </a>"""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage door sites - preview</title>
<meta name="robots" content="noindex,nofollow">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,system-ui,sans-serif;background:#0f1319;color:#e8ecf2;line-height:1.6;
  padding:56px 22px 70px}}
.wrap{{max-width:1120px;margin:0 auto}}
h1{{font-size:clamp(1.7rem,3.6vw,2.5rem);font-weight:800;letter-spacing:-.02em}}
.sub{{color:#98a3b3;margin:10px 0 34px;max-width:64ch}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}}
.c{{display:flex;flex-direction:column;background:#161b23;border:1px solid #252c37;border-radius:16px;
  overflow:hidden;text-decoration:none;color:inherit;transition:transform .18s,border-color .18s}}
.c:hover{{transform:translateY(-3px);border-color:#3d4757}}
.c__shot{{display:block;height:172px;overflow:hidden;background:#1d232c}}
.c__shot img{{width:100%;height:100%;object-fit:cover;display:block}}
.c__body{{display:block;padding:18px 20px 20px}}
.c__head{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;min-height:34px}}
.c__logo{{max-height:34px;max-width:150px;width:auto;object-fit:contain;background:#fff;
  border-radius:8px;padding:4px 7px}}
.c__logo--none{{font-size:.7rem;color:#7c8798;background:none;padding:0}}
.c__design{{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:#8ea2c0;
  border:1px solid #313a47;border-radius:999px;padding:4px 10px;white-space:nowrap}}
.c__name{{display:block;font-size:1.12rem;font-weight:600}}
.c__meta{{display:block;color:#98a3b3;font-size:.88rem;margin-top:3px}}
.c__go{{display:inline-block;margin-top:14px;font-weight:600;color:#7fb0ff}}
.note{{margin-top:36px;padding:16px 18px;border:1px solid #2c3644;border-radius:12px;
  background:#141922;color:#9aa6b6;font-size:.9rem;max-width:78ch}}
.note b{{color:#e8ecf2}}
@media(max-width:620px){{body{{padding:34px 16px 54px}}.grid{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<h1>Garage door sites - preview</h1>
<p class="sub">{len(sites)} sites, each on a different design, bundled under one origin
so they can be shared through a single link.</p>
<div class="grid">{cards}
</div>
<p class="note"><b>Preview build.</b> Phone numbers are placeholders and the quote form is
not connected to an inbox yet, so submitting it shows a notice instead of sending.
Each site's canonical tags still point at its real production domain.</p>
</div></body></html>"""


if __name__ == "__main__":
    bundle(sys.argv[1:] or DEFAULT)
