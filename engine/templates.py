#!/usr/bin/env python
"""Alternate full-site design templates for the garage-door engine.

Each template renders every page type (home / service / area / guide index + detail /
about / contact / quote) in a distinct visual language, driven by the same config +
content + schema as the default "garage" design. build.py injects the shared helpers
module as `H` and dispatches per site via the site's "template" field.

  H  — the build module (esc, icon, render_body, faq_accordion, humanize_heading,
       slugify, seo_title, area_label, org/service/breadcrumb/faq schema, SERVICE_TILES,
       CARD_IMGS, INNER_IMGS, HERO_IMG, _stable_idx)
"""
import json

H = None  # injected by build.get_renderer()

PHOTOS = "/assets/photos/"

# ---------------------------------------------------------------- shared bits
def _head(t, title, desc, url, schemas, fonts, bodyclass="", og=None):
    e = H.esc
    graph = {"@context": "https://schema.org", "@graph": schemas}
    ogm = ""
    if og:
        u = f"https://{t['domain']}{PHOTOS}{og}"
        ogm = f'<meta property="og:image" content="{u}"><meta name="twitter:image" content="{u}">'
    fav = "/assets/favicon.png" if t.get("has_logo") else "/assets/favicon.svg"
    ft = "image/png" if t.get("has_logo") else "image/svg+xml"
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(title)}</title><meta name="description" content="{e(desc)}">'
            f'<link rel="canonical" href="https://{t["domain"]}{url}">'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="{e(t["brand"])}">'
            f'<meta property="og:url" content="https://{t["domain"]}{url}"><meta property="og:title" content="{e(title)}">'
            f'<meta property="og:description" content="{e(desc)}">{ogm}'
            f'<meta name="twitter:card" content="summary_large_image">'
            f'<link rel="icon" type="{ft}" href="{fav}">'
            f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link href="https://fonts.googleapis.com/css2?{fonts}&display=swap" rel="stylesheet">'
            f'<link rel="stylesheet" href="/assets/site.css">'
            f'<script type="application/ld+json">{json.dumps(graph)}</script>'
            f'</head><body class="{bodyclass}">')

def _cat(pages, c): return [p for u, p in pages.items() if p["cat"] == c]

def _menu(pages, cat, all_url, all_label):
    """[(url,label)] for a nav dropdown: an 'All ...' link then each page in the category."""
    return [(all_url, all_label)] + [(p["url"], H.area_label(p)) for p in _cat(pages, cat)]

def _home_data(t, pages):
    home = pages.get("/")
    h1 = (home["h1"] if home else "") or f"Garage Door Repair & Installation in {t['city']}, {t['st']}"
    lead = (home["meta"] if home else "") or (
        f"Local garage door repair, spring and opener service and new-door installation across "
        f"{t['city']} and the surrounding metro.")
    faqs = (home["faq"] if (home and home["faq"]) else [
        (f"Do you offer same-day garage door repair in {t['city']}?",
         f"Yes - most repair calls in {t['city']} are handled the same or next day."),
        ("How much does a repair cost?",
         "It depends on the part. You get a written price on site before any work starts."),
        ("Should I repair or replace an older door?",
         "If the panels or track are failing on an original door, replacement can beat repeated repairs. We'll tell you honestly which fits."),
        ("Is replacing a spring a DIY job?",
         "No - torsion springs are under high tension and can injure. Leave that one to a tech.")])
    return h1, lead, faqs, _cat(pages, "service"), _cat(pages, "area"), _cat(pages, "guide")

def _svc_tiles(pages):
    """SERVICE_TILES with links resolved to real service pages where they exist."""
    out = []
    for ic, title, blurb, slug in H.SERVICE_TILES:
        url = f"/services/{slug}/" if slug and f"/services/{slug}/" in pages else "/request-a-quote/"
        out.append((ic, title, blurb, url))
    return out

def _inner_parts(t, p):
    """Render a content page's sections + optional FAQ to HTML (design-neutral inner text)."""
    parts = []
    for sec in p["sections"]:
        h2 = sec.get("h2", "")
        parts.append(f'<h2>{H.esc(H.humanize_heading(h2))}</h2>{H.render_body(sec.get("body", ""))}')
    if p["faq"]:
        parts.append(f'<h3>Frequently asked questions</h3>{"".join(f"<details><summary>{H.esc(q)}</summary><p>{H.esc(a)}</p></details>" for q,a in p["faq"])}')
    return "".join(parts)

def _inner_schemas(t, p, h1, label, parent):
    import re
    trail = [("Home", "/"), (label, parent), (h1, p["url"])]
    s = [H.org_schema(t), H.breadcrumb_schema(t, trail)]
    if p["cat"] == "service":
        s.append(H.service_schema(t, re.sub(r"\s+in\s+.*$", "", h1).strip() or h1, p["url"]))
    if p["faq"]:
        s.append(H.faq_schema(p["faq"]))
    return s

_LABELS = {"service": ("Services", "/services/"), "area": ("Service Areas", "/service-areas/"), "guide": ("Guides", "/guides/")}


