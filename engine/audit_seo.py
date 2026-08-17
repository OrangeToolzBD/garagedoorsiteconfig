#!/usr/bin/env python
"""Audit built sites for SEO / AEO / GEO signals."""
import json
import os
import re
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
try:
    _cfg = json.load(open(os.path.join(ROOT, "config", "sites.json"), encoding="utf-8"))
    DOMAINS = [s["domain"] for s in _cfg["sites"]]
except Exception:
    DOMAINS = [d for d in os.listdir(DIST) if "." in d and os.path.isdir(os.path.join(DIST, d))]


def text_of(html):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def audit_page(fp, domain):
    h = open(fp, encoding="utf-8").read()
    def find(pat):
        m = re.search(pat, h, re.I | re.S)
        return m.group(1).strip() if m else ""
    title = find(r"<title>(.*?)</title>")
    desc = find(r'<meta name="description" content="(.*?)"')
    canon = bool(re.search(r'<link rel="canonical"', h, re.I))
    og = len(re.findall(r'<meta property="og:', h, re.I))
    tw = bool(re.search(r'name="twitter:card"', h, re.I))
    h1 = re.findall(r"<h1[ >]", h, re.I)
    h2 = re.findall(r"<h2[ >]", h, re.I)
    imgs = re.findall(r"<img\b[^>]*>", h, re.I)
    imgs_alt = [i for i in imgs if re.search(r'alt="[^"]+"', i)]
    jsonld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
    types = []
    for block in jsonld:
        try:
            data = json.loads(block)
            objs = data if isinstance(data, list) else data.get("@graph", [data])
            for o in objs:
                if isinstance(o, dict) and o.get("@type"):
                    # "@type" is a list on nodes that declare several types (the
                    # business node is both LocalBusiness and
                    # HomeAndConstructionBusiness). Appending it raw made the
                    # set() in main() raise "unhashable type: 'list'".
                    ty = o["@type"]
                    types.extend(ty if isinstance(ty, list) else [ty])
        except Exception:
            types.append("PARSE_ERROR")
    internal = len(re.findall(r'href="/[^"]*"', h))
    faq = bool(re.search(r'class="faq"', h)) or ("FAQPage" in types)
    words = len(text_of(h).split())
    return {
        "title": title, "title_len": len(title),
        "desc": desc, "desc_len": len(desc),
        "canon": canon, "og": og, "tw": tw,
        "h1": len(h1), "h2": len(h2),
        "imgs": len(imgs), "imgs_alt": len(imgs_alt),
        "jsonld_types": types, "internal_links": internal,
        "faq": faq, "words": words,
    }


def main():
    print("=" * 78)
    for domain in DOMAINS:
        root = os.path.join(DIST, domain)
        pages = glob.glob(os.path.join(root, "**", "index.html"), recursive=True)
        rows = [audit_page(p, domain) for p in pages]
        n = len(rows)
        home = next((r for r in rows if True), {})
        # site-level files
        robots = os.path.exists(os.path.join(root, "robots.txt"))
        sitemap = os.path.exists(os.path.join(root, "sitemap.xml"))
        llms = os.path.exists(os.path.join(root, "llms.txt"))
        # aggregates
        title_bad = sum(1 for r in rows if r["title_len"] < 20 or r["title_len"] > 62)
        desc_bad = sum(1 for r in rows if r["desc_len"] < 70 or r["desc_len"] > 165)
        multi_h1 = sum(1 for r in rows if r["h1"] != 1)
        no_desc = sum(1 for r in rows if r["desc_len"] == 0)
        img_missing_alt = sum(r["imgs"] - r["imgs_alt"] for r in rows)
        faq_pages = sum(1 for r in rows if r["faq"])
        all_types = set(t for r in rows for t in r["jsonld_types"])
        avg_words = round(sum(r["words"] for r in rows) / max(n, 1))
        avg_links = round(sum(r["internal_links"] for r in rows) / max(n, 1))

        print(f"\n### {domain}  ({n} pages)")
        print(f"  robots.txt={robots}  sitemap.xml={sitemap}  llms.txt={llms}")
        print(f"  canonical: {sum(1 for r in rows if r['canon'])}/{n}   "
              f"og:tags on {sum(1 for r in rows if r['og'])}/{n}   twitter:card {sum(1 for r in rows if r['tw'])}/{n}")
        print(f"  title issues (<20 or >62 chars): {title_bad}/{n}")
        print(f"  meta-desc issues (<70 or >165): {desc_bad}/{n}   missing desc: {no_desc}")
        print(f"  pages with exactly one H1: {n-multi_h1}/{n}")
        print(f"  images missing alt: {img_missing_alt}")
        print(f"  FAQ (AEO) pages: {faq_pages}/{n}")
        print(f"  JSON-LD @types present: {sorted(all_types)}")
        print(f"  avg words/page: {avg_words}   avg internal links/page: {avg_links}")
    print("\n" + "=" * 78)


if __name__ == "__main__":
    main()