# ================================================================ IRONCLAD
# editorial / luxury / serif — cream + brass + ink, hairline dividers
IRON_FONTS = "family=Playfair+Display:ital,wght@0,500;0,700;0,900;1,500&family=Inter:wght@400;500;600"
IRON_CSS = r"""
:root{--ink:#171512;--cream:#f6f2ea;--paper:#fbf9f4;--brass:#a9803f;--rule:#d8cfbe;--muted:#6b6459}
*{margin:0;padding:0;box-sizing:border-box}html{scroll-behavior:smooth}
body{font-family:Inter,sans-serif;color:var(--ink);background:var(--paper);line-height:1.6;-webkit-font-smoothing:antialiased}
.serif{font-family:"Playfair Display",Georgia,serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 32px}
a{color:inherit;text-decoration:none}img{display:block;max-width:100%}
.kick{font-size:.72rem;letter-spacing:.32em;text-transform:uppercase;color:var(--brass);font-weight:600}
.ulink{position:relative;font-weight:500;padding-bottom:2px}
.ulink::after{content:"";position:absolute;left:0;bottom:0;width:100%;height:1px;background:currentColor;transform:scaleX(0);transform-origin:right;transition:transform .35s}
.ulink:hover::after{transform:scaleX(1);transform-origin:left}
.pill{display:inline-block;border:1px solid var(--ink);padding:14px 30px;font-size:.74rem;letter-spacing:.22em;text-transform:uppercase;font-weight:600;transition:.3s}
.pill:hover{background:var(--ink);color:var(--cream)}
.pill--brass{border-color:var(--brass);color:var(--brass)}.pill--brass:hover{background:var(--brass);color:#fff}
.util{background:var(--ink);color:var(--cream)}
.util .wrap{display:flex;justify-content:space-between;font-size:.72rem;letter-spacing:.12em;padding:9px 32px;text-transform:uppercase}
.util a{color:var(--brass)}
header{position:sticky;top:0;z-index:40;background:rgba(251,249,244,.9);backdrop-filter:blur(8px);border-bottom:1px solid var(--rule)}
.nav{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:20px 32px}
.nav__side{display:flex;gap:30px;font-size:.82rem}.nav__side--r{justify-content:flex-end}
.ni{position:relative}
.nav__side .ni .dc{display:inline-block;width:5px;height:5px;border-right:1px solid var(--brass);border-bottom:1px solid var(--brass);transform:rotate(45deg);margin-left:8px;vertical-align:2px}
.drop{position:absolute;top:100%;left:-18px;min-width:240px;background:var(--paper);border:1px solid var(--rule);box-shadow:0 22px 44px rgba(20,18,15,.14);padding:8px 0;opacity:0;visibility:hidden;transform:translateY(8px);transition:opacity .25s,transform .25s,visibility .25s;z-index:60}
.drop::before{content:"";position:absolute;top:-14px;left:0;right:0;height:14px}
.ni:hover .drop{opacity:1;visibility:visible;transform:translateY(0)}
.drop a{display:block;padding:9px 22px;font-size:.85rem;color:var(--ink);letter-spacing:.02em}
.drop a::after{display:none}
.drop a:hover{background:var(--cream);color:var(--brass)}
.drop a:first-child{color:var(--brass);font-weight:600;letter-spacing:.18em;text-transform:uppercase;font-size:.68rem;border-bottom:1px solid var(--rule);margin-bottom:6px;padding-bottom:11px}
.brand{font-size:1.5rem;font-weight:900;text-align:center;line-height:1}
.brand small{display:block;font-family:Inter;font-size:.56rem;letter-spacing:.34em;font-weight:600;color:var(--brass);margin-top:5px;text-transform:uppercase}
.burger,.mnav{display:none}
.hero{position:relative;min-height:82vh;display:flex;align-items:flex-end;color:var(--cream);overflow:hidden}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:grayscale(.2) brightness(.6)}
.hero::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,18,15,.15),rgba(20,18,15,.78))}
.hero__in{position:relative;z-index:2;padding:0 32px 78px;max-width:1180px;margin:0 auto;width:100%}
.hero__rule{width:1px;height:64px;background:var(--brass);margin-bottom:24px}
.hero h1{font-size:clamp(2.4rem,6vw,5rem);line-height:1.02;font-weight:900;max-width:16ch}
.hero__lead{margin:20px 0 28px;max-width:46ch;color:#e8e1d4;font-size:1.05rem}
.hero__cta{display:flex;gap:28px;align-items:center;flex-wrap:wrap}.hero__cta .ulink{color:var(--cream)}
.manifesto{padding:110px 0;text-align:center}
.manifesto p{font-family:"Playfair Display",serif;font-size:clamp(1.5rem,3.2vw,2.4rem);line-height:1.4;max-width:22ch;margin:20px auto 0}
.manifesto .em{font-style:italic;color:var(--brass)}
.svc{border-top:1px solid var(--rule)}
.svc__row{display:grid;grid-template-columns:110px 1fr auto;gap:28px;align-items:baseline;padding:34px 0;border-bottom:1px solid var(--rule);transition:padding-left .4s}
.svc__row:hover{padding-left:12px}
.svc__no{font-family:"Playfair Display",serif;font-size:1.3rem;color:var(--brass)}
.svc__t{font-family:"Playfair Display",serif;font-size:clamp(1.6rem,3.2vw,2.4rem);font-weight:700}
.svc__d{max-width:38ch;color:var(--muted)}
.svc__row:hover .svc__t{color:var(--brass)}
.break{position:relative;min-height:52vh;display:flex;align-items:center;justify-content:center;color:var(--cream);text-align:center}
.break img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness(.5)}
.break blockquote{position:relative;z-index:2;font-family:"Playfair Display",serif;font-style:italic;font-size:clamp(1.5rem,3.4vw,2.5rem);max-width:20ch;line-height:1.3;padding:0 24px}
.break cite{display:block;font-family:Inter;font-style:normal;font-size:.72rem;letter-spacing:.22em;text-transform:uppercase;color:var(--brass);margin-top:22px}
.sec{padding:104px 0}
.proc__head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:56px;flex-wrap:wrap;gap:16px}
.proc__head h2{font-family:"Playfair Display",serif;font-size:clamp(2rem,4vw,3rem);font-weight:700;max-width:14ch}
.timeline{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--ink)}
.tl{padding:26px 20px 0;border-right:1px solid var(--rule)}.tl:last-child{border-right:0}
.tl__no{font-family:"Playfair Display",serif;font-size:2.2rem;margin-top:-40px;background:var(--paper);display:inline-block;padding-right:12px}
.tl h3{font-size:1rem;margin:14px 0 8px}.tl p{font-size:.9rem;color:var(--muted)}
.quotes{background:var(--cream)}.quotes__grid{display:grid;grid-template-columns:1fr 1fr;gap:60px}
.q blockquote{font-family:"Playfair Display",serif;font-size:1.45rem;line-height:1.45;font-style:italic}
.q cite{display:block;font-style:normal;font-size:.74rem;letter-spacing:.16em;text-transform:uppercase;color:var(--brass);margin-top:18px}
.q .stars{color:var(--brass);letter-spacing:3px;margin-bottom:16px}
.est__grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:64px;align-items:center}
.est h2{font-family:"Playfair Display",serif;font-size:clamp(2rem,4vw,3rem);font-weight:700;margin-bottom:18px}
.est p{color:var(--muted);max-width:42ch;margin-bottom:28px}
.rate{border-top:1px solid var(--ink)}
.rate__row{display:flex;justify-content:space-between;align-items:baseline;padding:20px 4px;border-bottom:1px solid var(--rule)}
.rate__row span:first-child{font-family:"Playfair Display",serif;font-size:1.2rem}
.rate__row span:last-child{color:var(--brass);font-weight:600}
/* inner pages */
.phero{background:var(--cream);border-bottom:1px solid var(--rule);padding:64px 0 54px}
.crumb{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin-bottom:16px}
.crumb a{color:var(--brass)}
.phero h1{font-family:"Playfair Display",serif;font-size:clamp(2.1rem,5vw,3.6rem);font-weight:900;max-width:20ch}
.article{display:grid;grid-template-columns:1fr 300px;gap:64px;padding:80px 0}
.article .body{max-width:64ch}
.article h2{font-family:"Playfair Display",serif;font-size:1.7rem;font-weight:700;margin:34px 0 12px}
.article h3{font-family:"Playfair Display",serif;font-size:1.3rem;margin:28px 0 10px}
.article p{margin:0 0 16px;color:#3c372f}.article ul{margin:0 0 16px 20px;color:#3c372f}
.article img{border-radius:2px;margin:22px 0;filter:grayscale(.15)}
.article details{border-top:1px solid var(--rule);padding:16px 0}.article summary{font-family:"Playfair Display",serif;font-size:1.15rem;cursor:pointer}
.aside{align-self:start;position:sticky;top:100px;border:1px solid var(--ink);padding:28px}
.aside h3{font-family:"Playfair Display",serif;font-size:1.4rem;margin-bottom:8px}
.aside p{color:var(--muted);font-size:.92rem;margin-bottom:18px}
.aside .tel{display:block;font-family:"Playfair Display",serif;font-size:1.6rem;color:var(--brass);margin-bottom:16px}
.idx{padding:16px 0 90px}
footer{background:var(--ink);color:var(--cream);padding:88px 0 38px}
.f-word{font-family:"Playfair Display",serif;font-size:clamp(3rem,11vw,9rem);font-weight:900;line-height:.9;border-bottom:1px solid #3a352d;padding-bottom:36px;margin-bottom:44px}
.f-cols{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:38px;font-size:.9rem}
.f-cols h4{font-size:.66rem;letter-spacing:.24em;text-transform:uppercase;color:var(--brass);margin-bottom:16px}
.f-cols a,.f-cols p{color:#c9c1b3;display:block;padding:5px 0}.f-cols a:hover{color:#fff}
.f-legal{display:flex;justify-content:space-between;margin-top:50px;padding-top:22px;border-top:1px solid #3a352d;font-size:.74rem;letter-spacing:.1em;text-transform:uppercase;color:#8a8377;flex-wrap:wrap;gap:12px}
@media(max-width:860px){
 .nav{grid-template-columns:auto auto;padding:16px 22px}.nav__side{display:none}.brand{text-align:left}
 .burger{display:block;justify-self:end;background:none;border:1px solid var(--ink);padding:9px 14px;font-size:.7rem;letter-spacing:.2em;text-transform:uppercase}
 .mnav{flex-direction:column;padding:8px 22px 18px;border-top:1px solid var(--rule)}.mnav.open{display:flex}
 .mnav a{padding:12px 0;border-bottom:1px solid var(--rule);letter-spacing:.08em}
 .svc__row{grid-template-columns:56px 1fr;gap:14px}.svc__d{grid-column:1/-1;margin-top:6px}
 .timeline,.quotes__grid,.est__grid,.proc__head,.article,.f-cols{grid-template-columns:1fr}
 .timeline .tl{border-bottom:1px solid var(--rule)}.aside{position:static}
}
"""

def _iron_drop(pages, cat, all_url, all_label, trigger):
    e = H.esc
    if not _cat(pages, cat):
        return ""
    links = "".join(f'<a href="{u}">{e(l)}</a>' for u, l in _menu(pages, cat, all_url, all_label))
    return f'<div class="ni"><a class="ulink" href="{all_url}">{trigger}<span class="dc"></span></a><div class="drop">{links}</div></div>'

def _iron_header(t, pages):
    e = H.esc
    phone = f'<a href="tel:{t["tel"]}">{e(t["phone"])}</a>' if t.get("phone") else '<a href="/request-a-quote/">Book online</a>'
    left = (_iron_drop(pages, "service", "/services/", "All Work", "The Work")
            + _iron_drop(pages, "area", "/service-areas/", "All Areas", "Service Areas")
            + _iron_drop(pages, "guide", "/guides/", "All Guides", "Guides"))
    return (f'<div class="util"><div class="wrap"><span>Est. 2004 · {e(t["city"])}, {e(t["st"])}</span>'
            f'<span>By appointment · {phone}</span></div></div>'
            f'<header><div class="nav">'
            f'<nav class="nav__side">{left}</nav>'
            f'<a href="/" class="brand serif">{e(t["brand"].split(" ")[0])}<small>{e(" ".join(t["brand"].split(" ")[1:]) or "Garage Works")}</small></a>'
            f'<nav class="nav__side nav__side--r"><a class="ulink" href="/about/">Studio</a><a class="ulink" href="/contact/">Contact</a><a class="ulink" href="/request-a-quote/">Book a Visit</a></nav>'
            f'<button class="burger" onclick="document.getElementById(\'m\').classList.toggle(\'open\')">Menu</button></div>'
            f'<nav class="mnav" id="m"><a href="/services/">The Work</a><a href="/service-areas/">Service Areas</a><a href="/guides/">Guides</a><a href="/about/">Studio</a><a href="/contact/">Contact</a><a href="/request-a-quote/">Book a Visit</a></nav></header>')

def _iron_footer(t, pages):
    e = H.esc
    svc = _cat(pages, "service")[:4]
    slinks = "".join(f'<a href="{p["url"]}">{e(H.area_label(p))}</a>' for p in svc) or '<a href="/services/">Services</a>'
    return (f'<footer><div class="wrap"><div class="f-word serif">{e(t["brand"].split(" ")[0])}.</div>'
            f'<div class="f-cols">'
            f'<div><h4>The Studio</h4><p>A {e(t["city"])} garage door atelier working by appointment across the metro. Small on purpose.</p><p style="color:var(--brass);margin-top:10px">{e(t["phone"])}</p></div>'
            f'<div><h4>Work</h4>{slinks}<a href="/services/">All work</a></div>'
            f'<div><h4>Studio</h4><a href="/about/">About</a><a href="/guides/">Guides</a><a href="/request-a-quote/">Book a visit</a><a href="/contact/">Contact</a></div>'
            f'<div><h4>Visit</h4><p>{e(t["city"])}, {e(t["st"])}</p><p>Mon–Fri, by appt.</p></div></div>'
            f'<div class="f-legal"><span>© 2024 {e(t["brand"])}</span><span>{e(t["city"])} · {e(t["st"])}</span></div></div></footer>')

def iron_home(t, pages):
    e = H.esc
    h1, lead, faqs, svc, areas, guides = _home_data(t, pages)
    tiles = _svc_tiles(pages)
    rows = "".join(f'<a class="svc__row" href="{u}"><div class="svc__no serif">{i+1:02d}</div><div class="svc__t serif">{title}</div><div class="svc__d">{blurb}</div></a>'
                   for i, (ic, title, blurb, u) in enumerate(tiles[:4]))
    q = faqs[0]
    schemas = [H.org_schema(t), H.faq_schema(faqs)]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), lead, "/", schemas, IRON_FONTS, og=H.HERO_IMG)
            + _iron_header(t, pages)
            + f'<section class="hero"><img src="{PHOTOS}{H.HERO_IMG}" alt="{e(t["city"])} garage door"><div class="hero__in">'
              f'<div class="hero__rule"></div><p class="kick" style="color:#e6c893">Repair · Restoration · Installation</p>'
              f'<h1 class="serif">{e(h1)}</h1><p class="hero__lead">{e(lead)}</p>'
              f'<div class="hero__cta"><a class="pill" style="border-color:#e8e1d4;color:#f6f2ea" href="/services/">See The Work</a>'
              f'<a class="ulink" href="tel:{t["tel"]}">Or call the studio &nbsp;→</a></div></div></section>'
            + f'<section class="manifesto wrap"><span class="kick">Our belief</span>'
              f'<p class="serif">A door opens ten thousand times a year. It deserves <span class="em">more thought</span> than a rushed afternoon and a stapled invoice.</p></section>'
            + f'<section class="svc wrap">{rows}</section>'
            + f'<section class="break"><img src="{PHOTOS}gd-6.jpg" alt="Craftsman at work"><blockquote class="serif">"They fixed the door. Then they told us how to keep it from breaking again."<cite>— A {e(t["city"])} homeowner</cite></blockquote></section>'
            + f'<section class="sec wrap"><div class="proc__head"><h2 class="serif">Unhurried, and in the right order.</h2><span class="kick">The process</span></div>'
              f'<div class="timeline"><div class="tl"><div class="tl__no serif">I</div><h3>Conversation</h3><p>You describe the door. We ask what a phone quote never does.</p></div>'
              f'<div class="tl"><div class="tl__no serif">II</div><h3>Inspection</h3><p>On time, a written assessment, a price before a wrench turns.</p></div>'
              f'<div class="tl"><div class="tl__no serif">III</div><h3>The Work</h3><p>Done once, cleanly, with parts sized for the door.</p></div>'
              f'<div class="tl"><div class="tl__no serif">IV</div><h3>Aftercare</h3><p>Notes on what we found, and a standing line for questions.</p></div></div></section>'
            + f'<section class="sec quotes"><div class="wrap quotes__grid">'
              f'<div class="q"><div class="stars">★★★★★</div><blockquote class="serif">"{e(q[1])}"</blockquote><cite>{e(t["city"])} homeowner</cite></div>'
              f'<div class="q"><div class="stars">★★★★★</div><blockquote class="serif">"They talked us out of a full replacement. Rare to be sold less than you walked in expecting."</blockquote><cite>Repeat client — {e(t["city"])}</cite></div></div></section>'
            + f'<section class="sec est wrap"><div class="est__grid">'
              f'<div><span class="kick">Begin</span><h2 class="serif">Every door is a conversation.</h2>'
              f'<p>Tell us what yours is doing, and we\'ll tell you honestly what it needs — repair, restoration, or a fresh install for your {e(t["city"])} home.</p>'
              f'<a class="pill pill--brass" href="/request-a-quote/">Request an Estimate</a></div>'
              f'<div style="border:1px solid var(--rule);overflow:hidden;min-height:300px"><img src="{PHOTOS}gd-2.jpg" alt="{e(t["city"])} garage door work" style="width:100%;height:100%;object-fit:cover;filter:grayscale(.15)"></div>'
              f'</div></section>'
            + _iron_footer(t, pages) + _iron_js() + "</body></html>")

def _iron_js():
    return "<script>document.querySelectorAll('.svc__row').forEach(r=>{});</script>"

def iron_inner(t, pages, p):
    e = H.esc
    label, parent = _LABELS.get(p["cat"], ("", "/"))
    h1 = p["h1"] or H.area_label(p)
    img = H.INNER_IMGS[H._stable_idx(p["slug"] or p["url"], len(H.INNER_IMGS))]
    body = _inner_parts(t, p)
    aside = (f'<aside class="aside"><h3 class="serif">Book a visit</h3><p>Considered garage door work in {e(t["city"])}, {e(t["st"])}.</p>'
             f'<a class="tel serif" href="tel:{t["tel"]}">{e(t["phone"])}</a>'
             f'<a class="pill pill--brass" href="/request-a-quote/">Request an Estimate</a></aside>')
    schemas = _inner_schemas(t, p, h1, label, parent)
    return (_head(t, H.seo_title(p["title"] or f"{h1} | {t['brand']}"), p["meta"] or "", p["url"], schemas, IRON_FONTS, og=img)
            + _iron_header(t, pages)
            + f'<section class="phero"><div class="wrap"><div class="crumb"><a href="/">Home</a> / <a href="{parent}">{label}</a> / {e(h1)}</div><h1 class="serif">{e(h1)}</h1></div></section>'
            + f'<div class="wrap"><div class="article"><div class="body"><img src="{PHOTOS}{img}" alt="{e(h1)}" loading="lazy">{body}</div>{aside}</div></div>'
            + _iron_footer(t, pages) + "</body></html>")

def iron_index(t, pages, cat, url, h1, eyebrow, blurb):
    e = H.esc
    items = _cat(pages, cat)
    rows = "".join(f'<a class="svc__row" href="{p["url"]}"><div class="svc__no serif">{i+1:02d}</div><div class="svc__t serif">{e(H.area_label(p))}</div><div class="svc__d">{e((p["meta"] or "").split(".")[0])}</div></a>'
                   for i, p in enumerate(items))
    schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), blurb, url, schemas, IRON_FONTS)
            + _iron_header(t, pages)
            + f'<section class="phero"><div class="wrap"><div class="crumb"><a href="/">Home</a> / {e(h1)}</div><h1 class="serif">{e(h1)}</h1><p class="kick" style="margin-top:14px">{eyebrow}</p></div></section>'
            + f'<section class="svc wrap idx">{rows}</section>'
            + _iron_footer(t, pages) + "</body></html>")

def iron_trust(t, pages, url, h1, blocks, is_quote=False):
    e = H.esc
    body = "".join(f'<h2 class="serif">{e(hh)}</h2><p>{e(bb)}</p>' for hh, bb in blocks)
    aside = (f'<aside class="aside"><h3 class="serif">Talk to us</h3><p>Garage door help in {e(t["city"])}, {e(t["st"])}.</p>'
             f'<a class="tel serif" href="tel:{t["tel"]}">{e(t["phone"])}</a>'
             f'<a class="pill pill--brass" href="/request-a-quote/">Request a Visit</a></aside>')
    schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), f"{h1} — {t['brand']}, {t['city']}, {t['st']}.", url, schemas, IRON_FONTS)
            + _iron_header(t, pages)
            + f'<section class="phero"><div class="wrap"><div class="crumb"><a href="/">Home</a> / {e(h1)}</div><h1 class="serif">{e(h1)}</h1></div></section>'
            + f'<div class="wrap"><div class="article"><div class="body">{body}</div>{aside}</div></div>'
            + _iron_footer(t, pages) + "</body></html>")


# ================================================================ VOLT
VOLT_FONTS = "family=Archivo+Black&family=Space+Mono:wght@400;700&family=Inter:wght@400;600;800"
VOLT_CSS = r"""
:root{--bg:#0e0e12;--card:#17171d;--lime:#c8ff3d;--blue:#3d6bff;--line:#2b2b34;--txt:#e9e9ee;--dim:#9a9aa6}
*{margin:0;padding:0;box-sizing:border-box}html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font-family:Inter,sans-serif;line-height:1.55}
.disp{font-family:"Archivo Black",sans-serif;text-transform:uppercase}.mono{font-family:"Space Mono",monospace}
.wrap{max-width:1200px;margin:0 auto;padding:0 28px}a{color:inherit;text-decoration:none}img{display:block;max-width:100%}
.tag{display:inline-block;font-family:"Space Mono",monospace;font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;border:1px solid var(--lime);color:var(--lime);padding:5px 10px}
.btn{display:inline-flex;align-items:center;gap:10px;font-family:"Archivo Black",sans-serif;font-size:.82rem;text-transform:uppercase;padding:15px 26px;border:2px solid #000;cursor:pointer;transition:transform .12s,box-shadow .12s}
.btn--lime{background:var(--lime);color:#0e0e12;box-shadow:6px 6px 0 #000}
.btn--out{background:transparent;color:var(--txt);border-color:var(--txt);box-shadow:6px 6px 0 var(--blue)}
.btn:hover{transform:translate(3px,3px)}.btn--lime:hover{box-shadow:3px 3px 0 #000}.btn--out:hover{box-shadow:3px 3px 0 var(--blue)}
header{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:2px solid var(--lime)}
.hd{display:flex;align-items:center;justify-content:space-between;padding:16px 28px;max-width:1200px;margin:0 auto}
.logo{display:flex;align-items:center;gap:10px}
.logo__mark{font-family:"Archivo Black";background:var(--lime);color:#000;padding:6px 10px;border:2px solid #000;box-shadow:3px 3px 0 var(--blue);font-size:1.05rem}
.logo__t{font-family:"Archivo Black";font-size:1.1rem;text-transform:uppercase}
.hd nav{display:flex;gap:24px;font-family:"Space Mono";font-size:.82rem;text-transform:uppercase}.hd nav a:hover{color:var(--lime)}
.hd nav .ni{position:relative}
.hd nav .ni>a::after{content:" ▾";color:var(--lime)}
.hd nav .drop{position:absolute;top:100%;left:-8px;min-width:230px;background:var(--card);border:2px solid var(--lime);padding:6px 0;opacity:0;visibility:hidden;transform:translateY(8px);transition:.14s;z-index:70}
.hd nav .drop::before{content:"";position:absolute;top:-16px;left:0;right:0;height:16px}
.hd nav .ni:hover .drop{opacity:1;visibility:visible;transform:translateY(0)}
.hd nav .drop a{display:block;padding:10px 18px;font-family:"Space Mono";font-size:.78rem;text-transform:none;color:var(--txt)}
.hd nav .drop a::after{content:""}
.hd nav .drop a:hover{background:#0e0e12;color:var(--lime)}
.hd nav .drop a:first-child{color:var(--lime);text-transform:uppercase;font-size:.68rem;border-bottom:1px solid var(--line)}
.hd__cta{display:flex;align-items:center;gap:16px}.hd__cta .ph{font-family:"Space Mono";font-size:.82rem;color:var(--dim)}
.mtoggle{display:none;font-family:"Archivo Black";background:var(--lime);color:#000;border:2px solid #000;padding:8px 12px;cursor:pointer}.mnav{display:none}
.hero{border-bottom:2px solid var(--line);background:linear-gradient(var(--line) 1px,transparent 1px) 0 0/100% 46px,radial-gradient(var(--line) 1px,transparent 1px) 0 0/26px 26px}
.hero__grid{display:grid;grid-template-columns:1.15fr .85fr;gap:44px;padding:66px 28px;max-width:1200px;margin:0 auto;align-items:center}
.hero h1{font-family:"Archivo Black";font-size:clamp(2.4rem,5.6vw,4.6rem);line-height:.94;text-transform:uppercase}
.hero h1 em{font-style:normal;color:var(--lime);border-bottom:6px solid var(--blue)}
.hero__sub{margin:22px 0 30px;max-width:42ch;color:var(--dim);font-size:1.05rem}
.hero__btns{display:flex;gap:20px;flex-wrap:wrap}
.widget{background:var(--card);border:2px solid #000;box-shadow:10px 10px 0 var(--lime);padding:26px}
.widget h3{font-family:"Archivo Black";text-transform:uppercase;font-size:1rem;margin-bottom:4px}
.widget p{font-family:"Space Mono";font-size:.74rem;color:var(--dim);margin-bottom:18px}
.field{display:block;font-family:"Space Mono";font-size:.68rem;text-transform:uppercase;color:var(--dim);margin:14px 0 6px}
.ipt{width:100%;background:#0e0e12;border:2px solid var(--line);color:var(--txt);padding:12px;font-family:Inter}
.ipt:focus{outline:none;border-color:var(--lime)}.widget .btn{width:100%;justify-content:center;margin-top:20px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:2px solid var(--line)}
.stat{padding:32px 24px;border-right:2px solid var(--line);text-align:center}.stat:last-child{border-right:0}
.stat b{font-family:"Archivo Black";font-size:2.2rem;color:var(--lime);display:block;line-height:1}
.stat span{font-family:"Space Mono";font-size:.72rem;text-transform:uppercase;color:var(--dim)}
.sec{padding:84px 0}
.sec__h{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin-bottom:42px;flex-wrap:wrap}
.sec__h h2{font-family:"Archivo Black";font-size:clamp(1.9rem,4vw,3rem);text-transform:uppercase;line-height:1}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:26px}
.card{background:var(--card);border:2px solid #000;box-shadow:7px 7px 0 var(--line);padding:26px;transition:.14s;display:block}
.card:hover{transform:translate(-3px,-3px);box-shadow:10px 10px 0 var(--blue)}
.card__ic{width:46px;height:46px;display:grid;place-items:center;background:var(--lime);color:#000;border:2px solid #000;font-family:"Archivo Black";margin-bottom:16px}
.card h3{font-family:"Archivo Black";text-transform:uppercase;font-size:1.05rem;margin-bottom:10px}
.card p,.card ul{font-family:"Space Mono";font-size:.82rem;color:var(--dim)}.card ul{list-style:none}
.card li{padding:5px 0 5px 18px;position:relative}.card li::before{content:"▸";position:absolute;left:0;color:var(--lime)}
.pricing{background:#111116;border-top:2px solid var(--line);border-bottom:2px solid var(--line)}
.tiers{display:grid;grid-template-columns:repeat(3,1fr);border:2px solid #000}
.tier{padding:32px 26px;border-right:2px solid #000;background:var(--card)}.tier:last-child{border-right:0}
.tier--hot{background:var(--lime);color:#0e0e12}
.tier__name{font-family:"Space Mono";text-transform:uppercase;font-size:.76rem}
.tier__price{font-family:"Archivo Black";font-size:2.6rem;line-height:1;margin:12px 0}.tier__price small{font-family:"Space Mono";font-size:.8rem}
.tier ul{list-style:none;margin:16px 0 22px;font-size:.9rem}.tier li{padding:8px 0;border-top:1px dashed rgba(255,255,255,.16)}
.tier--hot li{border-color:rgba(0,0,0,.2)}.tier .btn{width:100%;justify-content:center}
.tgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.tcard{border:2px solid var(--line);padding:24px;background:var(--card)}.tcard .stars{color:var(--lime);letter-spacing:2px;margin-bottom:12px}
.tcard p{margin-bottom:16px}.tcard cite{font-family:"Space Mono";font-size:.76rem;color:var(--dim);font-style:normal}
.faq{max-width:820px;margin:0 auto}
.q2{border:2px solid var(--line);margin-bottom:14px;background:var(--card)}
.q2 summary{list-style:none;cursor:pointer;padding:20px 24px;font-family:"Archivo Black";font-size:1rem;text-transform:uppercase;display:flex;justify-content:space-between;align-items:center}
.q2 summary::-webkit-details-marker{display:none}.q2 summary::after{content:"+";color:var(--lime);font-size:1.6rem}.q2[open] summary::after{content:"–"}
.q2 p{padding:0 24px 22px;color:var(--dim)}
.cta{background:var(--lime);color:#0e0e12;text-align:center;padding:76px 28px;border-top:2px solid #000;border-bottom:2px solid #000}
.cta h2{font-family:"Archivo Black";font-size:clamp(2.2rem,6vw,3.8rem);text-transform:uppercase;line-height:.96;max-width:18ch;margin:0 auto 24px}
.cta .btn{background:#0e0e12;color:var(--lime);border-color:#0e0e12;box-shadow:6px 6px 0 var(--blue)}
/* inner */
.phero{border-bottom:2px solid var(--line);padding:52px 0;background:linear-gradient(var(--line) 1px,transparent 1px) 0 0/100% 44px}
.crumb{font-family:"Space Mono";font-size:.74rem;text-transform:uppercase;color:var(--dim);margin-bottom:14px}.crumb a{color:var(--lime)}
.phero h1{font-family:"Archivo Black";font-size:clamp(2rem,5vw,3.4rem);text-transform:uppercase;max-width:22ch}
.article{display:grid;grid-template-columns:1fr 300px;gap:40px;padding:66px 0}
.article .body{border:2px solid var(--line);padding:34px;background:var(--card)}
.article h2{font-family:"Archivo Black";text-transform:uppercase;font-size:1.3rem;margin:26px 0 10px;color:var(--lime)}
.article h3{font-family:"Archivo Black";text-transform:uppercase;font-size:1.05rem;margin:22px 0 8px}
.article p{margin:0 0 14px;color:#c5c5cf}.article ul{margin:0 0 14px 20px;color:#c5c5cf}
.article img{border:2px solid #000;margin:20px 0}
.article details{border-top:1px solid var(--line);padding:14px 0}.article summary{font-family:"Archivo Black";text-transform:uppercase;font-size:.92rem;cursor:pointer}
.aside{align-self:start;position:sticky;top:96px;border:2px solid #000;box-shadow:8px 8px 0 var(--lime);padding:26px;background:var(--card)}
.aside h3{font-family:"Archivo Black";text-transform:uppercase;font-size:1rem;margin-bottom:14px}
.aside .tel{display:block;font-family:"Archivo Black";font-size:1.4rem;color:var(--lime);margin:10px 0 16px}
footer{background:#0a0a0d;padding:0 0 30px}
.f-news{border-bottom:2px solid var(--line);padding:44px 0}
.f-news .wrap{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}
.f-news h3{font-family:"Archivo Black";text-transform:uppercase;font-size:1.5rem;max-width:16ch}
.f-form{display:flex;border:2px solid var(--lime)}.f-form input{background:#0e0e12;border:0;color:#fff;padding:14px 16px;font-family:"Space Mono";min-width:220px}
.f-form input:focus{outline:none}.f-form button{background:var(--lime);color:#000;border:0;font-family:"Archivo Black";padding:0 22px;text-transform:uppercase;cursor:pointer}
.f-cols{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:30px;padding:50px 0}
.f-cols h4{font-family:"Space Mono";font-size:.72rem;text-transform:uppercase;color:var(--lime);margin-bottom:16px}
.f-cols a,.f-cols p{display:block;color:var(--dim);padding:5px 0;font-size:.92rem}.f-cols a:hover{color:#fff}
.f-social{display:flex;gap:10px;margin-top:12px}.f-social a{width:38px;height:38px;border:2px solid var(--line);display:grid;place-items:center;font-family:"Archivo Black";font-size:.8rem}
.f-social a:hover{background:var(--lime);color:#000}
.f-bot{border-top:2px solid var(--line);padding-top:22px;font-family:"Space Mono";font-size:.74rem;color:#6a6a76;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}
@media(max-width:900px){.hd nav,.hd__cta .ph{display:none}.mtoggle{display:block}
 .hero__grid,.grid3,.tiers,.tgrid,.f-cols,.stats,.article{grid-template-columns:1fr}
 .tier,.stat{border-right:0;border-bottom:2px solid #000}.stats{border:0}.stat{border-bottom:2px solid var(--line)}
 .mnav{flex-direction:column;background:var(--card);border-bottom:2px solid var(--lime)}.mnav.open{display:flex}
 .mnav a{padding:14px 28px;border-top:1px solid var(--line);font-family:"Space Mono";text-transform:uppercase}
 .aside{position:static}.f-news .wrap{flex-direction:column;align-items:flex-start}}
"""

def _volt_drop(pages, cat, all_url, all_label, trigger):
    e = H.esc
    if not _cat(pages, cat):
        return f'<a href="{all_url}">{trigger}</a>'
    links = "".join(f'<a href="{u}">{e(l)}</a>' for u, l in _menu(pages, cat, all_url, all_label))
    return f'<div class="ni"><a href="{all_url}">{trigger}</a><div class="drop">{links}</div></div>'

def _volt_header(t, pages):
    e = H.esc
    nav = (_volt_drop(pages, "service", "/services/", "All Services", "Services")
           + _volt_drop(pages, "area", "/service-areas/", "All Areas", "Areas")
           + _volt_drop(pages, "guide", "/guides/", "All Guides", "Guides")
           + '<a href="/about/">About</a>')
    return (f'<header><div class="hd"><a href="/" class="logo"><span class="logo__mark">V⚡</span><span class="logo__t">{e(t["brand"].split(" ")[0])}</span></a>'
            f'<nav>{nav}</nav>'
            f'<div class="hd__cta"><span class="ph">{e(t["phone"])}</span><a class="btn btn--lime" href="/request-a-quote/">Get a Quote →</a></div>'
            f'<button class="mtoggle" onclick="document.getElementById(\'mn\').classList.toggle(\'open\')">≡</button></div>'
            f'<nav class="mnav" id="mn"><a href="/services/">Services</a><a href="/service-areas/">Areas</a><a href="/guides/">Guides</a><a href="/about/">About</a><a href="/request-a-quote/">Get a Quote</a></nav></header>')

def _volt_footer(t, pages):
    e = H.esc
    svc = _cat(pages, "service")[:4]
    slinks = "".join(f'<a href="{p["url"]}">{e(H.area_label(p))}</a>' for p in svc) or '<a href="/services/">Services</a>'
    return (f'<footer><div class="wrap"><div class="f-cols">'
            f'<div><div class="logo" style="margin-bottom:14px"><span class="logo__mark">V⚡</span><span class="logo__t">{e(t["brand"].split(" ")[0])}</span></div>'
            f'<p>Flat-rate garage door repair &amp; installation across {e(t["city"])}. Fast, fixed, guaranteed.</p><div class="f-social"><a>IG</a><a>X</a><a>YT</a><a>in</a></div></div>'
            f'<div><h4>Services</h4>{slinks}<a href="/services/">All services</a></div>'
            f'<div><h4>Company</h4><a href="/about/">About</a><a href="/guides/">Guides</a><a href="/service-areas/">Areas</a><a href="/request-a-quote/">Book online</a></div>'
            f'<div><h4>24/7 Line</h4><p style="color:var(--lime);font-family:\'Space Mono\'">{e(t["phone"])}</p><p>{e(t["city"])}, {e(t["st"])} &amp; metro</p><p>Open 24 hours</p></div></div>'
            f'<div class="f-bot"><span>© 2024 {e(t["brand"]).upper()}</span><span>// {e(t["city"]).upper()}.{e(t["st"])}</span></div></div></footer>')

def volt_home(t, pages):
    e = H.esc
    h1, lead, faqs, svc, areas, guides = _home_data(t, pages)
    tiles = _svc_tiles(pages)
    cards = "".join(f'<a class="card" href="{u}"><div class="card__ic">↯</div><h3>{title}</h3><p>{blurb}</p></a>' for ic, title, blurb, u in tiles)
    faq = "".join(f'<details class="q2"{" open" if i==0 else ""}><summary>{e(q)}</summary><p>{e(a)}</p></details>' for i, (q, a) in enumerate(faqs))
    schemas = [H.org_schema(t), H.faq_schema(faqs)]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), lead, "/", schemas, VOLT_FONTS, og=H.HERO_IMG)
            + _volt_header(t, pages)
            + f'<section class="hero"><div class="hero__grid"><div><span class="tag">⚡ Same-day service · {e(t["city"])}, {e(t["st"])}</span>'
              f'<h1 style="margin-top:18px">Garage door <em>down?</em> We\'re already moving.</h1><p class="hero__sub">{e(lead)}</p>'
              f'<div class="hero__btns"><a class="btn btn--lime" href="/request-a-quote/">Book a Fix</a><a class="btn btn--out" href="/services/">See Services</a></div></div>'
              f'<div class="widget"><h3>Instant Quote</h3><p>// avg. response: 8 minutes</p>'
              f'<label class="field">What\'s wrong?</label><select class="ipt"><option>Broken spring</option><option>Won\'t open / close</option><option>Opener dead</option><option>Off the track</option><option>New door install</option></select>'
              f'<label class="field">ZIP code</label><input class="ipt" placeholder="ZIP"><label class="field">Phone</label><input class="ipt" placeholder="{e(t["phone"])}">'
              f'<a class="btn btn--lime" href="tel:{t["tel"]}">Get My Price →</a></div></div></section>'
            + f'<div class="stats"><div class="stat"><b>60s</b><span>To book online</span></div><div class="stat"><b>Same-day</b><span>On most repairs</span></div>'
              f'<div class="stat"><b>Flat-rate</b><span>Priced upfront</span></div><div class="stat"><b>24/7</b><span>Emergency line</span></div></div>'
            + f'<section class="sec wrap"><div class="sec__h"><h2>What we <span style="color:var(--lime)">fix</span></h2><span class="mono" style="color:var(--dim)">// core services</span></div><div class="grid3">{cards}</div></section>'
            + f'<section class="sec wrap"><div class="sec__h"><h2>{e(t["city"])} <span style="color:var(--lime)">talks</span></h2></div><div class="tgrid">'
              f'<div class="tcard"><div class="stars">★★★★★</div><p>"Booked in the morning, spring replaced by noon. Online quote was the exact price I paid."</p><cite>// local homeowner</cite></div>'
              f'<div class="tcard"><div class="stars">★★★★★</div><p>"Opener died on a Sunday. Someone out in an hour. No weekend surcharge nonsense."</p><cite>// {e(t["city"])} resident</cite></div>'
              f'<div class="tcard"><div class="stars">★★★★★</div><p>"Flat pricing is the whole reason. No hourly meter, no found-another-problem upsell."</p><cite>// repeat customer</cite></div></div></section>'
            + f'<section class="sec wrap" style="padding-top:10px"><div class="sec__h"><h2>Straight <span style="color:var(--blue)">answers</span></h2></div><div class="faq">{faq}</div></section>'
            + f'<section class="cta"><h2>Stop wrestling that door.</h2><a class="btn" href="tel:{t["tel"]}">⚡ Call {e(t["phone"])}</a></section>'
            + _volt_footer(t, pages) + "</body></html>")

def _volt_aside(t):
    e = H.esc
    return (f'<aside class="aside"><h3>Book a fix</h3><p style="color:var(--dim);font-family:\'Space Mono\';font-size:.82rem">// flat-rate, same-day</p>'
            f'<a class="tel" href="tel:{t["tel"]}">{e(t["phone"])}</a>'
            f'<a class="btn btn--lime" href="/request-a-quote/" style="width:100%;justify-content:center">Get a Quote →</a></aside>')

def volt_inner(t, pages, p):
    e = H.esc
    label, parent = _LABELS.get(p["cat"], ("", "/"))
    h1 = p["h1"] or H.area_label(p)
    img = H.INNER_IMGS[H._stable_idx(p["slug"] or p["url"], len(H.INNER_IMGS))]
    body = _inner_parts(t, p)
    schemas = _inner_schemas(t, p, h1, label, parent)
    return (_head(t, H.seo_title(p["title"] or f"{h1} | {t['brand']}"), p["meta"] or "", p["url"], schemas, VOLT_FONTS, og=img)
            + _volt_header(t, pages)
            + f'<section class="phero"><div class="wrap"><div class="crumb"><a href="/">Home</a> // <a href="{parent}">{label}</a> // {e(h1)}</div><h1>{e(h1)}</h1></div></section>'
            + f'<div class="wrap"><div class="article"><div class="body"><img src="{PHOTOS}{img}" alt="{e(h1)}" loading="lazy">{body}</div>{_volt_aside(t)}</div></div>'
            + _volt_footer(t, pages) + "</body></html>")

def volt_index(t, pages, cat, url, h1, eyebrow, blurb):
    e = H.esc
    items = _cat(pages, cat)
    cards = "".join(f'<a class="card" href="{p["url"]}"><div class="card__ic">▸</div><h3>{e(H.area_label(p))}</h3><p>{e((p["meta"] or "").split(".")[0])}</p></a>' for p in items)
    schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), blurb, url, schemas, VOLT_FONTS)
            + _volt_header(t, pages)
            + f'<section class="phero"><div class="wrap"><div class="crumb"><a href="/">Home</a> // {e(h1)}</div><h1>{e(h1)}</h1></div></section>'
            + f'<section class="sec wrap"><div class="sec__h"><span class="mono" style="color:var(--lime)">// {eyebrow}</span></div><div class="grid3">{cards}</div></section>'
            + _volt_footer(t, pages) + "</body></html>")

def volt_trust(t, pages, url, h1, blocks, is_quote=False):
    e = H.esc
    body = "".join(f'<h2>{e(hh)}</h2><p>{e(bb)}</p>' for hh, bb in blocks)
    schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), f"{h1} — {t['brand']}, {t['city']}, {t['st']}.", url, schemas, VOLT_FONTS)
            + _volt_header(t, pages)
            + f'<section class="phero"><div class="wrap"><div class="crumb"><a href="/">Home</a> // {e(h1)}</div><h1>{e(h1)}</h1></div></section>'
            + f'<div class="wrap"><div class="article"><div class="body">{body}</div>{_volt_aside(t)}</div></div>'
            + _volt_footer(t, pages) + "</body></html>")


# ================================================================ NIMBUS
NIM_FONTS = "family=Baloo+2:wght@500;600;700;800&family=Nunito:wght@400;600;700"
NIM_CSS = r"""
:root{--ink:#2c3a49;--soft:#5b6b7b;--blue:#4c8dff;--sky:#e9f3ff;--mint:#e4f7ee;--peach:#ffeede;--lilac:#efe9ff;--r:26px}
*{margin:0;padding:0;box-sizing:border-box}html{scroll-behavior:smooth}
body{font-family:Nunito,sans-serif;color:var(--ink);background:#fbfdff;line-height:1.65}
h1,h2,h3{font-family:"Baloo 2",cursive;line-height:1.15;font-weight:800}
.wrap{max-width:1140px;margin:0 auto;padding:0 26px}a{color:inherit;text-decoration:none}img{display:block;max-width:100%}
.eyebrow{font-family:"Baloo 2";font-weight:700;color:var(--blue);font-size:.95rem}
.btn{display:inline-flex;align-items:center;gap:9px;font-family:"Baloo 2";font-weight:700;border-radius:999px;padding:13px 28px;font-size:1rem;cursor:pointer;border:0;transition:transform .18s,box-shadow .18s}
.btn--blue{background:var(--blue);color:#fff;box-shadow:0 10px 22px rgba(76,141,255,.35)}
.btn--soft{background:#fff;color:var(--ink);box-shadow:0 6px 18px rgba(44,58,73,.10)}
.btn:hover{transform:translateY(-3px) scale(1.02)}
.navwrap{position:sticky;top:16px;z-index:50;padding:0 16px}
.nav{max-width:1000px;margin:0 auto;background:rgba(255,255,255,.88);backdrop-filter:blur(12px);border:1px solid #e7eef7;border-radius:999px;box-shadow:0 12px 30px rgba(44,58,73,.10);display:flex;align-items:center;justify-content:space-between;padding:10px 12px 10px 22px}
.logo{display:flex;align-items:center;gap:10px;font-family:"Baloo 2";font-weight:800;font-size:1.25rem}
.logo__d{width:30px;height:30px;border-radius:50%;background:radial-gradient(circle at 30% 30%,#9cc4ff,var(--blue));box-shadow:0 4px 10px rgba(76,141,255,.4)}
.logo__img{width:38px;height:38px;object-fit:contain;border-radius:10px;flex:0 0 auto}
.nav__links{display:flex;gap:6px;font-family:"Baloo 2";font-weight:600}.nav__links a{padding:8px 14px;border-radius:999px;transition:.2s}.nav__links a:hover{background:var(--sky)}
.nav__links .ni{position:relative}
.nav__links .ni>a::after{content:" ˅";color:var(--blue)}
.nav__links .drop{position:absolute;top:calc(100% + 14px);left:50%;transform:translateX(-50%) translateY(8px);min-width:220px;background:#fff;border:1px solid #e7eef7;border-radius:18px;box-shadow:0 18px 38px rgba(44,58,73,.16);padding:10px;opacity:0;visibility:hidden;transition:.2s;z-index:70}
.nav__links .drop::before{content:"";position:absolute;top:-16px;left:0;right:0;height:16px}
.nav__links .ni:hover .drop{opacity:1;visibility:visible;transform:translateX(-50%) translateY(0)}
.nav__links .drop a{display:block;padding:9px 14px;border-radius:12px;font-size:.92rem;color:var(--ink)}
.nav__links .drop a:hover{background:var(--sky);color:var(--blue)}
.nav__links .drop a:first-child{color:var(--blue);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
.nav .btn{padding:10px 20px;font-size:.95rem}
.navtoggle{display:none;background:var(--sky);border:0;border-radius:50%;width:42px;height:42px;font-size:1.2rem;cursor:pointer}.mmenu{display:none}
.hero{position:relative;text-align:center;padding:76px 26px 92px;overflow:hidden}
.blob{position:absolute;border-radius:50%;filter:blur(8px);opacity:.7;z-index:0}
.b1{width:280px;height:280px;background:var(--peach);top:-40px;left:-60px}.b2{width:340px;height:340px;background:var(--mint);bottom:-80px;right:-70px}.b3{width:200px;height:200px;background:var(--lilac);top:120px;right:12%}
.hero__in{position:relative;z-index:2;max-width:760px;margin:0 auto}
.chip{display:inline-flex;align-items:center;gap:8px;background:#fff;border:1px solid #e7eef7;border-radius:999px;padding:7px 16px;font-weight:700;font-size:.9rem;box-shadow:0 6px 16px rgba(44,58,73,.08)}
.hero h1{font-size:clamp(2.4rem,6vw,4.2rem);margin:22px 0 16px}.hero h1 .hl{color:var(--blue)}
.hero__lead{font-size:1.2rem;color:var(--soft);max-width:52ch;margin:0 auto 30px}
.hero__btns{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}
.trust{display:flex;align-items:center;justify-content:center;gap:14px;margin-top:32px;color:var(--soft);font-weight:700}
.avatars{display:flex}.avatars span{width:38px;height:38px;border-radius:50%;border:3px solid #fff;margin-left:-12px;background:var(--sky)}
.avatars span:nth-child(2){background:var(--mint)}.avatars span:nth-child(3){background:var(--peach)}.avatars span:nth-child(4){background:var(--lilac)}
.sec{padding:76px 0}.sec__head{text-align:center;max-width:600px;margin:0 auto 46px}
.sec__head h2{font-size:clamp(2rem,4.4vw,3rem)}.sec__head p{color:var(--soft);font-size:1.1rem;margin-top:8px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.tile{border-radius:var(--r);padding:30px;transition:.2s;display:block}.tile:hover{transform:translateY(-6px)}
.tile:nth-child(3n+1){background:var(--sky)}.tile:nth-child(3n+2){background:var(--mint)}.tile:nth-child(3n){background:var(--peach)}
.tile__ic{width:56px;height:56px;border-radius:18px;background:#fff;display:grid;place-items:center;font-size:1.6rem;box-shadow:0 8px 16px rgba(44,58,73,.08);margin-bottom:16px}
.tile h3{font-size:1.35rem;margin-bottom:8px}.tile p{color:var(--soft)}.tile .more{display:inline-block;margin-top:14px;font-family:"Baloo 2";font-weight:700;color:var(--blue)}
.steps{background:linear-gradient(180deg,#fff,var(--sky));border-radius:40px;margin:0 26px}.steps .inner{max-width:1000px;margin:0 auto;padding:66px 26px}
.stepgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;position:relative}
.stepgrid::before{content:"";position:absolute;top:30px;left:16%;right:16%;border-top:3px dashed #bcd6f6;z-index:0}
.step{position:relative;z-index:1;text-align:center}
.step__n{width:62px;height:62px;border-radius:50%;background:var(--blue);color:#fff;font-family:"Baloo 2";font-weight:800;font-size:1.5rem;display:grid;place-items:center;margin:0 auto 18px;box-shadow:0 10px 20px rgba(76,141,255,.35);border:5px solid #fff}
.step h3{font-size:1.25rem;margin-bottom:6px}.step p{color:var(--soft)}
.why{display:grid;grid-template-columns:1fr 1fr;gap:50px;align-items:center}
.why__img{border-radius:34px;overflow:hidden;box-shadow:0 24px 50px rgba(44,58,73,.16);position:relative}.why__img img{width:100%;height:100%;object-fit:cover;aspect-ratio:4/3}
.why__badge{position:absolute;left:20px;bottom:20px;background:#fff;border-radius:20px;padding:12px 18px;font-family:"Baloo 2";font-weight:700;box-shadow:0 10px 22px rgba(44,58,73,.16)}
.why h2{font-size:clamp(1.9rem,4vw,2.8rem);margin-bottom:16px}
.checks{list-style:none;display:grid;gap:14px;margin-top:20px}.checks li{display:flex;gap:12px;align-items:center;font-weight:700}
.checks .c{width:30px;height:30px;border-radius:50%;background:var(--mint);color:#1f9d63;display:grid;place-items:center;flex:0 0 auto}
.bubbles{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.bubble{background:#fff;border-radius:24px;padding:26px;box-shadow:0 12px 30px rgba(44,58,73,.08);position:relative}
.bubble::after{content:"";position:absolute;left:34px;bottom:-14px;border:14px solid transparent;border-top-color:#fff;border-bottom:0}
.bubble .who{display:flex;align-items:center;gap:12px;margin-top:30px}.bubble .av{width:44px;height:44px;border-radius:50%;background:var(--peach)}
.bubble:nth-child(2) .av{background:var(--lilac)}.bubble:nth-child(3) .av{background:var(--sky)}
.bubble .who b{font-family:"Baloo 2"}.bubble .who span{display:block;color:var(--soft);font-size:.86rem}
.stars{color:#ffb020;letter-spacing:2px;margin-bottom:10px}
.plans{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.plan{background:#fff;border:2px solid #eef3f9;border-radius:28px;padding:30px;text-align:center;transition:.2s}.plan:hover{transform:translateY(-6px);border-color:var(--blue)}
.plan .ptag{display:inline-block;background:var(--sky);color:var(--blue);border-radius:999px;padding:5px 14px;font-family:"Baloo 2";font-weight:700;font-size:.85rem}
.plan .price{font-family:"Baloo 2";font-weight:800;font-size:2.6rem;margin:14px 0 4px}.plan .price small{font-size:.9rem;color:var(--soft)}
.plan p{color:var(--soft);margin-bottom:20px}.plan .btn{width:100%;justify-content:center}
.faqs{max-width:760px;margin:0 auto;display:grid;gap:14px}
.fq{background:#fff;border-radius:20px;box-shadow:0 8px 20px rgba(44,58,73,.06);overflow:hidden}
.fq summary{list-style:none;cursor:pointer;padding:20px 24px;font-family:"Baloo 2";font-weight:700;font-size:1.08rem;display:flex;justify-content:space-between;align-items:center}
.fq summary::-webkit-details-marker{display:none}.fq summary::after{content:"˅";color:var(--blue)}.fq[open] summary::after{content:"˄"}
.fq p{padding:0 24px 22px;color:var(--soft)}
.ctawrap{padding:0 26px 90px}
.cta{max-width:1000px;margin:0 auto;background:linear-gradient(135deg,#4c8dff,#7db3ff);border-radius:40px;text-align:center;color:#fff;padding:66px 30px;box-shadow:0 30px 60px rgba(76,141,255,.35)}
.cta h2{font-size:clamp(2rem,5vw,3.2rem);margin-bottom:10px}.cta p{opacity:.92;font-size:1.15rem;margin-bottom:26px}.cta .btn{background:#fff;color:var(--blue)}
/* inner */
.phero{text-align:center;padding:70px 26px 30px;position:relative}
.crumb{font-family:"Baloo 2";font-weight:600;color:var(--soft);margin-bottom:12px}.crumb a{color:var(--blue)}
.phero h1{font-size:clamp(2rem,5vw,3.2rem);max-width:20ch;margin:0 auto}
.article{max-width:820px;margin:0 auto;padding:30px 0 20px}
.article .body{background:#fff;border-radius:28px;box-shadow:0 12px 30px rgba(44,58,73,.07);padding:38px}
.article h2{font-size:1.6rem;margin:26px 0 10px}.article h3{font-size:1.25rem;margin:22px 0 8px}
.article p{margin:0 0 14px;color:#41525f}.article ul{margin:0 0 14px 20px;color:#41525f}.article img{border-radius:22px;margin:20px 0}
.article details{background:var(--sky);border-radius:16px;padding:14px 18px;margin:10px 0}.article summary{font-family:"Baloo 2";font-weight:700;cursor:pointer}
.aside{max-width:820px;margin:0 auto 10px;background:linear-gradient(135deg,var(--mint),var(--sky));border-radius:28px;padding:26px;text-align:center}
.aside h3{margin-bottom:6px}.aside p{color:var(--soft);margin-bottom:16px}
footer{background:#eef4fb;border-radius:44px 44px 0 0;padding:60px 0 30px;margin-top:20px}
.f-top{display:grid;grid-template-columns:1.5fr 1fr 1fr 1.2fr;gap:32px;padding-bottom:40px;border-bottom:2px solid #dde8f4}
.f-top h4{font-family:"Baloo 2";font-weight:700;margin-bottom:14px;font-size:1.05rem}
.f-top a:not(.btn),.f-top p{display:block;color:var(--soft);padding:5px 0;font-weight:600}.f-top a:not(.btn):hover{color:var(--blue)}
.f-card{background:#fff;border-radius:24px;padding:26px;box-shadow:0 12px 26px rgba(44,58,73,.08)}
.f-card .btn{display:flex;width:100%;box-sizing:border-box;justify-content:center;text-align:center;padding:14px 18px;margin-top:16px}
.f-social{display:flex;gap:10px;margin-top:16px}.f-social a{width:40px;height:40px;border-radius:50%;background:var(--sky);display:grid;place-items:center;font-family:"Baloo 2";font-weight:700;color:var(--blue)}.f-social a:hover{background:var(--blue);color:#fff}
.f-bot{text-align:center;padding-top:26px;color:var(--soft);font-weight:600}
@media(max-width:900px){.nav__links{display:none}.navtoggle{display:grid;place-items:center}
 .mmenu{flex-direction:column;gap:4px;max-width:1000px;margin:10px auto 0;background:#fff;border-radius:24px;padding:14px;box-shadow:0 12px 30px rgba(44,58,73,.12)}.mmenu.open{display:flex}
 .mmenu a{padding:12px 16px;border-radius:14px;font-family:"Baloo 2";font-weight:700}
 .tiles,.stepgrid,.why,.bubbles,.plans,.f-top{grid-template-columns:1fr}.stepgrid::before{display:none}.bubble::after{display:none}}
"""

def _nim_logo(t):
    if t.get("has_logo"):
        return f'<img class="logo__img" src="/assets/logo-emblem.png" alt="{H.esc(t["brand"])} logo">'
    return '<span class="logo__d"></span>'

def _nim_call(t):
    """(href, label) for a call button that works with or without a phone on file."""
    if t.get("phone"):
        return f'tel:{t["tel"]}', f'Call {H.esc(t["phone"])}'
    return "/request-a-quote/", "Call now"

def _nim_drop(pages, cat, all_url, all_label, trigger):
    e = H.esc
    if not _cat(pages, cat):
        return f'<a href="{all_url}">{trigger}</a>'
    links = "".join(f'<a href="{u}">{e(l)}</a>' for u, l in _menu(pages, cat, all_url, all_label))
    return f'<div class="ni"><a href="{all_url}">{trigger}</a><div class="drop">{links}</div></div>'

def _nim_header(t, pages):
    e = H.esc
    links = (_nim_drop(pages, "service", "/services/", "All Services", "Services")
             + _nim_drop(pages, "area", "/service-areas/", "All Areas", "Areas")
             + _nim_drop(pages, "guide", "/guides/", "All Guides", "Guides")
             + '<a href="/about/">About</a>')
    return (f'<div class="navwrap"><nav class="nav"><a href="/" class="logo">{_nim_logo(t)}{e(t["brand"].split(" ")[0])}</a>'
            f'<div class="nav__links">{links}</div>'
            f'<a class="btn btn--blue" href="/request-a-quote/">Book now</a>'
            f'<button class="navtoggle" onclick="document.getElementById(\'mm\').classList.toggle(\'open\')">☰</button></nav>'
            f'<div class="mmenu" id="mm"><a href="/services/">Services</a><a href="/service-areas/">Areas</a><a href="/guides/">Guides</a><a href="/about/">About</a><a href="/request-a-quote/">Book now</a></div></div>')

def _nim_footer(t, pages):
    e = H.esc
    svc = _cat(pages, "service")[:4]
    slinks = "".join(f'<a href="{p["url"]}">{e(H.area_label(p))}</a>' for p in svc) or '<a href="/services/">Services</a>'
    line = e(t["phone"]) if t.get("phone") else "Friendly help, on your schedule."
    return (f'<footer><div class="wrap"><div class="f-top">'
            f'<div><div class="logo" style="margin-bottom:12px">{_nim_logo(t)}{e(t["brand"].split(" ")[0])}</div>'
            f'<p style="max-width:30ch">Friendly garage door care for {e(t["city"])} homes. The neighborly first call.</p><div class="f-social"><a>f</a><a>◎</a><a>▷</a></div></div>'
            f'<div><h4>Help with</h4>{slinks}<a href="/services/">All services</a></div>'
            f'<div><h4>Company</h4><a href="/about/">About</a><a href="/guides/">Guides</a><a href="/service-areas/">Areas</a><a href="/request-a-quote/">Book now</a></div>'
            f'<div class="f-card"><h4>Say hi 👋</h4><p style="color:var(--soft);font-weight:600;margin-bottom:4px">{line}</p><a class="btn btn--blue" href="/request-a-quote/">Book a visit</a></div></div>'
            f'<div class="f-bot">© 2024 {e(t["brand"])} · Made with 🧡 in {e(t["city"])}</div></div></footer>')

def nim_home(t, pages):
    e = H.esc
    h1, lead, faqs, svc, areas, guides = _home_data(t, pages)
    tiles = _svc_tiles(pages)
    tt = "".join(f'<a class="tile" href="{u}"><div class="tile__ic">🔧</div><h3>{title}</h3><p>{blurb}</p><span class="more">Learn more →</span></a>' for ic, title, blurb, u in tiles)
    faq = "".join(f'<details class="fq"{" open" if i==0 else ""}><summary>{e(q)}</summary><p>{e(a)}</p></details>' for i, (q, a) in enumerate(faqs))
    chref, clabel = _nim_call(t)
    schemas = [H.org_schema(t), H.faq_schema(faqs)]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), lead, "/", schemas, NIM_FONTS, og=H.HERO_IMG)
            + _nim_header(t, pages)
            + f'<section class="hero"><span class="blob b1"></span><span class="blob b2"></span><span class="blob b3"></span><div class="hero__in">'
              f'<span class="chip">👋 {e(t["city"])}\'s friendliest garage door team</span>'
              f'<h1>A stuck door is stressful.<br>We make it <span class="hl">easy.</span></h1><p class="hero__lead">{e(lead)}</p>'
              f'<div class="hero__btns"><a class="btn btn--blue" href="/request-a-quote/">📞 Book a friendly visit</a><a class="btn btn--soft" href="/services/">See services</a></div>'
              f'<div class="trust"><div class="avatars"><span></span><span></span><span></span><span></span></div>Loved by homeowners across {e(t["city"])}</div></div></section>'
            + f'<section class="sec"><div class="wrap"><div class="sec__head"><span class="eyebrow">What we help with</span><h2>Care for every kind of door</h2><p>Whatever\'s going on, there\'s a gentle, get-it-done option here.</p></div><div class="tiles">{tt}</div></div></section>'
            + f'<section class="sec" style="padding-bottom:40px"><div class="steps"><div class="inner"><div class="sec__head"><span class="eyebrow">Nice and simple</span><h2>Help in three easy steps</h2></div>'
              f'<div class="stepgrid"><div class="step"><div class="step__n">1</div><h3>Say hello</h3><p>Tell us what\'s up by phone or text. A real {e(t["city"])} human answers.</p></div>'
              f'<div class="step"><div class="step__n">2</div><h3>We pop by</h3><p>On time, tidy, and up-front. You\'ll see the price before we start.</p></div>'
              f'<div class="step"><div class="step__n">3</div><h3>All better</h3><p>Fixed, tested, and tidied — with tips to keep it happy.</p></div></div></div></div></section>'
            + f'<section class="sec"><div class="wrap why"><div class="why__img"><img src="{PHOTOS}gd-3.jpg" alt="A friendly technician"><div class="why__badge">🧡 Neighborly by nature</div></div>'
              f'<div><span class="eyebrow">Why folks pick us</span><h2>Fewer surprises, more smiles</h2><p style="color:var(--soft)">We treat your home like our own and your time like it matters.</p>'
              f'<ul class="checks"><li><span class="c">✓</span>Upfront prices, always explained</li><li><span class="c">✓</span>Friendly, vetted technicians</li><li><span class="c">✓</span>Tidy work &amp; clean-up after</li><li><span class="c">✓</span>No-pressure, honest advice</li></ul></div></div></section>'
            + f'<section class="sec"><div class="wrap"><div class="sec__head"><span class="eyebrow">Kind words</span><h2>Neighbors say the sweetest things</h2></div><div class="bubbles">'
              f'<div class="bubble"><div class="stars">★★★★★</div><p>"So refreshing. Explained everything, no jargon, no pressure. My door\'s never been quieter!"</p><div class="who"><span class="av"></span><div><b>Priya S.</b><span>{e(t["city"])}</span></div></div></div>'
              f'<div class="bubble"><div class="stars">★★★★★</div><p>"Texted at breakfast, fixed by lunch. Genuinely lovely people to have in your driveway."</p><div class="who"><span class="av"></span><div><b>Marcus L.</b><span>{e(t["city"])}</span></div></div></div>'
              f'<div class="bubble"><div class="stars">★★★★★</div><p>"They could\'ve sold me a new door and didn\'t. Just an honest little repair. Customers for life."</p><div class="who"><span class="av"></span><div><b>Dana &amp; Rob</b><span>{e(t["city"])}</span></div></div></div></div></div></section>'
            + f'<section class="sec" style="padding-bottom:20px"><div class="wrap"><div class="sec__head"><span class="eyebrow">Good to know</span><h2>Little questions, answered</h2></div><div class="faqs">{faq}</div></div></section>'
            + f'<div class="ctawrap"><div class="cta"><h2>Let\'s get that door smiling again 🙂</h2><p>Book a warm, no-pressure visit with your {e(t["city"])} neighbors.</p><a class="btn" href="{chref}">📞 {clabel}</a></div></div>'
            + _nim_footer(t, pages) + "</body></html>")

def _nim_aside(t):
    e = H.esc
    href, label = _nim_call(t)
    return (f'<div class="aside"><h3>Need a hand? 👋</h3><p>Friendly, no-pressure garage door help in {e(t["city"])}.</p>'
            f'<a class="btn btn--blue" href="{href}">📞 {label}</a></div>')

def nim_inner(t, pages, p):
    e = H.esc
    label, parent = _LABELS.get(p["cat"], ("", "/"))
    h1 = p["h1"] or H.area_label(p)
    img = H.INNER_IMGS[H._stable_idx(p["slug"] or p["url"], len(H.INNER_IMGS))]
    body = _inner_parts(t, p)
    schemas = _inner_schemas(t, p, h1, label, parent)
    return (_head(t, H.seo_title(p["title"] or f"{h1} | {t['brand']}"), p["meta"] or "", p["url"], schemas, NIM_FONTS, og=img)
            + _nim_header(t, pages)
            + f'<section class="phero"><div class="crumb"><a href="/">Home</a> · <a href="{parent}">{label}</a> · {e(h1)}</div><h1>{e(h1)}</h1></section>'
            + f'<div class="article"><div class="body"><img src="{PHOTOS}{img}" alt="{e(h1)}" loading="lazy">{body}</div></div>'
            + f'<div class="wrap" style="padding-bottom:40px">{_nim_aside(t)}</div>'
            + _nim_footer(t, pages) + "</body></html>")

def nim_index(t, pages, cat, url, h1, eyebrow, blurb):
    e = H.esc
    items = _cat(pages, cat)
    tt = "".join(f'<a class="tile" href="{p["url"]}"><div class="tile__ic">🚪</div><h3>{e(H.area_label(p))}</h3><p>{e((p["meta"] or "").split(".")[0])}</p><span class="more">Open →</span></a>' for p in items)
    schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), blurb, url, schemas, NIM_FONTS)
            + _nim_header(t, pages)
            + f'<section class="phero"><div class="crumb"><a href="/">Home</a> · {e(h1)}</div><h1>{e(h1)}</h1></section>'
            + f'<section class="sec" style="padding-top:30px"><div class="wrap"><div class="sec__head"><span class="eyebrow">{eyebrow}</span><p>{e(blurb)}</p></div><div class="tiles">{tt}</div></div></section>'
            + _nim_footer(t, pages) + "</body></html>")

def nim_trust(t, pages, url, h1, blocks, is_quote=False):
    e = H.esc
    body = "".join(f'<h2>{e(hh)}</h2><p>{e(bb)}</p>' for hh, bb in blocks)
    schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), f"{h1} — {t['brand']}, {t['city']}, {t['st']}.", url, schemas, NIM_FONTS)
            + _nim_header(t, pages)
            + f'<section class="phero"><div class="crumb"><a href="/">Home</a> · {e(h1)}</div><h1>{e(h1)}</h1></section>'
            + f'<div class="article"><div class="body">{body}</div></div>'
            + f'<div class="wrap" style="padding-bottom:40px">{_nim_aside(t)}</div>'
            + _nim_footer(t, pages) + "</body></html>")


# ---------------------------------------------------------------- registry
# note: inner() takes (t, p, pages) in build.py's GARAGE lambda, but our functions use
# (t, pages, p); adapt with a wrapper so the interface matches build.py exactly.
def _mk(css_str, home, inner, index, trust):
    return {"css": (lambda cs: (lambda t: cs))(css_str),
            "home": home,
            "inner": (lambda fn: (lambda t, p, pages: fn(t, pages, p)))(inner),
            "index": index, "trust": trust}

REGISTRY = {
    "ironclad": _mk(IRON_CSS, iron_home, iron_inner, iron_index, iron_trust),
    "volt": _mk(VOLT_CSS, volt_home, volt_inner, volt_index, volt_trust),
    "nimbus": _mk(NIM_CSS, nim_home, nim_inner, nim_index, nim_trust),
}
