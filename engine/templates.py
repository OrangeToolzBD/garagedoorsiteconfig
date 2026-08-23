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
from datetime import date

H = None  # injected by build.get_renderer()

PHOTOS = "/assets/photos/"


def _year():
    """Current year. These footers used to hard-code 2024, which quietly went stale
    on every alt-template site while the default garage design stayed correct."""
    return date.today().year


def _hero(t):
    """City-matched hero chosen by build.select_photos(), or the generic pool shot."""
    return t.get("hero_img") or H.HERO_IMG


def _card(t, i, fallback):
    """One of the six per-service photos select_photos() picked for this city.
    The alt templates used to hard-code gd-*.jpg here, so ironclad/nimbus sites shipped
    generic stock while every garage-design site got the curated set."""
    imgs = t.get("card_imgs") or []
    return imgs[i % len(imgs)] if imgs else fallback


def _tel(t, label=None, cls=""):
    """Dial link, or "" when this site has no number configured. These designs used to
    emit `<a href="tel:+1"></a>` -- an empty link that dials nothing -- on the ~999
    domains with a blank phone field."""
    if not H.has_phone(t):
        return ""
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="tel:{t["tel"]}">{label if label else H.esc(t["phone"])}</a>'


def _quote(label, cls=""):
    """Fallback CTA for the phone-less case: the quote form is the working path."""
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="/request-a-quote/">{label}</a>'


def _quote_block(t, is_quote):
    """The lead-capture form on /request-a-quote/. Shares build.quote_form() and
    QFORM_CSS with the default design, so all four templates capture leads the same
    way rather than only the garage one having a form at all."""
    if not is_quote:
        return ""
    form = H.quote_form(t)
    # padding-block only -- a `padding` shorthand here would wipe out each design's
    # own .wrap gutter and push the form flush against the viewport edges.
    # max-width: these designs have no side card next to the form, so without a cap it
    # stretches the full 1180px container and the inputs read as a wall.
    return (f'<div class="wrap" style="padding-block:36px 8px">'
            f'<div style="max-width:860px">{form}</div></div>') if form else ""


def _inner(t, p):
    """The photo select_photos() assigned to this specific inner page."""
    imgs = t.get("inner_imgs") or {}
    return imgs.get(p["url"]) or H.INNER_IMGS[H._stable_idx(p["slug"] or p["url"], len(H.INNER_IMGS))]

# ---------------------------------------------------------------- shared bits
def _head(t, title, desc, url, schemas, fonts, bodyclass="", og=None):
    # the design's own `fonts` argument is superseded by the site's pairing; keeping the
    # parameter means no design signature had to change
    fonts = H.type_fonts(t)
    bodyclass = (bodyclass + " " + H.variant_classes(t)).strip()
    e = H.esc
    graph = {"@context": "https://schema.org", "@graph": schemas}
    ogm = preload = ""
    if og:
        u = f"https://{t['domain']}{PHOTOS}{og}"
        ogm = f'<meta property="og:image" content="{u}"><meta name="twitter:image" content="{u}">'
        # the hero is the LCP element -- start it before the stylesheet resolves
        preload = f'<link rel="preload" as="image" href="{PHOTOS}{og}" fetchpriority="high">'
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
            f'<link rel="stylesheet" href="/assets/site.css">{preload}'
            f'<script type="application/ld+json">{json.dumps(graph)}</script>'
            f'</head><body class="{bodyclass}"><a class="skip" href="#main">Skip to content</a>')

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


# ================================================================ SHARED CHROME
# One header/footer/nav implementation for every alt design.
#
# These designs began life as the single-page mockups in variants/, where the nav was
# decoration: menus were `#anchor` links, dropdowns opened on :hover only, and the
# mobile panel listed the section anchors. Ported to real multi-page sites, each design
# re-typed its own version of that markup and inherited the same faults -- dropdowns
# that no touch device can open, mobile menus that reach the three index pages but none
# of the ~30 pages under them, burgers with no accessible name or state, and footer
# "social" icons that are <a> elements with no href.
#
# So the chrome is built once, here, and every design themes it. The class vocabulary
# below is the contract: this module owns layout, positioning and behaviour; a design's
# stylesheet owns colour, type, borders and spacing. A new design cannot reintroduce
# the mockup-grade nav without deliberately overriding structural rules.
#
# Behaviour guaranteed for every design:
#   - every content page is reachable from the nav on desktop AND on mobile
#   - dropdowns open on hover (pointer) and on click/tap (touch + keyboard)
#   - correct aria-expanded / aria-controls / aria-haspopup throughout
#   - Escape closes, focus returns to the trigger, outside-click dismisses
#   - no anchor is emitted without an href

CHROME_MOBILE_BP = 1080          # must match the @media breakpoint in CHROME_CSS

def _nav_groups(pages):
    """The dropdown groups this site actually has content for, in nav order."""
    out = []
    for cat in ("service", "area", "guide"):
        items = _cat(pages, cat)
        if not items:
            continue
        label, all_url = _LABELS[cat]
        links = [(all_url, f"All {label}")] + [(p["url"], H.area_label(p)) for p in items]
        out.append((label, all_url, links))
    return out


def _chrome_brand(t, h=44, text=True):
    """Brand link. A horizontal lockup already carries the business name so it stands
    alone; a square badge keeps a text label beside it; a site with no logo file falls
    back to the generated SVG mark.

    `text=False` drops the label and lets the logo carry the brand on its own -- used
    in the footer, where there is room to show the mark at a size you can actually
    read. The accessible name then comes from the image's alt text instead."""
    e = H.esc
    if H.is_wide_lockup(t) or (t.get("has_logo") and not text):
        w, hh = H.logo_box(t, h)
        return (f'<a class="tc-brand tc-brand--lockup" href="/">'
                f'<img src="/assets/logo-emblem.png" alt="{e(t["brand"])}" width="{w}" height="{hh}" '
                f'loading="eager" decoding="async"></a>')
    if t.get("has_logo"):
        w, hh = H.logo_box(t, h)
        mark = (f'<img src="/assets/logo-emblem.png" alt="" width="{w}" height="{hh}" '
                f'loading="eager" decoding="async">')
    else:
        mark = H.gdoor_svg(h)
    return (f'<a class="tc-brand" href="/"><span class="tc-brand__mark">{mark}</span>'
            f'<span class="tc-brand__txt">{e(t["brand"])}</span></a>')


def _chrome_header(t, pages, cta="Request a Quote"):
    """Header + desktop nav + mobile panel. The mobile panel carries the *same* groups
    as the desktop dropdowns -- collapsed into accordions -- rather than a shortcut list
    of index pages, which is what left ~30 pages per site unreachable on a phone."""
    e = H.esc
    groups = _nav_groups(pages)

    desktop = ""
    for i, (label, all_url, links) in enumerate(groups):
        mid = f"tcd-{i}"
        opts = "".join(f'<a href="{u}">{e(l)}</a>' for u, l in links)
        desktop += (f'<div class="tc-item">'
                    f'<button class="tc-trigger" type="button" aria-expanded="false" '
                    f'aria-controls="{mid}" aria-haspopup="true">{e(label)}<span class="tc-caret" aria-hidden="true"></span></button>'
                    f'<div class="tc-drop" id="{mid}">{opts}</div></div>')
    desktop += '<a class="tc-link" href="/about/">About</a><a class="tc-link" href="/contact/">Contact</a>'

    mobile = ""
    for i, (label, all_url, links) in enumerate(groups):
        mid = f"tcm-{i}"
        opts = "".join(f'<a href="{u}">{e(l)}</a>' for u, l in links)
        mobile += (f'<div class="tc-macc">'
                   f'<button class="tc-msum" type="button" aria-expanded="false" aria-controls="{mid}">'
                   f'{e(label)}<span class="tc-caret" aria-hidden="true"></span></button>'
                   f'<div class="tc-mlinks" id="{mid}">{opts}</div></div>')
    mobile += ('<a class="tc-mlink" href="/about/">About</a>'
               '<a class="tc-mlink" href="/contact/">Contact</a>'
               f'<a class="tc-mcta" href="/request-a-quote/">{e(cta)}</a>')
    tel = _tel(t, cls="tc-mtel")
    if tel:
        mobile += tel

    top = _tel(t, cls="tc-tel")
    # announcement bar sits above the sticky header, so it scrolls away with the page
    return (hb_announce(t)
            + f'<header class="tc-bar"><div class="tc-inner">'
            f'{_chrome_brand(t)}'
            f'<nav class="tc-nav" aria-label="Main">{desktop}</nav>'
            f'<div class="tc-acts">{top}<a class="tc-cta" href="/request-a-quote/">{e(cta)}</a></div>'
            f'<button class="tc-burger" type="button" aria-label="Menu" aria-expanded="false" '
            f'aria-controls="tc-menu"><span></span><span></span><span></span></button>'
            f'</div><nav class="tc-mobile" id="tc-menu" aria-label="Mobile">{mobile}</nav></header><main id="main">')


def _chrome_footer(t, pages, blurb=None, tagline=None):
    """Shared footer. Every link here resolves to a real page -- the alt designs used to
    decorate this area with <a>IG</a>/<a>f</a> placeholders that are unfocusable, have
    no destination, and read as broken links to a crawler."""
    e = H.esc
    svc = _cat(pages, "service")[:5]
    areas = _cat(pages, "area")[:8]
    guides = _cat(pages, "guide")[:4]
    def col(title, links, all_link=None):
        body = "".join(f'<a href="{u}">{e(l)}</a>' for u, l in links)
        if all_link:
            body += f'<a href="{all_link[0]}">{e(all_link[1])}</a>'
        return f'<div class="tc-fcol"><h3>{e(title)}</h3>{body}</div>' if body else ""
    cols = col("Services", [(p["url"], H.area_label(p)) for p in svc], ("/services/", "All services"))
    cols += col("Service Areas", [(p["url"], H.area_label(p)) for p in areas], ("/service-areas/", "All areas"))
    cols += col("Guides", [(p["url"], H.area_label(p)) for p in guides], ("/guides/", "All guides"))
    cols += col("Company", [("/about/", "About"), ("/contact/", "Contact"),
                            ("/request-a-quote/", "Request a quote")])
    addr = f'{e(t["city"])}, {e(t["st"])}' + (f' {e(t["zip"])}' if t.get("zip") else "")
    tel = _tel(t, cls="tc-ftel")
    blurb = blurb or (f'Garage door repair, spring and opener service and new-door installation '
                      f'across {e(t["city"])} and the surrounding metro.')
    return (f'</main><footer class="tc-foot"><div class="tc-fwrap">'
            f'<div class="tc-fcols"><div class="tc-fbrand">{_chrome_brand(t, 104, text=False)}'
            f'<p>{blurb}</p><address>{addr}{"<br>" + tel if tel else ""}</address></div>{cols}</div>'
            f'<div class="tc-flegal"><span>&copy; {_year()} {e(t["brand"])}. All rights reserved.</span>'
            f'<span>{e(tagline or t["tagline"])}</span></div></div></footer>' + CHROME_JS)


CHROME_JS = """<script>(function(){
 var BP=window.matchMedia('(max-width:__BP__px)');
 function exp(el,v){if(el)el.setAttribute('aria-expanded',v?'true':'false')}
 // condensing header: mark the bar once the page has scrolled (no CSS selector for it)
 var bar=document.querySelector('.tc-bar');
 if(bar&&document.body.className.indexOf('v-nav-condense')>-1){
   var onScroll=function(){bar.classList.toggle('is-stuck',(window.pageYOffset||0)>60)};
   window.addEventListener('scroll',onScroll,{passive:true});onScroll();
 }
 var burger=document.querySelector('.tc-burger'),panel=document.getElementById('tc-menu');
 if(burger&&panel)burger.addEventListener('click',function(){exp(burger,panel.classList.toggle('open'))});
 // desktop dropdowns: hover for pointers, click for touch and keyboard. The mockups
 // these designs came from were hover-only, so no touch device could open a menu.
 document.querySelectorAll('.tc-item').forEach(function(item){
   var btn=item.querySelector('.tc-trigger');
   item.addEventListener('mouseenter',function(){if(!BP.matches)exp(btn,true)});
   item.addEventListener('mouseleave',function(){if(!BP.matches){exp(btn,false);item.classList.remove('open')}});
   if(btn)btn.addEventListener('click',function(e){e.preventDefault();exp(btn,item.classList.toggle('open'))});
 });
 // mobile accordions
 document.querySelectorAll('.tc-msum').forEach(function(btn){
   btn.addEventListener('click',function(){exp(btn,btn.parentNode.classList.toggle('open'))});
 });
 function closeAll(){
   document.querySelectorAll('.tc-item.open,.tc-macc.open').forEach(function(i){
     i.classList.remove('open');exp(i.querySelector('.tc-trigger,.tc-msum'),false);
   });
   if(panel&&panel.classList.contains('open')){panel.classList.remove('open');exp(burger,false)}
 }
 document.addEventListener('keydown',function(e){
   if(e.key!=='Escape')return;
   var open=document.querySelector('.tc-item.open,.tc-macc.open')||(panel&&panel.classList.contains('open')?panel:null);
   if(!open)return;
   closeAll();if(burger&&BP.matches)burger.focus();
 });
 document.addEventListener('click',function(e){
   if(e.target.closest('.tc-bar'))return;
   closeAll();
 });
})();</script>""".replace("__BP__", str(CHROME_MOBILE_BP))


# Structure and behaviour only -- each design's stylesheet supplies colour, type,
# borders, radii and spacing on top of these same class names.
CHROME_CSS = """
.tc-bar{position:sticky;top:0;z-index:70}
.tc-inner{display:flex;align-items:center;gap:18px;max-width:1200px;margin:0 auto;padding:12px 24px}
.tc-brand{display:flex;align-items:center;gap:11px;text-decoration:none;flex:0 0 auto}
.tc-brand--lockup img,.tc-brand__mark img,.tc-brand__mark svg{display:block;height:44px;width:auto;max-width:230px;object-fit:contain}
/* Footer: show the mark large enough to actually read, and let it carry the brand on
   its own -- no name repeated beside it. */
.tc-foot .tc-brand{margin-bottom:16px}
.tc-foot .tc-brand img{height:104px;max-width:300px}
/* The logos are dark artwork on transparency, so on a dark bar or footer they vanish
   into it. A light plate is what makes them legible; designs with a light background
   opt out by resetting .tc-plate. */
.tc-plate{background:#fff;border-radius:14px;padding:10px 16px;display:inline-flex;
  align-items:center;box-shadow:0 2px 10px rgba(0,0,0,.16)}
@media(max-width:620px){.tc-foot .tc-brand img{height:78px;max-width:230px}}
.tc-brand__txt{white-space:nowrap;line-height:1.1}
.tc-nav{display:flex;align-items:center;gap:4px;margin-left:auto}
.tc-item{position:relative}
.tc-trigger,.tc-msum{display:inline-flex;align-items:center;gap:7px;background:none;border:0;cursor:pointer;
  font:inherit;color:inherit;padding:10px 14px}
.tc-caret{width:7px;height:7px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;
  transform:rotate(45deg) translate(-2px,-2px);transition:transform .2s;flex:0 0 auto}
.tc-item.open .tc-caret,.tc-macc.open .tc-caret{transform:rotate(-135deg) translate(-3px,-3px)}
.tc-link{display:inline-block;padding:10px 14px;text-decoration:none;color:inherit}
.tc-drop{position:absolute;top:100%;left:0;min-width:250px;max-height:70vh;overflow-y:auto;
  opacity:0;visibility:hidden;transform:translateY(6px);transition:opacity .16s,transform .16s,visibility .16s;
  display:flex;flex-direction:column;padding:8px;z-index:80}
.tc-item:hover .tc-drop,.tc-item.open .tc-drop,.tc-item:focus-within .tc-drop{opacity:1;visibility:visible;transform:none}
.tc-drop a{padding:9px 12px;text-decoration:none;color:inherit;white-space:nowrap}
.tc-acts{display:flex;align-items:center;gap:14px;flex:0 0 auto}
.tc-cta{display:inline-block;padding:11px 20px;text-decoration:none;white-space:nowrap}
.tc-burger{display:none;flex-direction:column;justify-content:center;gap:5px;width:46px;height:42px;
  background:none;border:0;cursor:pointer;padding:0 10px;margin-left:auto}
.tc-burger span{display:block;height:2px;width:100%;background:currentColor;transition:transform .2s,opacity .2s}
.tc-burger[aria-expanded="true"] span:nth-child(1){transform:translateY(7px) rotate(45deg)}
.tc-burger[aria-expanded="true"] span:nth-child(2){opacity:0}
.tc-burger[aria-expanded="true"] span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
.tc-mobile{display:none;flex-direction:column;max-height:calc(100dvh - 68px);overflow-y:auto;
  overscroll-behavior:contain;padding:10px 16px 22px}
.tc-mobile.open{display:flex}
.tc-macc{display:flex;flex-direction:column}
.tc-msum{justify-content:space-between;width:100%;text-align:left;padding:14px 4px}
.tc-mlinks{display:none;flex-direction:column;padding:0 0 8px 14px}
.tc-macc.open .tc-mlinks{display:flex}
.tc-mlinks a,.tc-mlink{padding:11px 4px;text-decoration:none;color:inherit;display:block}
.tc-mcta{display:block;text-align:center;padding:13px;margin-top:12px;text-decoration:none}
.tc-mtel{display:block;text-align:center;padding:12px;text-decoration:none}
/* footer */
.tc-fwrap{max-width:1200px;margin:0 auto;padding:56px 24px 28px}
.tc-fcols{display:grid;grid-template-columns:1.6fr repeat(4,1fr);gap:30px}
.tc-fbrand p{max-width:34ch}
.tc-fbrand address{font-style:normal;margin-top:10px}
.tc-fcol{display:flex;flex-direction:column;gap:8px;min-width:0}
.tc-fcol h3{margin:0 0 4px}
.tc-fcol a{text-decoration:none;color:inherit}
.tc-flegal{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;margin-top:34px;padding-top:18px}
@media(max-width:__BP__px){
  .tc-nav,.tc-acts{display:none}
  .tc-burger{display:flex}
  .tc-drop{position:static;opacity:1;visibility:visible;transform:none}
  .tc-fcols{grid-template-columns:1fr 1fr}
}
@media(max-width:620px){
  .tc-inner{padding:10px 18px;gap:12px}
  .tc-fwrap{padding:40px 18px 24px}
  .tc-fcols{grid-template-columns:1fr}
  .tc-flegal{flex-direction:column;gap:6px}
}
""".replace("__BP__", str(CHROME_MOBILE_BP))


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
/* --- shared chrome, ironclad dress: paper, hairline rules, brass, no shadows --- */
.tc-bar{background:rgba(251,249,244,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--rule)}
.tc-inner{max-width:1180px;padding:16px 32px;gap:24px}
.tc-brand__txt{font-family:"Playfair Display",Georgia,serif;font-size:1.16rem;font-weight:700;letter-spacing:-.01em}
.tc-trigger,.tc-link,.tc-msum{font-size:.82rem;letter-spacing:.06em}
.tc-trigger:hover,.tc-link:hover{color:var(--brass)}
.tc-caret{border-color:var(--brass)}
.tc-drop{background:var(--paper);border:1px solid var(--rule);box-shadow:0 22px 44px rgba(20,18,15,.14);padding:8px 0;left:-18px}
.tc-drop a{padding:9px 22px;font-size:.85rem}
.tc-drop a:hover{background:var(--cream);color:var(--brass)}
.tc-drop a:first-child{color:var(--brass);font-weight:600;letter-spacing:.18em;text-transform:uppercase;
  font-size:.68rem;border-bottom:1px solid var(--rule);margin-bottom:6px;padding-bottom:11px}
.tc-tel{font-family:"Playfair Display",Georgia,serif;font-size:1.05rem;color:var(--brass)}
.tc-cta{border:1px solid var(--ink);padding:12px 24px;font-size:.7rem;letter-spacing:.2em;
  text-transform:uppercase;font-weight:600;transition:.3s}
.tc-cta:hover{background:var(--ink);color:var(--cream)}
.tc-mobile{background:var(--paper);border-top:1px solid var(--rule)}
.tc-msum,.tc-mlink{border-bottom:1px solid var(--rule);letter-spacing:.08em}
.tc-mlinks a{font-size:.9rem;color:var(--muted)}
.tc-mcta{border:1px solid var(--brass);color:var(--brass);letter-spacing:.2em;text-transform:uppercase;font-size:.72rem}
.tc-foot{background:var(--ink);color:var(--cream);margin-top:0}
.tc-fwrap{max-width:1180px;padding:80px 32px 34px}
.tc-fcol h3{font-family:Inter,sans-serif;font-size:.66rem;letter-spacing:.24em;text-transform:uppercase;
  color:var(--brass);font-weight:600}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:#c9c1b3;font-size:.9rem}
.tc-fcol a{padding:2px 0}.tc-fcol a:hover{color:#fff}
.tc-foot .tc-brand__txt{color:var(--cream)}
.tc-flegal{border-top:1px solid #3a352d;font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:#8a8377}
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
.svc__row{display:grid;grid-template-columns:110px 1fr 1fr 132px;gap:28px;align-items:center;padding:26px 0;border-bottom:1px solid var(--rule);transition:padding-left .4s}
.svc__row:hover{padding-left:12px}
/* index rows carry no thumbnail, so they use the three-column form */
.svc__row--plain{grid-template-columns:110px 1fr 1.2fr;align-items:baseline}
.svc__thumb{display:block;overflow:hidden;justify-self:end}
.svc__thumb img{width:132px;height:88px;object-fit:cover;filter:grayscale(.2);transition:filter .35s}
.svc__row:hover .svc__thumb img{filter:none}
.svc__no{font-family:"Playfair Display",serif;font-size:1.3rem;color:var(--brass)}
.svc__t{font-family:"Playfair Display",serif;font-size:clamp(1.6rem,3.2vw,2.4rem);font-weight:700;margin:0;letter-spacing:normal;line-height:1.2}
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
@media(max-width:860px){
 .svc__row{grid-template-columns:56px 1fr;gap:14px}.svc__d{grid-column:1/-1;margin-top:6px}
 .svc__thumb{display:none}
 .timeline,.quotes__grid,.est__grid,.proc__head,.article{grid-template-columns:1fr}
 .timeline .tl{border-bottom:1px solid var(--rule)}.aside{position:static}
}
"""

def _iron_header(t, pages):
    return _chrome_header(t, pages, cta="Request an Estimate")

def _iron_footer(t, pages):
    return _chrome_footer(t, pages, blurb=(
        f'Considered garage door work across {H.esc(t["city"])} and the surrounding metro '
        f'— repair, restoration and new-door installation.'))

def iron_home(t, pages):
    e = H.esc
    h1, lead, faqs, svc, areas, guides = _home_data(t, pages)
    tiles = _svc_tiles(pages)
    rows = "".join(f'<a class="svc__row" href="{u}"><div class="svc__no serif">{i+1:02d}</div>'
                   f'<div class="svc__t serif">{title}</div><div class="svc__d">{blurb}</div>'
                   f'<span class="svc__thumb"><img src="{PHOTOS}{_card(t, i, H.CARD_IMGS[i % len(H.CARD_IMGS)])}" '
                   f'alt="{e(title)} in {e(t["city"])}" width="400" height="300" loading="lazy" decoding="async"></span></a>'
                   for i, (ic, title, blurb, u) in enumerate(tiles[:4]))
    q = faqs[0]
    schemas = [H.org_schema(t), H.faq_schema(faqs)]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), lead, "/", schemas, IRON_FONTS, og=_hero(t))
            + _iron_header(t, pages)
            + f'<section class="hero"><img src="{PHOTOS}{_hero(t)}" alt="{e(t["city"])} garage door" width="1600" height="900" fetchpriority="high" decoding="async"><div class="hero__in">'
              f'<div class="hero__rule"></div><p class="kick" style="color:#e6c893">Repair · Restoration · Installation</p>'
              f'<h1 class="serif">{e(h1)}</h1><p class="hero__lead">{e(lead)}</p>'
              f'<div class="hero__cta"><a class="pill" style="border-color:#e8e1d4;color:#f6f2ea" href="/services/">See The Work</a>'
              f'{_tel(t, "Or call the studio &nbsp;→", "ulink")}</div></div></section>'
            + f'<section class="manifesto wrap"><span class="kick">Our belief</span>'
              f'<p class="serif">A door opens ten thousand times a year. It deserves <span class="em">more thought</span> than a rushed afternoon and a stapled invoice.</p></section>'
            + f'<section class="svc wrap">{rows}</section>'
            + f'<section class="break"><img src="{PHOTOS}{_card(t, 4, "gd-6.jpg")}" alt="Craftsman at work" width="1600" height="900" loading="lazy" decoding="async"><blockquote class="serif">"They fixed the door. Then they told us how to keep it from breaking again."<cite>— A {e(t["city"])} homeowner</cite></blockquote></section>'
            + f'<section class="sec wrap"><div class="proc__head"><h2 class="serif">Unhurried, and in the right order.</h2><span class="kick">The process</span></div>'
              f'<div class="timeline"><div class="tl"><div class="tl__no serif">I</div><h3>Conversation</h3><p>You describe the door. We ask what a phone quote never does.</p></div>'
              f'<div class="tl"><div class="tl__no serif">II</div><h3>Inspection</h3><p>On time, a written assessment, a price before a wrench turns.</p></div>'
              f'<div class="tl"><div class="tl__no serif">III</div><h3>The Work</h3><p>Done once, cleanly, with parts sized for the door.</p></div>'
              f'<div class="tl"><div class="tl__no serif">IV</div><h3>Aftercare</h3><p>Notes on what we found, and a standing line for questions.</p></div></div></section>'
            # This slot held two five-star "customer quotes" -- one of them the text of
            # an FAQ answer attributed to a homeowner. Nobody said either, so it was
            # rewritten to show the FAQ honestly. Now that hb_faq() renders the full FAQ
            # with its schema a few sections below, showing the first two questions here
            # as well just says the same thing twice, so the slot is gone.
            + hb_stack(t, pages, faqs, pin=("about", "safety"),
                       drop=("services", "steps", "guides", "cta"))
            + f'<section class="sec est wrap"><div class="est__grid">'
              f'<div><span class="kick">Begin</span><h2 class="serif">Every door is a conversation.</h2>'
              f'<p>Tell us what yours is doing, and we\'ll tell you honestly what it needs — repair, restoration, or a fresh install for your {e(t["city"])} home.</p>'
              f'<a class="pill pill--brass" href="/request-a-quote/">Request an Estimate</a></div>'
              f'<div style="border:1px solid var(--rule);overflow:hidden;min-height:300px"><img src="{PHOTOS}{_card(t, 1, "gd-2.jpg")}" alt="{e(t["city"])} garage door work" width="1200" height="900" loading="lazy" decoding="async" style="width:100%;height:100%;object-fit:cover;filter:grayscale(.15)"></div>'
              f'</div></section>'
            + _iron_footer(t, pages) + "</body></html>")

def iron_inner(t, pages, p):
    e = H.esc
    label, parent = _LABELS.get(p["cat"], ("", "/"))
    h1 = p["h1"] or H.area_label(p)
    img = _inner(t, p)
    body = _inner_parts(t, p)
    aside = (f'<aside class="aside"><h3 class="serif">Book a visit</h3><p>Considered garage door work in {e(t["city"])}, {e(t["st"])}.</p>'
             f'{_tel(t, cls="tel serif")}'
             f'<a class="pill pill--brass" href="/request-a-quote/">Request an Estimate</a></aside>')
    schemas = _inner_schemas(t, p, h1, label, parent)
    return (_head(t, H.page_title(t, p, h1), p["meta"] or "", p["url"], schemas, IRON_FONTS, og=img)
            + _iron_header(t, pages)
            + f'<section class="phero"><div class="wrap"><div class="crumb"><a href="/">Home</a> / <a href="{parent}">{label}</a> / {e(h1)}</div><h1 class="serif">{e(h1)}</h1></div></section>'
            + f'<div class="wrap"><div class="article"><div class="body"><img src="{PHOTOS}{img}" alt="{e(h1)}" width="1200" height="900" loading="lazy" decoding="async">{body}</div>{aside}</div></div>'
            + _iron_footer(t, pages) + "</body></html>")

def iron_index(t, pages, cat, url, h1, eyebrow, blurb):
    e = H.esc
    items = _cat(pages, cat)
    # h2, not a plain div: on an index page these row titles are the page's real
    # section headings. As divs the page went straight from h1 to the footer's h3.
    rows = "".join(f'<a class="svc__row svc__row--plain" href="{p["url"]}"><div class="svc__no serif">{i+1:02d}</div><h2 class="svc__t serif">{e(H.area_label(p))}</h2><div class="svc__d">{e((p["meta"] or "").split(".")[0])}</div></a>'
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
             f'{_tel(t, cls="tel serif")}'
             f'<a class="pill pill--brass" href="/request-a-quote/">Request a Visit</a></aside>')
    schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), H.trust_desc(t, h1, url), url, schemas, IRON_FONTS)
            + _iron_header(t, pages)
            + f'<section class="phero"><div class="wrap"><div class="crumb"><a href="/">Home</a> / {e(h1)}</div><h1 class="serif">{e(h1)}</h1></div></section>'
            + _quote_block(t, is_quote)
            + f'<div class="wrap"><div class="article"><div class="body">{body}</div>{aside}</div></div>'
            + _iron_footer(t, pages) + "</body></html>")


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
/* --- shared chrome, nimbus dress: floating rounded pill bar, soft blue --- */
.tc-bar{top:16px;padding:0 16px;background:none}
.tc-inner{max-width:1020px;background:rgba(255,255,255,.9);backdrop-filter:blur(12px);border:1px solid #e7eef7;
  border-radius:999px;box-shadow:0 12px 30px rgba(44,58,73,.10);padding:10px 12px 10px 22px;gap:10px}
.tc-brand__txt{font-family:"Baloo 2",cursive;font-weight:800;font-size:1.2rem}
.tc-brand__mark img,.tc-brand__mark svg{height:38px;border-radius:10px}
.tc-brand--lockup img{height:40px}
.tc-trigger,.tc-link,.tc-msum{font-family:"Baloo 2",cursive;font-weight:600;border-radius:999px;padding:8px 14px}
.tc-trigger:hover,.tc-link:hover{background:var(--sky)}
.tc-caret{border-color:var(--blue)}
.tc-drop{background:#fff;border:1px solid #e7eef7;border-radius:18px;box-shadow:0 18px 38px rgba(44,58,73,.16);
  padding:10px;top:calc(100% + 12px)}
.tc-drop a{border-radius:12px;font-size:.92rem}
.tc-drop a:hover{background:var(--sky);color:var(--blue)}
.tc-drop a:first-child{color:var(--blue);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
.tc-tel{font-family:"Baloo 2",cursive;font-weight:700;color:var(--blue)}
.tc-cta{background:var(--blue);color:#fff;border-radius:999px;font-family:"Baloo 2",cursive;font-weight:700;
  padding:10px 20px;box-shadow:0 8px 18px rgba(76,141,255,.32)}
.tc-burger{background:var(--sky);border-radius:50%;width:42px;height:42px;padding:0 11px;color:var(--blue)}
.tc-mobile{max-width:1020px;margin:10px auto 0;background:#fff;border-radius:24px;padding:14px 18px 20px;
  box-shadow:0 12px 30px rgba(44,58,73,.12)}
.tc-msum,.tc-mlink{font-family:"Baloo 2",cursive;font-weight:700;border-radius:14px}
.tc-mlinks a{color:var(--soft);font-weight:600}
.tc-mcta{background:var(--blue);color:#fff;border-radius:999px;font-family:"Baloo 2",cursive;font-weight:700}
.tc-foot{background:#eef4fb;border-radius:44px 44px 0 0;margin-top:20px}
.tc-fcol h3{font-family:"Baloo 2",cursive;font-weight:700;font-size:1.05rem}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:var(--soft);font-weight:600}
.tc-fcol a:hover{color:var(--blue)}
.tc-flegal{border-top:2px solid #dde8f4;color:var(--soft);font-weight:600}
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
.tile__img{display:block;border-radius:20px;overflow:hidden;margin-bottom:18px;box-shadow:0 8px 16px rgba(44,58,73,.08)}
.tile__img img{width:100%;height:180px;object-fit:cover;display:block;transition:transform .45s ease}
.tile:hover .tile__img img{transform:scale(1.06)}
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
@media(max-width:900px){
 .tiles,.stepgrid,.why,.bubbles,.plans{grid-template-columns:1fr}.stepgrid::before{display:none}.bubble::after{display:none}}
"""

def _nim_call(t):
    """(href, label) for a call button that works with or without a phone on file."""
    if H.has_phone(t):
        return f'tel:{t["tel"]}', f'Call {H.esc(t["phone"])}'
    # don't say "Call" when the link goes to a form
    return "/request-a-quote/", "Book a visit"

def _nim_header(t, pages):
    return _chrome_header(t, pages, cta="Book now")

def _nim_footer(t, pages):
    return _chrome_footer(t, pages, blurb=(
        f'Friendly garage door care for {H.esc(t["city"])} homes — repairs, springs, '
        f'openers and new doors, booked around your day.'))

def nim_home(t, pages):
    e = H.esc
    h1, lead, faqs, svc, areas, guides = _home_data(t, pages)
    tiles = _svc_tiles(pages)
    # real per-service photography instead of a repeated wrench emoji as the "icon"
    tt = "".join(f'<a class="tile" href="{u}"><span class="tile__img">'
                 f'<img src="{PHOTOS}{_card(t, i, H.CARD_IMGS[i % len(H.CARD_IMGS)])}" '
                 f'alt="{e(title)} in {e(t["city"])}" width="800" height="600" loading="lazy" decoding="async">'
                 f'</span><h3>{title}</h3><p>{blurb}</p><span class="more">Learn more →</span></a>'
                 for i, (ic, title, blurb, u) in enumerate(tiles))
    faq = "".join(f'<details class="fq"{" open" if i==0 else ""}><summary>{e(q)}</summary><p>{e(a)}</p></details>' for i, (q, a) in enumerate(faqs))
    chref, clabel = _nim_call(t)
    schemas = [H.org_schema(t), H.faq_schema(faqs)]
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), lead, "/", schemas, NIM_FONTS, og=_hero(t))
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
            + f'<section class="sec"><div class="wrap why"><div class="why__img"><img src="{PHOTOS}{_card(t, 2, "gd-3.jpg")}" alt="A friendly technician" width="1200" height="900" loading="lazy" decoding="async"><div class="why__badge">🧡 Neighborly by nature</div></div>'
              f'<div><span class="eyebrow">Why folks pick us</span><h2>Fewer surprises, more smiles</h2><p style="color:var(--soft)">We treat your home like our own and your time like it matters.</p>'
              f'<ul class="checks"><li><span class="c">✓</span>Upfront prices, always explained</li><li><span class="c">✓</span>Friendly, vetted technicians</li><li><span class="c">✓</span>Tidy work &amp; clean-up after</li><li><span class="c">✓</span>No-pressure, honest advice</li></ul></div></div></section>'
            # This was three five-star "neighbor" testimonials with invented names
            # and quotes -- nobody said any of it. Same violation removed from
            # ironclad earlier; it was missed here. Now real content blocks.
            + hb_stack(t, pages, faqs, pin=("about", "tips"),
                       drop=("services", "steps", "faq", "cta"))
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
    img = _inner(t, p)
    body = _inner_parts(t, p)
    schemas = _inner_schemas(t, p, h1, label, parent)
    return (_head(t, H.page_title(t, p, h1), p["meta"] or "", p["url"], schemas, NIM_FONTS, og=img)
            + _nim_header(t, pages)
            + f'<section class="phero"><div class="crumb"><a href="/">Home</a> · <a href="{parent}">{label}</a> · {e(h1)}</div><h1>{e(h1)}</h1></section>'
            + f'<div class="article"><div class="body"><img src="{PHOTOS}{img}" alt="{e(h1)}" width="1200" height="900" loading="lazy" decoding="async">{body}</div></div>'
            + f'<div class="wrap" style="padding-bottom:40px">{_nim_aside(t)}</div>'
            + _nim_footer(t, pages) + "</body></html>")

def nim_index(t, pages, cat, url, h1, eyebrow, blurb):
    e = H.esc
    items = _cat(pages, cat)
    tt = "".join(f'<a class="tile" href="{p["url"]}"><div class="tile__ic">🚪</div><h2>{e(H.area_label(p))}</h2><p>{e((p["meta"] or "").split(".")[0])}</p><span class="more">Open →</span></a>' for p in items)
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
    return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), H.trust_desc(t, h1, url), url, schemas, NIM_FONTS)
            + _nim_header(t, pages)
            + f'<section class="phero"><div class="crumb"><a href="/">Home</a> · {e(h1)}</div><h1>{e(h1)}</h1></section>'
            + _quote_block(t, is_quote)
            + f'<div class="article"><div class="body">{body}</div></div>'
            + f'<div class="wrap" style="padding-bottom:40px">{_nim_aside(t)}</div>'
            + _nim_footer(t, pages) + "</body></html>")


NIM_BLOCKS = r'''
/* --- shared section blocks, nimbus dress: rounded, soft, pastel-tinted --- */
:root{--v-card-r:26px}   /* keep nimbus's roundness under every card variant */
.hb-eyebrow{color:var(--blue);font-weight:800}
.hb h2{font-family:"Baloo 2",cursive;font-weight:800}
.hb--svc,.hb--sig,.hb--faq{background:var(--sky)}
.hb--tips,.hb--doors{background:var(--mint)}
.hb--about,.hb--local,.hb--safety{background:#fff}
.hb--stats{background:var(--peach);padding:0}
.hb-statrow{padding:34px 0}
.hb-stat b{font-family:"Baloo 2",cursive;color:var(--blue)}
.hb-svc,.hb-guide,.hb-sig,.hb-door,.hb-tip,.hb-seg,.hb-rev{
  background:#fff;border:0;border-radius:var(--r);box-shadow:0 10px 26px rgba(44,58,73,.08)}
.hb-svc__img img,.hb-guide__img img,.hb-door__img img{border-radius:var(--r) var(--r) 0 0}
.hb-svc:hover,.hb-guide:hover,.hb-door:hover{transform:translateY(-5px);box-shadow:0 16px 34px rgba(44,58,73,.13)}
.hb-more{color:var(--blue);font-weight:800}
.hb-step__n{background:var(--blue);color:#fff;border-radius:50%}
.hb-areas a{background:#fff;border-radius:999px;text-align:center;font-weight:700;
  box-shadow:0 6px 16px rgba(44,58,73,.07)}
.hb-areas a:hover{background:var(--blue);color:#fff}
.hb-atier h3{color:var(--soft)}
.hb-faq{background:#fff;border-radius:20px;padding:18px 24px;margin-bottom:12px;border:0}
.hb-faq summary{font-family:"Baloo 2",cursive;font-weight:700}
.hb-rvr__c{background:#fff;border-radius:var(--r);box-shadow:0 10px 26px rgba(44,58,73,.08)}
.hb-rvr__c--alt{background:var(--lilac);box-shadow:none}
.hb-safety{background:var(--peach);border-radius:var(--r);padding:34px}
.hb-emerg{background:#fff;border-radius:var(--r);padding:26px 30px;box-shadow:0 10px 26px rgba(44,58,73,.08)}
.hb-emerg__btn{background:var(--blue);color:#fff;border-radius:999px}
.hb--cta{background:linear-gradient(135deg,var(--sky),var(--mint))}
.hb--cta .hb-cta__btn{background:var(--blue);color:#fff;border-radius:999px}
.hb--cta .hb-cta__btn--alt{background:#fff;color:var(--blue)}
'''

IRON_BLOCKS = r'''
/* --- shared section blocks, ironclad dress: paper, hairline rules, brass, no shadow --- */
:root{--v-card-r:0}      /* ironclad is square-cornered throughout */
.hb-eyebrow{color:var(--brass);letter-spacing:.28em;font-size:.7rem}
.hb h2{font-family:"Playfair Display",Georgia,serif;font-weight:700;letter-spacing:normal}
.hb--svc,.hb--sig,.hb--faq,.hb--stats{background:var(--cream)}
.hb--about,.hb--local,.hb--safety,.hb--tips,.hb--doors{background:var(--paper)}
.hb-lead,.hb-prose{color:var(--muted)}
.hb-svc,.hb-guide,.hb-sig,.hb-door,.hb-tip,.hb-seg,.hb-rev{
  background:var(--paper);border:1px solid var(--rule);border-radius:0;box-shadow:none}
.hb-svc:hover,.hb-guide:hover,.hb-door:hover{border-color:var(--brass)}
.hb-svc h3,.hb-guide h3,.hb-door h3,.hb-tip h3,.hb-sig h3{
  font-family:"Playfair Display",Georgia,serif;font-weight:700}
.hb-svc__img img,.hb-guide__img img,.hb-door__img img{filter:grayscale(.2)}
.hb-svc:hover .hb-svc__img img,.hb-guide:hover .hb-guide__img img{filter:none}
.hb-more{color:var(--brass);font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;font-weight:600}
.hb-step__n{background:none;color:var(--brass);border:1px solid var(--brass);border-radius:0;
  font-family:"Playfair Display",serif}
.hb-statrow{padding:30px 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.hb-stat b{font-family:"Playfair Display",serif;color:var(--brass)}
.hb-areas a{border:1px solid var(--rule);border-radius:0;font-size:.9rem}
.hb-areas a:hover{border-color:var(--brass);color:var(--brass)}
.hb-atier h3{color:var(--brass)}
.hb-faq{border-bottom:1px solid var(--rule)}
.hb-faq summary{font-family:"Playfair Display",Georgia,serif;font-size:1.15rem}
.hb-rvr__c{border:1px solid var(--rule)}
.hb-rvr__c--alt{background:var(--cream)}
.hb-safety{border-left:2px solid var(--brass);padding-left:28px}
.hb-emerg{border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}
.hb-emerg__btn{border:1px solid var(--brass);color:var(--brass);letter-spacing:.18em;
  text-transform:uppercase;font-size:.72rem}
.hb--cta{background:var(--ink);color:var(--cream)}
.hb--cta .hb-cta__btn{background:var(--brass);color:#fff;letter-spacing:.18em;
  text-transform:uppercase;font-size:.74rem}
.hb--cta .hb-cta__btn--alt{background:none;border:1px solid var(--cream);color:var(--cream)}
'''


# ---------------------------------------------------------------- registry
# note: inner() takes (t, p, pages) in build.py's GARAGE lambda, but our functions use
# (t, pages, p); adapt with a wrapper so the interface matches build.py exactly.
# These designs ship their own stylesheet rather than the shared design system, so the
# ================================================================ SHARED PAGE SKELETON
# The inner / index / trust pages of every design after ironclad and nimbus.
#
# Identity lives in the homepage, the chrome and the stylesheet -- that is what a
# visitor actually reads as "a different site". An article page is an article page in
# all of them: breadcrumb, H1, prose, a photo, a contact aside. Re-typing that seven
# more times is how ironclad and nimbus ended up with seven different half-correct
# breadcrumbs, so the markup is written once here and each design dresses it.
#
# Class contract: .pg-hero .pg-crumb .pg-wrap .pg-art .pg-body .pg-aside .pg-idx

def _pg_aside(t, heading="Talk to us", cta="Request a Quote"):
    e = H.esc
    return (f'<aside class="pg-aside"><h3>{e(heading)}</h3>'
            f'<p>Garage door help in {e(t["city"])}, {e(t["st"])}.</p>'
            f'{_tel(t, cls="pg-tel")}<a class="pg-btn" href="/request-a-quote/">{e(cta)}</a></aside>')


def _pg_crumb(trail):
    """Breadcrumb. Last item is the current page, so it is text, not a link."""
    e = H.esc
    parts = []
    for i, (label, url) in enumerate(trail):
        parts.append(e(label) if i == len(trail) - 1 else f'<a href="{url}">{e(label)}</a>')
    return f'<nav class="pg-crumb" aria-label="Breadcrumb">{" / ".join(parts)}</nav>'


def _gen_inner(fonts, cta="Request a Quote"):
    def inner(t, pages, p):
        e = H.esc
        label, parent = _LABELS.get(p["cat"], ("", "/"))
        h1 = p["h1"] or H.area_label(p)
        img = _inner(t, p)
        schemas = _inner_schemas(t, p, h1, label, parent)
        return (_head(t, H.page_title(t, p, h1), p["meta"] or "",
                      p["url"], schemas, fonts, og=img)
                + _chrome_header(t, pages, cta)
                + f'<section class="pg-hero"><div class="pg-wrap">'
                  f'{_pg_crumb([("Home", "/"), (label, parent), (h1, p["url"])])}'
                  f'<h1>{e(h1)}</h1></div></section>'
                + f'<div class="pg-wrap"><div class="pg-art"><div class="pg-body">'
                  f'<img src="{PHOTOS}{img}" alt="{e(h1)}" width="1200" height="900" loading="lazy" decoding="async">'
                  f'{_inner_parts(t, p)}</div>{_pg_aside(t, cta=cta)}</div></div>'
                + _chrome_footer(t, pages) + "</body></html>")
    return inner


def _gen_index(fonts, cta="Request a Quote"):
    def index(t, pages, cat, url, h1, eyebrow, blurb):
        e = H.esc
        # h2 per row: on an index page these titles are the page's real section
        # headings, and as plain divs the document went h1 -> footer h3.
        rows = "".join(
            f'<a class="pg-row" href="{p["url"]}"><span class="pg-row__n">{i + 1:02d}</span>'
            f'<h2>{e(H.area_label(p))}</h2>'
            f'<span class="pg-row__d">{e((p["meta"] or "").split(".")[0])}</span></a>'
            for i, p in enumerate(_cat(pages, cat)))
        schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
        return (_head(t, H.seo_title(f"{h1} | {t['brand']}"), blurb, url, schemas, fonts)
                + _chrome_header(t, pages, cta)
                + f'<section class="pg-hero"><div class="pg-wrap">'
                  f'{_pg_crumb([("Home", "/"), (h1, url)])}'
                  f'<h1>{e(h1)}</h1><p class="pg-eyebrow">{e(eyebrow)}</p></div></section>'
                + f'<div class="pg-wrap pg-idx">{rows}</div>'
                + _chrome_footer(t, pages) + "</body></html>")
    return index


def _gen_trust(fonts, cta="Request a Quote"):
    def trust(t, pages, url, h1, blocks, is_quote=False):
        e = H.esc
        body = "".join(f'<h2>{e(hh)}</h2><p>{e(bb)}</p>' for hh, bb in blocks)
        schemas = [H.org_schema(t), H.breadcrumb_schema(t, [("Home", "/"), (h1, url)])]
        return (_head(t, H.seo_title(f"{h1} | {t['brand']}"),
                      H.trust_desc(t, h1, url), url, schemas, fonts)
                + _chrome_header(t, pages, cta)
                + f'<section class="pg-hero"><div class="pg-wrap">'
                  f'{_pg_crumb([("Home", "/"), (h1, url)])}<h1>{e(h1)}</h1></div></section>'
                + _quote_block(t, is_quote)
                + f'<div class="pg-wrap"><div class="pg-art"><div class="pg-body">{body}</div>'
                  f'{_pg_aside(t, cta=cta)}</div></div>'
                + _chrome_footer(t, pages) + "</body></html>")
    return trust


# Structure for the shared page types; every design restyles these.
PAGE_CSS = """
.pg-wrap{max-width:1180px;margin:0 auto;padding:0 28px}
/* `.wrap` is the container name build.py's shared pieces use -- the quote form block
   and the GHL embed both wrap themselves in one. ironclad and nimbus define it in
   their own stylesheets; the block-composed designs did not, so on those seven the
   quote form had no max-width and no gutter: full-bleed on desktop, flush to the
   screen edge on a phone. Alias it to the page container. */
.wrap{max-width:1180px;margin:0 auto;padding:0 28px}
.pg-hero{padding:54px 0 44px}
.pg-crumb{font-size:.76rem;margin-bottom:14px}
.pg-crumb a{text-decoration:none;color:inherit}
.pg-hero h1{max-width:22ch}
.pg-eyebrow{margin-top:12px;opacity:.75}
.pg-art{display:grid;grid-template-columns:1fr 300px;gap:56px;padding:44px 0 76px;align-items:start}
.pg-body{min-width:0;max-width:66ch}
.pg-body img{width:100%;height:auto;margin:0 0 26px}
.pg-body h2{margin:32px 0 12px}.pg-body h3{margin:24px 0 10px}
.pg-body p{margin:0 0 15px}.pg-body ul,.pg-body ol{margin:0 0 15px 20px}
.pg-body details{padding:14px 0}.pg-body summary{cursor:pointer;font-weight:700}
.pg-aside{position:sticky;top:96px;padding:26px}
.pg-aside h3{margin:0 0 6px}.pg-aside p{margin:0 0 16px;opacity:.8}
.pg-tel{display:block;font-size:1.3rem;font-weight:700;margin-bottom:14px;text-decoration:none;color:inherit}
.pg-btn{display:block;text-align:center;padding:13px 18px;text-decoration:none}
.pg-idx{padding:8px 0 84px;display:flex;flex-direction:column}
.pg-row{display:grid;grid-template-columns:64px 1fr 1.1fr;gap:20px;align-items:baseline;
  padding:26px 6px;text-decoration:none;color:inherit}
.pg-row h2{margin:0;font-size:1.5rem}
.pg-row__d{opacity:.7;font-size:.94rem}
@media(max-width:900px){
  .pg-art{grid-template-columns:1fr;gap:32px}
  .pg-aside{position:static}
  .pg-row{grid-template-columns:44px 1fr;gap:12px}
  .pg-row__d{grid-column:1/-1}
}
"""


# ================================================================ HOME SECTION BLOCKS
# Composable homepage sections. A design picks which of these it uses and in what
# order; that ordering plus its stylesheet is what makes it read as its own site.
#
# Nothing here asserts a review score, a review count, a founding year, an award or a
# certification. build.py holds that line deliberately (see its `_home_sec` note) and
# ironclad used to break it with a hard-coded "Est. 2004" and two five-star quotes that
# no customer ever said. Copy below describes how the work is done, which the operator
# can stand behind, and per-city specifics come from the content JSON.

def hb_services(t, pages, eyebrow="What we do", title=None):
    """Service cards, each with the photo select_photos() picked for this city and
    service. The card images are the main place the brand/photos library shows up on a
    homepage -- without them these designs render as walls of text."""
    e = H.esc
    title = title or f"Garage door work in {t['city']}"
    tiles = "".join(
        f'<a class="hb-svc" href="{u}">'
        f'<span class="hb-svc__img"><img src="{PHOTOS}{_card(t, i, H.CARD_IMGS[i % len(H.CARD_IMGS)])}" '
        f'alt="{e(name)} in {e(t["city"])}" width="800" height="600" loading="lazy" decoding="async"></span>'
        f'<span class="hb-svc__txt"><h3>{e(name)}</h3><p>{e(blurb)}</p>'
        f'<span class="hb-more">Learn more</span></span></a>'
        for i, (_ic, name, blurb, u) in enumerate(_svc_tiles(pages)))
    return (f'<section class="hb hb--svc"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>{e(title)}</h2>'
            f'<div class="hb-svcs">{tiles}</div></div></section>')


def hb_steps(t, eyebrow="How it works"):
    e = H.esc
    steps = [("Tell us what the door is doing",
              "A description of the noise or the fault usually narrows it down before we arrive."),
             ("We diagnose and price it in writing",
              "You get the number for the whole job - parts and labour - before a wrench turns."),
             ("We fix it, and show you what failed",
              "Most repairs are done in one visit, and you keep the old part if you want it.")]
    cells = "".join(f'<li class="hb-step"><span class="hb-step__n">{i+1}</span>'
                    f'<h3>{e(a)}</h3><p>{e(b)}</p></li>' for i, (a, b) in enumerate(steps))
    return (f'<section class="hb hb--steps"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>Straightforward, in three steps</h2>'
            f'<ol class="hb-steps">{cells}</ol></div></section>')


def hb_signals(t, eyebrow="Why homeowners call us"):
    e = H.esc
    items = [("Same-day on most repairs", "Broken springs and stuck doors do not wait for a slot next week."),
             ("A written price, not a range", "You approve the number before the work starts, and it does not move."),
             ("We fix what is broken", "If a spring is all it needs, we will not talk you into a whole new door."),
             (f"We work {e(t['city'])} every day", "Local housing stock, local hardware, and the faults that come with both.")]
    cells = "".join(f'<div class="hb-sig"><h3>{a}</h3><p>{b}</p></div>' for a, b in items)
    # Needs its own h2: the tiles below are h3s, so a design that opens with this block
    # (hearth does) would otherwise step the document straight from h1 to h3.
    return (f'<section class="hb hb--sig"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p>'
            f'<h2>What you get on every call</h2>'
            f'<div class="hb-sigs">{cells}</div></div></section>')


def hb_areas(t, pages, eyebrow="Where we work"):
    """Service areas, split into neighborhoods inside the city and nearby communities
    when the content distinguishes them (the nb-/sub- filename prefix, kept as
    page["kind"]). Falls back to one flat list when a site only has one kind."""
    e = H.esc
    areas = _cat(pages, "area")
    if not areas:
        return ""
    nb = [p for p in areas if p.get("kind") == "nb"]
    sub = [p for p in areas if p.get("kind") == "sub"]
    link = lambda p: f'<a href="{p["url"]}">{e(H.area_label(p))}</a>'
    if nb and sub:
        body = (f'<div class="hb-atier"><h3>{e(t["city"])} neighborhoods</h3>'
                f'<div class="hb-areas">{"".join(link(p) for p in nb)}</div></div>'
                f'<div class="hb-atier"><h3>Nearby communities</h3>'
                f'<div class="hb-areas">{"".join(link(p) for p in sub)}</div></div>')
    else:
        body = f'<div class="hb-areas">{"".join(link(p) for p in areas)}</div>'
    return (f'<section class="hb hb--areas"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p>'
            f'<h2>Serving {e(t["city"])} and nearby</h2>'
            f'<p class="hb-lead">{len(areas)} {e(t["city"])}-area neighborhoods and '
            f'communities we cover - is your street on the list?</p>'
            f'<div class="hb-atiers">{body}</div>'
            f'<a class="hb-more" href="/service-areas/">All service areas</a></div></section>')


# ---- blocks ported from the default design's expanded homepage ----
# These sections existed only on the "garage" design, gated behind uses_expanded(), so
# nine of ten sites rendered a much thinner page than the engine could already produce.
# The copy and data (SYMPTOMS, DOOR_TYPES, REPAIR/REPLACE_SIGNS, MAINT_TIPS) stay in
# build.py and are reached through H -- only the markup is new here, so the two designs
# can never drift apart in wording.

def hb_symptoms(t, pages, eyebrow="Start here"):
    """Symptom chips -> the page that explains that symptom. Every chip resolves
    against a page this site actually has."""
    e = H.esc
    chips = "".join(f'<a class="hb-sym" href="{H._first_url(pages, cands)}">{e(label)}</a>'
                    for label, cands in H.SYMPTOMS)
    return (f'<section class="hb hb--sym"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>What is your door doing?</h2>'
            f'<p class="hb-lead">Pick the closest symptom and read what usually causes it '
            f'- or get in touch and describe it.</p>'
            f'<div class="hb-syms">{chips}</div></div></section>')


def hb_repair_replace(t, eyebrow="Straight answer"):
    e = H.esc
    rep = "".join(f"<li>{e(s)}</li>" for s in H.REPAIR_SIGNS)
    rpl = "".join(f"<li>{e(s)}</li>" for s in H.REPLACE_SIGNS)
    return (f'<section class="hb hb--rvr"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>Repair it, or replace it?</h2>'
            f'<p class="hb-lead">Nobody should be sold a whole new door for a broken spring. '
            f'Here is how the call actually gets made.</p>'
            f'<div class="hb-rvr">'
            f'<div class="hb-rvr__c"><h3>Repair usually wins when</h3><ul>{rep}</ul></div>'
            f'<div class="hb-rvr__c hb-rvr__c--alt"><h3>Replacement usually wins when</h3><ul>{rpl}</ul></div>'
            f'</div></div></section>')


def hb_doors(t, pages, eyebrow="Door styles"):
    """Door-style grid. Uses the six GD INSTALLATION photos select_photos() reserved
    for this block when the site has them."""
    e = H.esc
    imgs = t.get("door_imgs") or []
    url = H._first_url(pages, ["/services/garage-door-installation/"], "/request-a-quote/")
    cells = ""
    for i, (name, blurb) in enumerate(H.DOOR_TYPES):
        pic = (f'<span class="hb-door__img"><img src="{PHOTOS}{imgs[i % len(imgs)]}" '
               f'alt="{e(name)} garage door" width="800" height="600" loading="lazy" '
               f'decoding="async"></span>') if imgs else ""
        cells += (f'<a class="hb-door" href="{url}">{pic}'
                  f'<span class="hb-door__t"><h3>{e(name)}</h3><p>{e(blurb)}</p></span></a>')
    return (f'<section class="hb hb--doors"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>Doors we install</h2>'
            f'<div class="hb-doors">{cells}</div></div></section>')


def hb_maintenance(t, eyebrow="Keep it running"):
    e = H.esc
    cells = "".join(f'<div class="hb-tip"><h3>{e(title)}</h3><p>{e(body)}</p></div>'
                    for _ic, title, body in H.MAINT_TIPS)
    return (f'<section class="hb hb--tips"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>Four things that keep a door alive</h2>'
            f'<div class="hb-tips">{cells}</div></div></section>')


def hb_safety(t, eyebrow="Please read"):
    e = H.esc
    return (f'<section class="hb hb--safety"><div class="hb-wrap"><div class="hb-safety">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p>'
            f'<h2>The one job we ask you not to do yourself</h2>'
            f'<p>A torsion spring stores enough energy to lift a door that weighs about as '
            f'much as you do, and it lets go of all of it the moment a winding bar slips. '
            f'Spring replacement is the most common source of serious injury in this trade, '
            f'and it is the one repair we tell every homeowner in {e(t["city"])} to hand over.</p>'
            f'<p>Plenty of the rest is fair game for a confident DIYer. This one is not.</p>'
            f'</div></div></section>')


def hb_emergency(t):
    e = H.esc
    ask = "call" if H.has_phone(t) else "send it through"
    cta = _tel(t, label=f'Call {e(t["phone"])}', cls="hb-emerg__btn") or \
        '<a class="hb-emerg__btn" href="/request-a-quote/">Request urgent service</a>'
    return (f'<section class="hb hb--emerg"><div class="hb-wrap"><div class="hb-emerg">'
            f'<div><b>Door stuck open, or a spring already gone?</b>'
            f'<span>Neither one waits for an appointment window - {ask} and we will move '
            f'the job up the list.</span></div>{cta}</div></div></section>')


def hb_local(t, pages, eyebrow="Local knowledge"):
    """Renders the city's own copy from the home JSON. Returns "" when that city has no
    such section, so it never prints a generic paragraph in its place."""
    e = H.esc
    home = pages.get("/")
    body = ""
    for sec in (home or {}).get("sections", []):
        h2 = (sec.get("h2") or "").lower()
        if any(k in h2 for k in ("local", "why_local", "area", "climate", "weather")):
            body = sec.get("body", "")
            break
    if not body:
        return ""
    return (f'<section class="hb hb--local"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p>'
            f'<h2>Doors in {e(t["city"])}, specifically</h2>'
            f'<div class="hb-prose">{H.render_body(body)}</div></div></section>')


def hb_reviews(t, eyebrow="In their words"):
    """Customer reviews, in one of three layouts chosen per domain.

    Renders ONLY from `reviews` in sites.json -- a list of {quote, name, area?}. There
    is no fallback copy and no placeholder, deliberately: this engine has twice shipped
    invented five-star testimonials with made-up names, and a review block that writes
    its own reviews is the single easiest way for that to happen again. No data, no
    section.

    Shape:  "testimonials": [{"quote": "...", "name": "R. Patel", "area": "Oak Lawn"}]

    Note the key is `testimonials`, not `reviews`: sites.json already uses `reviews` for
    a review *count* string that pairs with `rating`, and both are read below.
    """
    items = [r for r in (t.get("testimonials") or []) if isinstance(r, dict)
             and (r.get("quote") or "").strip()]
    if not items:
        return ""
    e = H.esc
    layout = H.recipe(t)["reviews"]
    cells = ""
    for r in items:
        who = e(r.get("name") or "Verified customer")
        where = f' &middot; {e(r["area"])}' if r.get("area") else ""
        cells += (f'<figure class="hb-rev"><blockquote>{e(r["quote"])}</blockquote>'
                  f'<figcaption>{who}{where}</figcaption></figure>')
    rating = ""
    if t.get("rating") and t.get("reviews"):
        rating = (f'<p class="hb-lead">{e(str(t["rating"]))} out of 5 from '
                  f'{e(str(t["reviews"]))} reviews</p>')
    return (f'<section class="hb hb--rev hb-rev--{layout}"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>What {e(t["city"])} customers say</h2>'
            f'{rating}<div class="hb-revs">{cells}</div></div></section>')


def hb_gallery(t, eyebrow="Recent work"):
    """A photo grid of real jobs. Uses the dedicated gallery set select_photos() picks,
    which is offset from the service-card shots so this is not the same six images
    again. Renders nothing if the photo library has no match for this site."""
    e = H.esc
    imgs = t.get("gallery_imgs") or []
    if len(imgs) < 4:
        return ""
    cells = "".join(
        f'<figure class="hb-shot"><img src="{PHOTOS}{fn}" alt="Garage door work in {e(t["city"])}" '
        f'width="800" height="600" loading="lazy" decoding="async"></figure>' for fn in imgs)
    return (f'<section class="hb hb--gallery"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p>'
            f'<h2>Doors we have worked on around {e(t["city"])}</h2>'
            f'<div class="hb-shots">{cells}</div></div></section>')


def hb_announce(t):
    """Thin bar above the header. Renders only when `announce` is configured for the
    site (or in defaults) -- an empty promo bar is worse than none, and inventing a
    seasonal offer would put a claim on the page nobody agreed to."""
    msg = (t.get("announce") or "").strip()
    if not msg:
        return ""
    link = ""
    if t.get("announce_url"):
        link = f' <a href="{H.esc(t["announce_url"])}">{H.esc(t.get("announce_cta") or "Learn more")}</a>'
    return f'<div class="hb-announce"><div class="hb-wrap"><span>{H.esc(msg)}</span>{link}</div></div>'


def hb_stats(t, pages):
    """A small counted strip. Every figure is derived from what this site actually
    contains -- services built, areas covered, guides written -- so nothing here is a
    number someone has to stand behind. Deliberately no population or "jobs completed"
    figure: neither is in the data, and both would be invented."""
    e = H.esc
    svc, areas, guides = _cat(pages, "service"), _cat(pages, "area"), _cat(pages, "guide")
    # Labels are written for a homeowner, not for whoever built the site. "Guides
    # written" and "Diagnosis / first, then the fix" were engine-speak -- a visitor has
    # no idea what a "guide" is here or why a count of them matters.
    items = []
    if svc:
        items.append((str(len(svc)), "services we handle"))
    if areas:
        items.append((str(len(areas)), f"areas around {t['city']}"))
    items.append(("Same-day", "on most repairs"))
    items.append(("Written", "prices before we start"))
    cells = "".join(f'<div class="hb-stat"><b>{e(n)}</b><span>{e(l)}</span></div>' for n, l in items)
    return f'<section class="hb hb--stats"><div class="hb-wrap"><div class="hb-statrow">{cells}</div></div></section>'


def hb_about(t, pages, eyebrow="About"):
    """A short business introduction on the homepage. The site has an /about/ page, but
    nothing on the homepage ever said who the company is."""
    e = H.esc
    home = pages.get("/")
    # prefer the city's own copy where the content JSON provides it
    intro = ""
    for sec in (home or {}).get("sections", []):
        body = (sec.get("body") or "").strip()
        if body and not body.startswith("-"):
            intro = body.split("\n\n")[0]
            break
    if not intro:
        intro = (f"{t['brand']} works on garage doors across {t['city']}, {t['st']} and the "
                 f"surrounding metro - repair, spring and opener service, and new-door "
                 f"installation.")
    second = (f"Garage door problems are usually urgent: a car shut in, or a door that will "
              f"not close and seal the house. The approach is to say plainly what a door "
              f"needs, what it does not, and when a repair makes better sense than a "
              f"replacement - or the other way round.")
    return (f'<section class="hb hb--about"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>About {e(t["brand"])}</h2>'
            f'<div class="hb-prose"><p>{e(intro)}</p><p>{e(second)}</p></div></div></section>')


def hb_segments(t, pages, eyebrow="Who we help"):
    """Residential / commercial split.

    Gated on a `commercial` flag because it is a claim about what this business takes
    on, not a design choice -- asserting commercial service for 1000 domains nobody has
    checked is the same mistake as the invented "Est. 2004". Turn it on per site, or
    once in the `defaults` block of config/sites.json."""
    if not t.get("commercial"):
        return ""
    e = H.esc
    svc_url = "/services/" if _cat(pages, "service") else "/request-a-quote/"
    cards = [
        ("Residential", f"Homes in {t['city']}",
         "Repair, spring and opener service, and new door installation for single- "
         "and double-car home garages."),
        ("Commercial", "Businesses and property",
         "Rolling steel, sectional and dock doors, serviced with the higher cycle "
         "counts of commercial use in mind."),
    ]
    cells = "".join(
        f'<a class="hb-seg" href="{svc_url}"><span class="hb-seg__k">{e(k)}</span>'
        f'<h3>{e(h)}</h3><p>{e(b)}</p><span class="hb-more">See services</span></a>'
        for k, h, b in cards)
    return (f'<section class="hb hb--seg"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>Residential &amp; commercial</h2>'
            f'<div class="hb-segs">{cells}</div></div></section>')


def hb_guides(t, pages, eyebrow="Good to know"):
    e = H.esc
    guides = _cat(pages, "guide")
    if not guides:
        return ""
    imgs = t.get("inner_imgs") or {}
    cards = "".join(
        f'<a class="hb-guide" href="{p["url"]}">'
        + (f'<span class="hb-guide__img"><img src="{PHOTOS}{imgs[p["url"]]}" alt="{e(H.area_label(p))}" '
           f'width="800" height="600" loading="lazy" decoding="async"></span>' if imgs.get(p["url"]) else "")
        + f'<span class="hb-guide__txt"><h3>{e(H.area_label(p))}</h3>'
          f'<p>{e((p["meta"] or "").split(".")[0])}</p></span></a>' for p in guides)
    return (f'<section class="hb hb--guides"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>Plain answers, before you call</h2>'
            f'<div class="hb-guides">{cards}</div></div></section>')


def hb_faq(faqs, eyebrow="Questions"):
    e = H.esc
    items = "".join(f'<details class="hb-faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>'
                    for q, a in faqs)
    return (f'<section class="hb hb--faq"><div class="hb-wrap">'
            f'<p class="hb-eyebrow">{e(eyebrow)}</p><h2>Frequently asked</h2>'
            f'<div class="hb-faqs">{items}</div></div></section>')


def hb_cta(t, heading=None, cta="Request a quote", compact=False):
    """The conversion band. `compact` is the mid-page form: one line, slimmer, and
    worded as an interruption rather than a close, so a page carrying two CTAs does not
    print the same block twice."""
    e = H.esc
    if compact:
        heading = heading or f"Door already down? {t['city']} calls get same-day slots first."
        action = _tel(t, label=f'Call {e(t["phone"])}', cls="hb-cta__btn") or ""
        return (f'<section class="hb hb--cta hb--cta-slim"><div class="hb-wrap">'
                f'<div class="hb-cta__row"><p>{e(heading)}</p>'
                f'<div class="hb-cta__acts">{action}'
                f'<a class="hb-cta__btn hb-cta__btn--alt" href="/request-a-quote/">{e(cta)}</a>'
                f'</div></div></div></section>')
    heading = heading or f"Need a garage door fixed in {t['city']}?"
    sub = ("Tell us what it is doing and we will come back with a written price."
           if not H.has_phone(t) else "Call for same-day service on most repairs.")
    action = _tel(t, label=f'Call {e(t["phone"])}', cls="hb-cta__btn") or ""
    return (f'<section class="hb hb--cta"><div class="hb-wrap">'
            f'<h2>{e(heading)}</h2><p>{e(sub)}</p>'
            f'<div class="hb-cta__acts">{action}'
            f'<a class="hb-cta__btn hb-cta__btn--alt" href="/request-a-quote/">{e(cta)}</a>'
            f'</div></div></section>')


def hb_photo(t, i, alt=None, cls=""):
    e = H.esc
    return (f'<img class="hb-photo {cls}" src="{PHOTOS}{_card(t, i, H.CARD_IMGS[i % len(H.CARD_IMGS)])}" '
            f'alt="{e(alt or f"Garage door work in {t["city"]}")}" width="1200" height="900" '
            f'loading="lazy" decoding="async">')


# ---------------------------------------------------------------- homepage composition
# At ~1000 sites across ten designs, roughly a hundred sites share each design. If they
# also share a section order, they are the same page in different colours. So the middle
# of the homepage is ordered per domain: deterministic (a domain always builds the same
# site, so diffs stay reviewable and nothing churns between builds) but different from
# its neighbours.
#
# Anchors are fixed on purpose rather than shuffled: services stays near the top because
# it is what the visitor came for, and areas -> FAQ -> CTA close every page because that
# is the conversion path. Only the explanatory middle moves.

def _domain_order(items, seed):
    """Stable per-domain ordering. Same domain + same block set -> same order forever."""
    import hashlib
    keyed = [(hashlib.md5(f"{seed}|{name}".encode()).hexdigest(), name, fn)
             for name, fn in items]
    return [(name, fn) for _, name, fn in sorted(keyed)]


def hb_stack(t, pages, faqs, pin=(), drop=()):
    """The homepage body for a block-composed design.

    `pin` lets a design fix a few blocks at the top -- that is part of its identity
    (atlas leads with its at-a-glance stats, hearth with a warm intro). Everything else
    is ordered by domain. `drop` removes blocks a design renders in its own markup, so
    nothing appears twice.
    """
    blocks = {
        "about":    lambda: hb_about(t, pages),
        "stats":    lambda: hb_stats(t, pages),
        "symptoms": lambda: hb_symptoms(t, pages),
        "signals":  lambda: hb_signals(t),
        "steps":    lambda: hb_steps(t),
        "rvr":      lambda: hb_repair_replace(t),
        "doors":    lambda: hb_doors(t, pages),
        "tips":     lambda: hb_maintenance(t),
        "safety":   lambda: hb_safety(t),
        "emergency": lambda: hb_emergency(t),
        "local":    lambda: hb_local(t, pages),
        "segments": lambda: hb_segments(t, pages),
        "guides":   lambda: hb_guides(t, pages),
        "gallery":  lambda: hb_gallery(t),
        "reviews":  lambda: hb_reviews(t),
    }
    for name in tuple(drop) + tuple(H.recipe(t)["drop"]):
        blocks.pop(name, None)
    pinned = [(n, blocks.pop(n)) for n in pin if n in blocks]
    middle = _domain_order(list(blocks.items()), t.get("domain", ""))
    # ironclad and nimbus render their own services rows, so they drop this anchor
    # rather than printing the same list twice
    out = [] if "services" in drop else [hb_services(t, pages)]
    out += [fn() for _, fn in pinned]
    # cta axis: where the *extra* conversion band sits. The closing CTA always stays --
    # it is the page's main conversion path -- so this adds at most one more, and the
    # extra one uses the slim form. The axis previously emitted a class nothing read.
    mode = H.recipe(t)["cta"]
    blocks_mid = [fn() for _, fn in middle]
    if mode == "mid" and len(blocks_mid) > 3:
        blocks_mid.insert(len(blocks_mid) // 2, hb_cta(t, compact=True))
    elif mode == "both" and blocks_mid:
        blocks_mid.insert(1 if len(blocks_mid) > 1 else 0, hb_cta(t, compact=True))
    out += blocks_mid
    # The closing anchors are droppable as well: nimbus ends with its own FAQ accordion
    # and CTA panel, ironclad with its own estimate band. Appending the shared ones on
    # top printed the same questions and the same call to action twice.
    if "areas" not in drop:
        out.append(hb_areas(t, pages))
    if "faq" not in drop:
        out.append(hb_faq(faqs))
    if "cta" not in drop:
        out.append(hb_cta(t))
    return "".join(out)


# Structural CSS for the blocks above. Designs restyle freely; this only guarantees
# the sections lay out sanely before any theming is applied.
BLOCK_CSS = """
.hb{padding:76px 0}
.hb-wrap{max-width:1180px;margin:0 auto;padding:0 28px}
.hb-eyebrow{font-size:.74rem;letter-spacing:.2em;text-transform:uppercase;margin:0 0 12px;opacity:.75}
.hb h2{margin:0 0 34px}
.hb-svcs{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.hb-svc{display:flex;flex-direction:column;text-decoration:none;color:inherit;overflow:hidden}
.hb-svc__img{display:block;overflow:hidden}
.hb-svc__img img{width:100%;height:200px;object-fit:cover;transition:transform .45s ease}
.hb-svc:hover .hb-svc__img img{transform:scale(1.06)}
.hb-svc__txt{display:block;padding:26px}
.hb-svc h3{margin:0 0 10px}.hb-svc p{margin:0 0 14px;opacity:.8}
.hb-more{display:inline-block;font-weight:700;text-decoration:none}
.hb-steps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:26px}
.hb-step__n{display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;
  border-radius:50%;font-weight:800;margin-bottom:14px}
.hb-step h3{margin:0 0 8px;font-size:1.12rem}.hb-step p{margin:0;opacity:.8}
.hb-sigs{display:grid;grid-template-columns:repeat(4,1fr);gap:24px}
/* Every element the card axis can turn into a card MUST carry its own padding. The
   axis adds a background, a border and a shadow; a card whose text touches its own
   edge reads as broken. .hb-svc / .hb-guide / .hb-door delegate this to their inner
   __txt wrapper so the image can sit flush; .hb-tip and .hb-seg declare it directly.
   .hb-sig had no base rule at all, so on quarry (card=raised, which paints a
   background) the copy sat against the border. */
.hb-sig{padding:24px}
.hb-sig h3{margin:0 0 8px;font-size:1.05rem}.hb-sig p{margin:0;opacity:.8;font-size:.94rem}
.hb-areas{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:22px}
.hb-areas a{padding:12px 14px;text-decoration:none;color:inherit}
.hb-lead{margin:-18px 0 26px;max-width:62ch;opacity:.8}
.hb-atiers{display:flex;flex-direction:column;gap:26px;margin-bottom:8px}
.hb-atier h3{margin:0 0 12px;font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;opacity:.7}
/* announcement bar */
.hb-announce{width:100%;font-size:.9rem}
.hb-announce .hb-wrap{display:flex;gap:10px;justify-content:center;align-items:center;
  flex-wrap:wrap;padding-top:9px;padding-bottom:9px;text-align:center}
.hb-announce a{color:inherit;text-decoration:underline}
/* stat strip */
.hb--stats{padding:0}
.hb-statrow{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;padding:26px 0}
.hb-stat{display:flex;flex-direction:column;gap:2px}
.hb-stat b{font-size:clamp(1.5rem,3vw,2.1rem);line-height:1.05}
.hb-stat span{font-size:.88rem;opacity:.75}
/* about */
.hb-prose{max-width:68ch;display:flex;flex-direction:column;gap:14px}
/* residential / commercial */
.hb-segs{display:grid;grid-template-columns:1fr 1fr;gap:22px}
.hb-seg{display:block;padding:30px;text-decoration:none;color:inherit}
.hb-seg__k{display:inline-block;font-size:.7rem;letter-spacing:.18em;text-transform:uppercase;
  opacity:.7;margin-bottom:10px}
.hb-seg h3{margin:0 0 10px}.hb-seg p{margin:0 0 14px;opacity:.8}
.hb-guides{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.hb-guide{display:flex;flex-direction:column;text-decoration:none;color:inherit;overflow:hidden}
.hb-guide__img{display:block;overflow:hidden}
.hb-guide__img img{width:100%;height:170px;object-fit:cover}
.hb-guide__txt{display:block;padding:24px}
.hb-guide h3{margin:0 0 8px;font-size:1.1rem}.hb-guide p{margin:0;opacity:.8;font-size:.94rem}
.hb-faqs{display:flex;flex-direction:column}
.hb-faq{padding:18px 0}
.hb-faq summary{cursor:pointer;font-weight:700;font-size:1.05rem}
.hb-faq p{margin:12px 0 0;opacity:.85;max-width:70ch}
.hb--cta{text-align:center}
.hb--cta-slim{padding-top:0;padding-bottom:0;text-align:left}
.hb--cta-slim .hb-wrap{padding-top:26px;padding-bottom:26px}
.hb-cta__row{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}
.hb-cta__row p{margin:0;font-size:1.08rem;font-weight:600;max-width:52ch}
.hb--cta-slim .hb-cta__acts{justify-content:flex-end;margin:0}
.hb--cta p{margin:0 0 24px;opacity:.85}
.hb-cta__acts{display:flex;gap:14px;justify-content:center;flex-wrap:wrap}
.hb-cta__btn{display:inline-block;padding:15px 30px;text-decoration:none;font-weight:700}
.hb-photo{width:100%;height:auto;display:block}
.hb-shots{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.hb-shot{margin:0;overflow:hidden}
.hb-shot img{width:100%;height:220px;object-fit:cover;display:block;transition:transform .5s ease}
.hb-shot:hover img{transform:scale(1.05)}
@media(max-width:980px){.hb-shots{grid-template-columns:1fr 1fr}}
@media(max-width:620px){.hb-shots{grid-template-columns:1fr}.hb-shot img{height:200px}}
/* ported expanded-homepage blocks */
.hb-syms{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.hb-sym{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 16px;
  text-decoration:none;color:inherit;font-weight:600}
.hb-sym::after{content:"→";opacity:.6}
.hb-rvr{display:grid;grid-template-columns:1fr 1fr;gap:22px}
.hb-rvr__c{padding:28px}
.hb-rvr__c h3{margin:0 0 14px;font-size:1.1rem}
.hb-rvr__c ul{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:9px}
.hb-rvr__c li{opacity:.85}
.hb-doors{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.hb-door{display:flex;flex-direction:column;text-decoration:none;color:inherit;overflow:hidden}
.hb-door__img{display:block;overflow:hidden}
.hb-door__img img{width:100%;height:170px;object-fit:cover;display:block;transition:transform .45s ease}
.hb-door:hover .hb-door__img img{transform:scale(1.06)}
.hb-door__t{display:block;padding:22px}
.hb-door h3{margin:0 0 7px;font-size:1.05rem}.hb-door p{margin:0;opacity:.8;font-size:.92rem}
.hb-tips{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.hb-tip{padding:24px}
.hb-tip h3{margin:0 0 8px;font-size:1.02rem}.hb-tip p{margin:0;opacity:.8;font-size:.93rem}
.hb-safety{max-width:70ch;display:flex;flex-direction:column;gap:12px}
.hb--emerg{padding:0}
.hb-emerg{display:flex;align-items:center;justify-content:space-between;gap:22px;
  flex-wrap:wrap;padding:26px 0}
.hb-emerg b{display:block;font-size:1.1rem;margin-bottom:4px}
.hb-emerg span{opacity:.85}
.hb-emerg__btn{display:inline-block;padding:13px 26px;text-decoration:none;font-weight:700;white-space:nowrap}
@media(max-width:980px){
  .hb-syms{grid-template-columns:1fr 1fr}
  .hb-rvr,.hb-doors,.hb-tips{grid-template-columns:1fr}
}
@media(max-width:620px){
  .hb-syms{grid-template-columns:1fr}
  .hb-emerg{flex-direction:column;align-items:flex-start}
}

@media(max-width:980px){
  .hb-svcs,.hb-steps,.hb-guides,.hb-segs{grid-template-columns:1fr}
  .hb-sigs,.hb-areas,.hb-statrow{grid-template-columns:1fr 1fr}
}
@media(max-width:620px){
  .hb{padding:52px 0}.hb-wrap{padding:0 18px}
  .hb-sigs,.hb-areas{grid-template-columns:1fr}
  .hb-statrow{gap:14px}
  .hb-seg{padding:24px}
}
"""


# skip-link and focus-ring rules have to be appended here instead of coming for free.
A11Y_CSS = """
.skip{position:absolute;left:-9999px;top:0;z-index:200;background:#111;color:#fff;
  padding:12px 18px;font-weight:700}
.skip:focus{left:0;text-decoration:none}
:focus-visible{outline:3px solid currentColor;outline-offset:2px}
"""

# Opt-in plates for designs whose chrome is dark. Appended per design in REGISTRY
# rather than applied globally, so the light designs are not given a white box they
# do not need.
# Plate the *artwork* only, never the whole brand link -- these bars set `color:#fff`,
# so a plate around the link would put white text on a white box.
# `--lockup` is the logo-only render; `__mark` is the badge that sits beside a label.
DARK_FOOT_LOGO = """
.tc-foot .tc-brand--lockup{background:#fff;border-radius:16px;padding:12px 20px;
  display:inline-flex;align-items:center;box-shadow:0 4px 16px rgba(0,0,0,.28)}
.tc-foot .tc-brand__mark{background:#fff;border-radius:12px;padding:8px 12px;
  display:inline-flex;align-items:center}
"""
DARK_BAR_LOGO = """
.tc-bar .tc-brand--lockup{background:#fff;border-radius:12px;padding:5px 12px;
  display:inline-flex;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.22)}
.tc-bar .tc-brand__mark{background:#fff;border-radius:10px;padding:4px 8px;
  display:inline-flex;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.22)}
"""


def _paint(css, t):
    """Substitute the site's own brand palette into a design's stylesheet.

    A design owns structure and typography; the colour comes from the site's theme,
    which engine.py derives from the brand hex in domains.csv. That way two sites on
    the same design still read as different companies -- and each one matches its own
    logo instead of a palette picked for someone else."""
    return (css.replace("__P__", t.get("p", "#12213a"))
               .replace("__PD__", t.get("pd", "#0b1626"))
               .replace("__ACCENT__", t.get("accent", "#c2703a"))
               .replace("__ONACCENT__", t.get("on_accent", "#ffffff")))


def _mk(css_str, home, inner, index, trust, blocks=False):
    # CHROME_CSS first so a design's own rules can theme it; the design stylesheet
    # always wins on colour/type, never on the layout that makes the nav work.
    base = CHROME_CSS + (PAGE_CSS + BLOCK_CSS if blocks else "")
    return {"css": (lambda cs: (lambda t: base + _paint(cs, t) + A11Y_CSS + H.QFORM_CSS
                                          + H.actionbar_css(t) + H.fx_css(t)
                                          + H.VARIANT_CSS + H.type_css(t) + H.footer_css(t)))(css_str),
            "home": home,
            "inner": (lambda fn: (lambda t, p, pages: fn(t, pages, p)))(inner),
            "index": index, "trust": trust}


def _design(fonts, css, home_fn, cta="Request a Quote"):
    """A design built on the shared chrome + shared page skeleton + section blocks.
    Only the homepage and the stylesheet are bespoke."""
    return _mk(css, home_fn, _gen_inner(fonts, cta), _gen_index(fonts, cta),
               _gen_trust(fonts, cta), blocks=True)


def _home_head(t, pages, fonts, cta, bodyclass=""):
    """Head + chrome shared by the block-composed homepages."""
    h1, lead, faqs, svc, areas, guides = _home_data(t, pages)
    schemas = [H.org_schema(t), H.faq_schema(faqs)]
    head = _head(t, H.seo_title(f"{h1} | {t['brand']}"), lead, "/", schemas, fonts,
                 bodyclass=bodyclass, og=_hero(t))
    return h1, lead, faqs, head + _chrome_header(t, pages, cta)


# ---------------------------------------------------------------- FORGE
# industrial: near-black steel, brand-colour rule, condensed caps, square corners
FORGE_FONTS = "family=Oswald:wght@400;500;600;700&family=Inter:wght@400;500;700"
FORGE_CSS = r"""
:root{--p:__P__;--acc:__ACCENT__;--steel:#14171c;--steel2:#1c2028;--line:#2c313b;--dim:#98a0ad}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Inter,sans-serif;background:var(--steel);color:#e8ebef;line-height:1.65}
h1,h2,h3,.disp{font-family:Oswald,Impact,sans-serif;text-transform:uppercase;letter-spacing:.02em;font-weight:600;line-height:1.05}
h1{font-size:clamp(2.4rem,5.4vw,4.2rem)}h2{font-size:clamp(1.8rem,3.4vw,2.6rem)}
a{color:inherit}img{display:block;max-width:100%}
.tc-bar{background:rgba(20,23,28,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}
.tc-trigger,.tc-link,.tc-msum{font-family:Oswald,sans-serif;text-transform:uppercase;font-size:.86rem;letter-spacing:.08em}
.tc-drop,.tc-mobile{background:var(--steel2);border:1px solid var(--line)}
.tc-drop a:hover{background:#252a34;color:var(--acc)}
.tc-drop a:first-child{color:var(--acc);border-bottom:1px solid var(--line);margin-bottom:6px}
.tc-tel{font-family:Oswald,sans-serif;font-size:1.1rem;color:var(--acc)}
.tc-cta,.hb-cta__btn,.pg-btn{background:var(--acc);color:__ONACCENT__;font-family:Oswald,sans-serif;
  text-transform:uppercase;letter-spacing:.08em;border-radius:0}
.tc-burger{color:#e8ebef}
.tc-msum,.tc-mlink{border-bottom:1px solid var(--line)}
.tc-foot{background:#0e1116;border-top:3px solid var(--acc)}
.tc-fcol h3{font-family:Oswald,sans-serif;text-transform:uppercase;letter-spacing:.14em;font-size:.8rem;color:var(--acc)}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:var(--dim);font-size:.92rem}
.tc-fcol a:hover{color:#fff}
.tc-flegal{border-top:1px solid var(--line);color:#6d7583;font-size:.8rem}
/* hero */
.fg-hero{position:relative;min-height:74vh;display:flex;align-items:flex-end;overflow:hidden}
.fg-hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:grayscale(.4) brightness(.42)}
.fg-hero__in{position:relative;z-index:2;max-width:1180px;margin:0 auto;padding:0 28px 70px;width:100%}
.fg-kick{display:inline-block;font-family:Oswald,sans-serif;text-transform:uppercase;letter-spacing:.26em;
  font-size:.76rem;color:var(--acc);border-left:3px solid var(--acc);padding-left:12px;margin-bottom:20px}
.fg-hero h1{max-width:16ch}
.fg-hero p{max-width:52ch;color:#c3cad4;margin:18px 0 28px;font-size:1.06rem}
.fg-acts{display:flex;gap:14px;flex-wrap:wrap}
.fg-btn{display:inline-block;padding:15px 30px;background:var(--acc);color:__ONACCENT__;text-decoration:none;
  font-family:Oswald,sans-serif;text-transform:uppercase;letter-spacing:.08em}
.fg-btn--ghost{background:none;border:1px solid #55606f;color:#e8ebef}
.fg-rail{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);background:var(--steel2)}
.fg-rail div{padding:26px 28px;border-right:1px solid var(--line)}
.fg-rail div:last-child{border-right:0}
.fg-rail b{display:block;font-family:Oswald,sans-serif;font-size:1.05rem;text-transform:uppercase;color:var(--acc)}
.fg-rail span{font-size:.9rem;color:var(--dim)}
/* blocks */
.hb--svc,.hb--areas{background:var(--steel2)}
.hb-eyebrow{color:var(--acc)}
.hb-svc,.hb-guide{background:var(--steel);border:1px solid var(--line);transition:border-color .2s,transform .2s}
.hb-svc:hover,.hb-guide:hover{border-color:var(--acc);transform:translateY(-3px)}
.hb-more{color:var(--acc)}
.hb-step__n{background:var(--acc);color:__ONACCENT__;border-radius:0;font-family:Oswald,sans-serif}
.hb-areas a{background:var(--steel);border:1px solid var(--line)}
.hb-areas a:hover{border-color:var(--acc)}
.hb-faq{border-bottom:1px solid var(--line)}
.hb--cta{background:var(--acc);color:__ONACCENT__}
.hb--cta .hb-cta__btn{background:#0e1116;color:#fff}
.hb--cta .hb-cta__btn--alt{background:none;border:1px solid rgba(255,255,255,.55);color:__ONACCENT__}
/* inner */
.pg-hero{background:var(--steel2);border-bottom:1px solid var(--line)}
.pg-crumb{color:var(--dim)}.pg-crumb a:hover{color:var(--acc)}
.pg-body p,.pg-body li{color:#c3cad4}
.pg-body details{border-bottom:1px solid var(--line)}
.pg-aside{background:var(--steel2);border:1px solid var(--line)}
.pg-tel{color:var(--acc)}
.pg-row{border-bottom:1px solid var(--line)}
.pg-row:hover h2{color:var(--acc)}
.pg-row__n{font-family:Oswald,sans-serif;color:var(--acc)}
@media(max-width:900px){.fg-rail{grid-template-columns:1fr 1fr}}
"""

def forge_home(t, pages):
    e = H.esc
    h1, lead, faqs, top = _home_head(t, pages, FORGE_FONTS, "Request a Quote")
    call = _tel(t, label=f'Call {e(t["phone"])}', cls="fg-btn") or ""
    rail = "".join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in [
        ("Same-day", "on most repair calls"), ("Written price", "before work starts"),
        ("Springs & openers", "the two most common failures"), (f"{e(t['city'])} metro", "and the surrounding suburbs")])
    return (top
            + f'<section class="fg-hero"><img src="{PHOTOS}{_hero(t)}" alt="{e(t["city"])} garage door" '
              f'width="1600" height="900" fetchpriority="high" decoding="async">'
              f'<div class="fg-hero__in"><span class="fg-kick">Repair · Install · Service</span>'
              f'<h1>{e(h1)}</h1><p>{e(lead)}</p>'
              f'<div class="fg-acts">{call}<a class="fg-btn fg-btn--ghost" href="/services/">See what we fix</a></div>'
              f'</div></section>'
            + f'<div class="fg-rail">{rail}</div>'
            + hb_stack(t, pages, faqs, pin=("stats", "emergency"))
            + _chrome_footer(t, pages) + "</body></html>")


# ---------------------------------------------------------------- COASTLINE
# airy editorial: white, wide margins, high-contrast serif display, thin rules
COAST_FONTS = "family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Karla:wght@400;500;700"
COAST_CSS = r"""
:root{--p:__P__;--acc:__ACCENT__;--ink:#1a1f26;--soft:#5d6672;--line:#e3e7ec;--wash:#f7f8fa}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Karla,sans-serif;background:#fff;color:var(--ink);line-height:1.72}
h1,h2,h3{font-family:Fraunces,Georgia,serif;font-weight:600;line-height:1.14;letter-spacing:-.015em}
h1{font-size:clamp(2.3rem,4.6vw,3.7rem)}h2{font-size:clamp(1.7rem,3vw,2.4rem)}
a{color:inherit}img{display:block;max-width:100%}
.tc-bar{background:rgba(255,255,255,.93);border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}
.tc-inner{padding:18px 28px}
.tc-trigger,.tc-link,.tc-msum{font-size:.9rem}
.tc-trigger:hover,.tc-link:hover{color:var(--p)}
.tc-drop,.tc-mobile{background:#fff;border:1px solid var(--line);box-shadow:0 20px 44px rgba(26,31,38,.10)}
.tc-drop a:hover{background:var(--wash);color:var(--p)}
.tc-drop a:first-child{color:var(--p);font-weight:700;border-bottom:1px solid var(--line);margin-bottom:6px}
.tc-tel{font-family:Fraunces,serif;font-size:1.1rem;color:var(--p)}
.tc-cta,.hb-cta__btn,.pg-btn{background:var(--p);color:#fff;border-radius:2px;font-weight:700}
.tc-msum,.tc-mlink{border-bottom:1px solid var(--line)}
.tc-foot{background:var(--wash);border-top:1px solid var(--line)}
.tc-fcol h3{font-family:Karla,sans-serif;font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--soft)}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:var(--soft);font-size:.93rem}
.tc-fcol a:hover{color:var(--p)}
.tc-flegal{border-top:1px solid var(--line);color:var(--soft);font-size:.84rem}
/* hero */
.cs-hero{max-width:1180px;margin:0 auto;padding:74px 28px 40px;display:grid;
  grid-template-columns:1.05fr .95fr;gap:64px;align-items:center}
.cs-kick{font-size:.74rem;letter-spacing:.24em;text-transform:uppercase;color:var(--acc);margin-bottom:18px}
.cs-hero p{color:var(--soft);font-size:1.1rem;margin:20px 0 30px;max-width:46ch}
.cs-acts{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.cs-btn{display:inline-block;padding:15px 30px;background:var(--p);color:#fff;text-decoration:none;
  border-radius:2px;font-weight:700}
.cs-link{text-decoration:none;border-bottom:1px solid var(--acc);padding-bottom:3px;font-weight:700}
.cs-hero__img{position:relative}
.cs-hero__img img{width:100%;height:520px;object-fit:cover;border-radius:2px}
.cs-strip{border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-top:34px}
.cs-strip div{max-width:1180px;margin:0 auto;padding:22px 28px;display:flex;gap:44px;flex-wrap:wrap;
  font-size:.88rem;color:var(--soft)}
.cs-strip b{color:var(--ink)}
/* blocks */
.hb-eyebrow{color:var(--acc)}
.hb--svc,.hb--faq{background:var(--wash)}
.hb-svc,.hb-guide{background:#fff;border:1px solid var(--line);border-radius:3px}
.hb-svc:hover,.hb-guide:hover{border-color:var(--p)}
.hb-svc h3,.hb-guide h3{font-size:1.25rem}
.hb-more{color:var(--p)}
.hb-step__n{background:var(--p);color:#fff}
.hb-areas a{border:1px solid var(--line);border-radius:2px}
.hb-areas a:hover{border-color:var(--p);color:var(--p)}
.hb-faq{border-bottom:1px solid var(--line)}
.hb--cta{background:var(--p);color:#fff}
.hb--cta .hb-cta__btn{background:#fff;color:var(--p)}
.hb--cta .hb-cta__btn--alt{background:none;border:1px solid rgba(255,255,255,.6);color:#fff}
/* inner */
.pg-hero{border-bottom:1px solid var(--line)}
.pg-crumb{color:var(--soft)}
.pg-body p,.pg-body li{color:#3f4854}
.pg-body img{border-radius:2px}
.pg-body details{border-bottom:1px solid var(--line)}
.pg-aside{background:var(--wash);border:1px solid var(--line);border-radius:3px}
.pg-tel{color:var(--p);font-family:Fraunces,serif}
.pg-row{border-bottom:1px solid var(--line)}
.pg-row:hover h2{color:var(--p)}
.pg-row__n{color:var(--acc);font-family:Fraunces,serif}
@media(max-width:900px){.cs-hero{grid-template-columns:1fr;gap:34px;padding-top:44px}
 .cs-hero__img img{height:300px}}
"""

def coast_home(t, pages):
    e = H.esc
    h1, lead, faqs, top = _home_head(t, pages, COAST_FONTS, "Request a Quote")
    call = _tel(t, label=f'Call {e(t["phone"])}', cls="cs-btn") or \
        '<a class="cs-btn" href="/request-a-quote/">Request a quote</a>'
    return (top
            + f'<section class="cs-hero"><div><p class="cs-kick">Garage doors · {e(t["city"])}, {e(t["st"])}</p>'
              f'<h1>{e(h1)}</h1><p>{e(lead)}</p>'
              f'<div class="cs-acts">{call}<a class="cs-link" href="/services/">See what we fix</a></div></div>'
              f'<div class="cs-hero__img"><img src="{PHOTOS}{_hero(t)}" alt="{e(t["city"])} garage door" '
              f'width="1200" height="900" fetchpriority="high" decoding="async"></div></section>'
            + f'<div class="cs-strip"><div><span><b>Same-day</b> on most repairs</span>'
              f'<span><b>Written</b> prices, not ranges</span>'
              f'<span><b>Springs, openers, panels</b> and full replacements</span></div></div>'
            + hb_stack(t, pages, faqs, pin=("about", "guides"))
            + _chrome_footer(t, pages) + "</body></html>")


# ---------------------------------------------------------------- BEACON
# colour-block: flat brand panels, oversized display type, no hero photograph
BEACON_FONTS = "family=Anton&family=Inter:wght@400;500;600;800"
BEACON_CSS = r"""
:root{--p:__P__;--pd:__PD__;--acc:__ACCENT__;--ink:#15181d;--soft:#59616d;--line:#e6e9ee}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Inter,sans-serif;background:#fff;color:var(--ink);line-height:1.66}
h1,h2,h3{font-family:Anton,Impact,sans-serif;font-weight:400;text-transform:uppercase;
  letter-spacing:.005em;line-height:.98}
h1{font-size:clamp(2.8rem,7vw,5.6rem)}h2{font-size:clamp(2rem,4.2vw,3.2rem)}
h3{font-size:1.2rem;letter-spacing:.02em}
a{color:inherit}img{display:block;max-width:100%}
.tc-bar{background:var(--p);color:#fff}
.tc-brand__txt{font-family:Anton,sans-serif;text-transform:uppercase;font-size:1.3rem}
.tc-trigger,.tc-link,.tc-msum{font-weight:600;font-size:.9rem}
.tc-drop{background:var(--pd);border:0}
.tc-drop a:hover{background:rgba(255,255,255,.12)}
.tc-drop a:first-child{color:var(--acc);font-weight:800;border-bottom:1px solid rgba(255,255,255,.2);margin-bottom:6px}
.tc-tel{font-weight:800}
.tc-cta{background:var(--acc);color:__ONACCENT__;font-weight:800}
.tc-mobile{background:var(--pd);color:#fff}
.tc-msum,.tc-mlink{border-bottom:1px solid rgba(255,255,255,.16)}
.tc-mcta{background:var(--acc);color:__ONACCENT__;font-weight:800}
.tc-foot{background:var(--ink);color:#fff}
.tc-fcol h3{font-family:Inter,sans-serif;font-size:.72rem;letter-spacing:.2em;color:var(--acc);font-weight:800}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:#aeb5c0;font-size:.93rem}
.tc-fcol a:hover{color:#fff}
.tc-flegal{border-top:1px solid #2b3038;color:#7d8592;font-size:.82rem}
/* hero: flat colour, no photo */
.bc-hero{background:var(--p);color:#fff;padding:86px 0 76px}
.bc-in{max-width:1180px;margin:0 auto;padding:0 28px}
.bc-kick{display:inline-block;background:var(--acc);color:__ONACCENT__;font-weight:800;font-size:.74rem;
  letter-spacing:.18em;text-transform:uppercase;padding:7px 14px;margin-bottom:24px}
.bc-hero h1{max-width:15ch}
.bc-hero p{max-width:50ch;margin:22px 0 32px;font-size:1.1rem;color:rgba(255,255,255,.86)}
.bc-acts{display:flex;gap:14px;flex-wrap:wrap}
.bc-btn{display:inline-block;padding:16px 32px;background:#fff;color:var(--p);text-decoration:none;font-weight:800}
.bc-btn--alt{background:none;border:2px solid rgba(255,255,255,.6);color:#fff}
.bc-band{background:var(--acc);color:__ONACCENT__}
.bc-band div{max-width:1180px;margin:0 auto;padding:20px 28px;display:flex;gap:40px;flex-wrap:wrap;font-weight:700}
/* blocks */
.hb-eyebrow{color:var(--acc);font-weight:800}
.hb--svc{background:#f5f7fa}
.hb-svc{background:#fff;border-bottom:5px solid var(--p)}
.hb-svc:hover{border-bottom-color:var(--acc)}
.hb-guide{background:#f5f7fa;border-left:5px solid var(--acc)}
.hb-more{color:var(--p);font-weight:800}
.hb--steps{background:var(--ink);color:#fff}
.hb--steps .hb-step p{color:#aeb5c0;opacity:1}
.hb-step__n{background:var(--acc);color:__ONACCENT__;border-radius:0;font-family:Anton,sans-serif;font-size:1.2rem}
.hb-sig{border-top:4px solid var(--p);padding-top:16px}
.hb-areas a{background:#f5f7fa;font-weight:600}
.hb-areas a:hover{background:var(--p);color:#fff}
.hb-faq{border-bottom:2px solid var(--line)}
.hb--cta{background:var(--p);color:#fff}
.hb--cta .hb-cta__btn{background:var(--acc);color:__ONACCENT__}
.hb--cta .hb-cta__btn--alt{background:#fff;color:var(--p)}
/* inner */
.pg-hero{background:var(--p);color:#fff;padding:60px 0 52px}
.pg-crumb{color:rgba(255,255,255,.78)}
.pg-body p,.pg-body li{color:#3c444f}
.pg-body details{border-bottom:2px solid var(--line)}
.pg-aside{background:#f5f7fa;border-top:5px solid var(--acc)}
.pg-tel{color:var(--p)}
.pg-row{border-bottom:2px solid var(--line)}
.pg-row:hover h2{color:var(--p)}
.pg-row__n{font-family:Anton,sans-serif;color:var(--acc);font-size:1.3rem}
"""

def beacon_home(t, pages):
    e = H.esc
    h1, lead, faqs, top = _home_head(t, pages, BEACON_FONTS, "Free Quote")
    call = _tel(t, label=f'Call {e(t["phone"])}', cls="bc-btn") or ""
    return (top
            + f'<section class="bc-hero"><div class="bc-in"><span class="bc-kick">{e(t["city"])}, {e(t["st"])}</span>'
              f'<h1>{e(h1)}</h1><p>{e(lead)}</p><div class="bc-acts">{call}'
              f'<a class="bc-btn bc-btn--alt" href="/request-a-quote/">Get a free quote</a></div></div></section>'
            + f'<div class="bc-band"><div><span>Same-day on most repairs</span>'
              f'<span>Written prices</span><span>Springs · Openers · Panels · New doors</span></div></div>'
            + hb_stack(t, pages, faqs, pin=("symptoms", "stats"))
            + _chrome_footer(t, pages) + "</body></html>")


# ---------------------------------------------------------------- ATLAS
# corporate technical: slab headings, dense grid, tabular rhythm, navy + steel
ATLAS_FONTS = "family=Roboto+Slab:wght@400;600;700&family=Roboto:wght@400;500;700"
ATLAS_CSS = r"""
:root{--p:__P__;--pd:__PD__;--acc:__ACCENT__;--ink:#1b2027;--soft:#5a6470;--line:#dde2e8;--wash:#f4f6f9}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Roboto,Arial,sans-serif;background:#fff;color:var(--ink);line-height:1.62}
h1,h2,h3{font-family:"Roboto Slab",Georgia,serif;font-weight:700;line-height:1.16}
h1{font-size:clamp(2rem,3.8vw,3rem)}h2{font-size:clamp(1.6rem,2.6vw,2.1rem)}
a{color:inherit}img{display:block;max-width:100%}
.tc-bar{background:#fff;border-bottom:3px solid var(--p)}
.tc-inner{padding:12px 28px}
.tc-trigger,.tc-link,.tc-msum{font-size:.88rem;font-weight:500}
.tc-trigger:hover,.tc-link:hover{color:var(--p)}
.tc-drop,.tc-mobile{background:#fff;border:1px solid var(--line);box-shadow:0 16px 34px rgba(27,32,39,.14)}
.tc-drop a:hover{background:var(--wash);color:var(--p)}
.tc-drop a:first-child{color:var(--p);font-weight:700;border-bottom:1px solid var(--line);margin-bottom:6px}
.tc-tel{font-family:"Roboto Slab",serif;font-weight:700;color:var(--p)}
.tc-cta,.hb-cta__btn,.pg-btn{background:var(--p);color:#fff;border-radius:3px;font-weight:700}
.tc-msum,.tc-mlink{border-bottom:1px solid var(--line)}
.tc-foot{background:var(--pd);color:#fff}
.tc-fcol h3{font-family:Roboto,sans-serif;font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--acc)}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:#b3bcc7;font-size:.92rem}
.tc-fcol a:hover{color:#fff}
.tc-flegal{border-top:1px solid rgba(255,255,255,.16);color:#8d97a4;font-size:.82rem}
/* hero */
.at-hero{background:var(--wash);border-bottom:1px solid var(--line)}
.at-in{max-width:1180px;margin:0 auto;padding:52px 28px;display:grid;grid-template-columns:1.25fr .75fr;gap:48px;align-items:center}
.at-kick{font-size:.74rem;letter-spacing:.18em;text-transform:uppercase;color:var(--p);font-weight:700;margin-bottom:14px}
.at-hero p{color:var(--soft);margin:16px 0 26px;max-width:52ch}
.at-acts{display:flex;gap:12px;flex-wrap:wrap}
.at-btn{display:inline-block;padding:14px 26px;background:var(--p);color:#fff;text-decoration:none;
  border-radius:3px;font-weight:700}
.at-btn--alt{background:#fff;color:var(--p);border:1px solid var(--p)}
.at-spec{background:#fff;border:1px solid var(--line);border-radius:3px;overflow:hidden}
.at-spec h2{font-size:.82rem;letter-spacing:.14em;text-transform:uppercase;font-family:Roboto,sans-serif;
  background:var(--p);color:#fff;margin:0;padding:12px 18px}
.at-spec dl{margin:0;display:grid;grid-template-columns:auto 1fr}
.at-spec dt{padding:11px 18px;border-bottom:1px solid var(--line);font-weight:500;color:var(--soft);font-size:.88rem}
.at-spec dd{padding:11px 18px;border-bottom:1px solid var(--line);margin:0;text-align:right;font-weight:700;font-size:.88rem}
.at-spec dl>:nth-last-child(-n+2){border-bottom:0}
/* blocks */
.hb-eyebrow{color:var(--p);font-weight:700}
.hb--svc,.hb--faq{background:var(--wash)}
.hb-svc,.hb-guide{background:#fff;border:1px solid var(--line);border-radius:3px}
.hb-svc:hover,.hb-guide:hover{border-color:var(--p);box-shadow:0 10px 26px rgba(27,32,39,.10)}
.hb-more{color:var(--p);font-weight:700}
.hb-step__n{background:var(--p);color:#fff;border-radius:3px}
.hb-sig{background:#fff;border:1px solid var(--line);border-radius:3px;padding:20px}
.hb-areas a{border:1px solid var(--line);border-radius:3px;font-size:.92rem}
.hb-areas a:hover{border-color:var(--p);color:var(--p)}
.hb-faq{border-bottom:1px solid var(--line)}
.hb--cta{background:var(--pd);color:#fff}
.hb--cta .hb-cta__btn{background:var(--acc);color:__ONACCENT__}
.hb--cta .hb-cta__btn--alt{background:none;border:1px solid rgba(255,255,255,.5);color:#fff}
/* inner */
.pg-hero{background:var(--wash);border-bottom:1px solid var(--line)}
.pg-crumb{color:var(--soft)}
.pg-body p,.pg-body li{color:#404a56}
.pg-body details{border-bottom:1px solid var(--line)}
.pg-aside{background:var(--wash);border:1px solid var(--line);border-radius:3px}
.pg-tel{color:var(--p);font-family:"Roboto Slab",serif}
.pg-row{border-bottom:1px solid var(--line)}
.pg-row:hover h2{color:var(--p)}
.pg-row__n{color:var(--acc);font-family:"Roboto Slab",serif}
@media(max-width:900px){.at-in{grid-template-columns:1fr;gap:28px}}
"""

def atlas_home(t, pages):
    e = H.esc
    h1, lead, faqs, top = _home_head(t, pages, ATLAS_FONTS, "Request a Quote")
    call = _tel(t, label=f'Call {e(t["phone"])}', cls="at-btn") or ""
    spec = "".join(f'<dt>{a}</dt><dd>{b}</dd>' for a, b in [
        ("Service area", f'{e(t["city"])}, {e(t["st"])}'),
        ("Response", "Same-day on most repairs"),
        ("Pricing", "Written, before work starts"),
        ("Common jobs", "Springs, cables, openers, panels"),
        ("Installation", "Insulated and non-insulated doors")])
    return (top
            + f'<section class="at-hero"><div class="at-in"><div>'
              f'<p class="at-kick">Garage door repair &amp; installation</p><h1>{e(h1)}</h1>'
              f'<p>{e(lead)}</p><div class="at-acts">{call}'
              f'<a class="at-btn at-btn--alt" href="/services/">Browse services</a></div></div>'
              f'<div class="at-spec"><h2>At a glance</h2><dl>{spec}</dl></div></div></section>'
            + hb_stack(t, pages, faqs, pin=("stats", "rvr"))
            + _chrome_footer(t, pages) + "</body></html>")


# ---------------------------------------------------------------- HEARTH
# warm residential: cream ground, soft rounded photo cards, friendly serif
HEARTH_FONTS = "family=Bitter:wght@500;600;700&family=Nunito+Sans:wght@400;600;700"
HEARTH_CSS = r"""
:root{--p:__P__;--acc:__ACCENT__;--ink:#2c2622;--soft:#6f6459;--cream:#faf6f0;--card:#fff;--line:#e8ded1}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"Nunito Sans",sans-serif;background:var(--cream);color:var(--ink);line-height:1.7}
h1,h2,h3{font-family:Bitter,Georgia,serif;font-weight:600;line-height:1.2}
h1{font-size:clamp(2.1rem,4.4vw,3.4rem)}h2{font-size:clamp(1.6rem,2.9vw,2.3rem)}
a{color:inherit}img{display:block;max-width:100%}
.tc-bar{background:rgba(250,246,240,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}
.tc-trigger,.tc-link,.tc-msum{font-weight:600;font-size:.92rem;border-radius:12px}
.tc-trigger:hover,.tc-link:hover{background:#f1e7da}
.tc-drop,.tc-mobile{background:var(--card);border:1px solid var(--line);border-radius:18px;
  box-shadow:0 18px 38px rgba(44,38,34,.12)}
.tc-drop a{border-radius:10px}
.tc-drop a:hover{background:#f6ede1;color:var(--p)}
.tc-drop a:first-child{color:var(--p);font-weight:700}
.tc-tel{font-family:Bitter,serif;font-weight:700;color:var(--p)}
.tc-cta,.hb-cta__btn,.pg-btn{background:var(--p);color:#fff;border-radius:999px;font-weight:700}
.tc-msum,.tc-mlink{border-bottom:1px solid var(--line)}
.tc-foot{background:#f1e7da;border-top:1px solid var(--line)}
.tc-fcol h3{font-family:Bitter,serif;font-size:1rem}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:var(--soft);font-size:.93rem}
.tc-fcol a:hover{color:var(--p)}
.tc-flegal{border-top:1px solid var(--line);color:var(--soft);font-size:.85rem}
/* hero */
.ht-hero{max-width:1180px;margin:0 auto;padding:60px 28px 26px}
.ht-card{background:var(--card);border:1px solid var(--line);border-radius:34px;overflow:hidden;
  display:grid;grid-template-columns:1fr 1fr;box-shadow:0 22px 50px rgba(44,38,34,.09)}
.ht-card__txt{padding:52px 46px}
.ht-kick{display:inline-block;background:#f6ede1;color:var(--p);border-radius:999px;padding:7px 16px;
  font-size:.76rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:18px}
.ht-card p{color:var(--soft);margin:16px 0 28px}
.ht-acts{display:flex;gap:12px;flex-wrap:wrap}
.ht-btn{display:inline-block;padding:14px 28px;background:var(--p);color:#fff;text-decoration:none;
  border-radius:999px;font-weight:700}
.ht-btn--alt{background:#f6ede1;color:var(--p)}
.ht-card__img img{width:100%;height:100%;min-height:380px;object-fit:cover}
/* blocks */
.hb-eyebrow{color:var(--acc);font-weight:700}
.hb-svc,.hb-guide{background:var(--card);border:1px solid var(--line);border-radius:24px}
.hb-svc:hover,.hb-guide:hover{box-shadow:0 16px 34px rgba(44,38,34,.10);transform:translateY(-3px)}
.hb-svc,.hb-guide{transition:transform .2s,box-shadow .2s}
.hb-more{color:var(--p);font-weight:700}
.hb--steps{background:#f4ebdf}
.hb-step__n{background:var(--p);color:#fff}
.hb-sig{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:22px}
.hb-areas a{background:var(--card);border:1px solid var(--line);border-radius:999px;text-align:center;font-weight:600}
.hb-areas a:hover{background:var(--p);color:#fff;border-color:var(--p)}
.hb-faq{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px 22px;margin-bottom:10px}
.hb--cta{background:var(--p);color:#fff}
.hb--cta .hb-cta__btn{background:#fff;color:var(--p)}
.hb--cta .hb-cta__btn--alt{background:rgba(255,255,255,.16);color:#fff}
/* inner */
.pg-hero{padding-top:44px}
.pg-crumb{color:var(--soft)}
.pg-body{background:var(--card);border:1px solid var(--line);border-radius:26px;padding:34px;max-width:none}
.pg-body img{border-radius:18px}
.pg-body p,.pg-body li{color:#4d453d}
.pg-body details{border-bottom:1px solid var(--line)}
.pg-aside{background:var(--card);border:1px solid var(--line);border-radius:24px}
.pg-tel{color:var(--p);font-family:Bitter,serif}
.pg-row{background:var(--card);border:1px solid var(--line);border-radius:20px;margin-bottom:12px;padding:24px 26px}
.pg-row:hover{border-color:var(--p)}
.pg-row__n{color:var(--acc);font-family:Bitter,serif}
@media(max-width:900px){.ht-card{grid-template-columns:1fr}.ht-card__txt{padding:36px 26px}
 .ht-card__img img{min-height:240px}}
"""

def hearth_home(t, pages):
    e = H.esc
    h1, lead, faqs, top = _home_head(t, pages, HEARTH_FONTS, "Book a visit")
    call = _tel(t, label=f'Call {e(t["phone"])}', cls="ht-btn") or ""
    return (top
            + f'<section class="ht-hero"><div class="ht-card"><div class="ht-card__txt">'
              f'<span class="ht-kick">{e(t["city"])}, {e(t["st"])}</span><h1>{e(h1)}</h1>'
              f'<p>{e(lead)}</p><div class="ht-acts">{call}'
              f'<a class="ht-btn ht-btn--alt" href="/request-a-quote/">Book a visit</a></div></div>'
              f'<div class="ht-card__img"><img src="{PHOTOS}{_hero(t)}" alt="{e(t["city"])} garage door" '
              f'width="1200" height="900" fetchpriority="high" decoding="async"></div></div></section>'
            + hb_stack(t, pages, faqs, pin=("about", "tips"))
            + _chrome_footer(t, pages) + "</body></html>")


# ---------------------------------------------------------------- QUARRY
# utility / brutalist: hard black rules, mono labels, no shadows, type-led hero
QUARRY_FONTS = "family=Space+Grotesk:wght@500;700&family=IBM+Plex+Mono:wght@400;600"
QUARRY_CSS = r"""
:root{--p:__P__;--acc:__ACCENT__;--ink:#0f0f10;--soft:#4a4a4f;--line:#0f0f10;--wash:#f2f2ef}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"Space Grotesk",sans-serif;background:#fdfdfb;color:var(--ink);line-height:1.6}
h1,h2,h3{font-family:"Space Grotesk",sans-serif;font-weight:700;line-height:1.06;letter-spacing:-.02em}
h1{font-size:clamp(2.6rem,6vw,4.8rem)}h2{font-size:clamp(1.8rem,3.6vw,2.8rem)}
a{color:inherit}img{display:block;max-width:100%}
.mono{font-family:"IBM Plex Mono",monospace;font-size:.74rem;letter-spacing:.1em;text-transform:uppercase}
.tc-bar{background:#fdfdfb;border-bottom:2px solid var(--ink)}
.tc-trigger,.tc-link,.tc-msum{font-family:"IBM Plex Mono",monospace;font-size:.76rem;letter-spacing:.1em;text-transform:uppercase}
.tc-trigger:hover,.tc-link:hover{background:var(--ink);color:#fdfdfb}
.tc-drop,.tc-mobile{background:#fdfdfb;border:2px solid var(--ink);padding:0}
.tc-drop a{border-bottom:1px solid #dcdcd6;font-family:"IBM Plex Mono",monospace;font-size:.78rem}
.tc-drop a:last-child{border-bottom:0}
.tc-drop a:hover{background:var(--acc);color:__ONACCENT__}
.tc-drop a:first-child{font-weight:600;background:var(--wash)}
.tc-tel{font-family:"IBM Plex Mono",monospace;font-weight:600}
.tc-cta,.hb-cta__btn,.pg-btn{background:var(--ink);color:#fdfdfb;border-radius:0;
  font-family:"IBM Plex Mono",monospace;font-size:.76rem;letter-spacing:.1em;text-transform:uppercase}
.tc-msum,.tc-mlink{border-bottom:2px solid var(--ink)}
.tc-foot{background:var(--ink);color:#fdfdfb}
.tc-fcol h3{font-family:"IBM Plex Mono",monospace;font-size:.72rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--acc)}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:#b6b6b0;font-size:.9rem}
.tc-fcol a:hover{color:#fff}
.tc-flegal{border-top:1px solid #35353a;color:#87878230;color:#878782;font-family:"IBM Plex Mono",monospace;font-size:.72rem}
/* hero: type-led, photo as a bordered slab underneath */
.qy-hero{max-width:1180px;margin:0 auto;padding:70px 28px 0}
.qy-hero h1{max-width:14ch;margin:18px 0}
.qy-meta{display:flex;gap:26px;flex-wrap:wrap;border-top:2px solid var(--ink);border-bottom:2px solid var(--ink);
  padding:14px 0;margin:30px 0 0}
.qy-hero p{max-width:54ch;color:var(--soft);font-size:1.06rem;margin-bottom:26px}
.qy-acts{display:flex;gap:0;flex-wrap:wrap;margin-bottom:34px}
.qy-btn{display:inline-block;padding:16px 30px;background:var(--ink);color:#fdfdfb;text-decoration:none;
  font-family:"IBM Plex Mono",monospace;font-size:.76rem;letter-spacing:.1em;text-transform:uppercase;
  border:2px solid var(--ink)}
.qy-btn--alt{background:#fdfdfb;color:var(--ink)}
.qy-slab{border:2px solid var(--ink);overflow:hidden}
.qy-slab img{width:100%;height:min(52vh,440px);object-fit:cover;filter:grayscale(.25)}
/* blocks */
.hb-eyebrow{font-family:"IBM Plex Mono",monospace;color:var(--ink)}
.hb--svc{background:var(--wash);border-top:2px solid var(--ink);border-bottom:2px solid var(--ink)}
.hb-svc,.hb-guide{background:#fdfdfb;border:2px solid var(--ink)}
.hb-svc:hover,.hb-guide:hover{background:var(--acc);color:__ONACCENT__}
.hb-svc:hover .hb-more,.hb-guide:hover p{color:inherit}
.hb-more{font-family:"IBM Plex Mono",monospace;font-size:.76rem;letter-spacing:.1em;text-transform:uppercase}
.hb-step__n{background:var(--ink);color:#fdfdfb;border-radius:0;font-family:"IBM Plex Mono",monospace}
.hb-sig{border-left:2px solid var(--ink);padding-left:18px}
.hb-areas a{border:2px solid var(--ink);font-family:"IBM Plex Mono",monospace;font-size:.76rem;
  letter-spacing:.06em;text-transform:uppercase}
.hb-areas a:hover{background:var(--ink);color:#fdfdfb}
.hb-faq{border-bottom:2px solid var(--ink)}
.hb--cta{background:var(--ink);color:#fdfdfb;border-top:2px solid var(--ink)}
.hb--cta .hb-cta__btn{background:var(--acc);color:__ONACCENT__;border:2px solid var(--acc)}
.hb--cta .hb-cta__btn--alt{background:none;border:2px solid #fdfdfb;color:#fdfdfb}
/* inner */
.pg-hero{border-bottom:2px solid var(--ink)}
.pg-crumb{font-family:"IBM Plex Mono",monospace;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase}
.pg-body p,.pg-body li{color:#3a3a3f}
.pg-body img{border:2px solid var(--ink)}
.pg-body details{border-bottom:2px solid var(--ink)}
.pg-aside{border:2px solid var(--ink);background:var(--wash)}
.pg-tel{font-family:"IBM Plex Mono",monospace}
.pg-row{border-bottom:2px solid var(--ink)}
.pg-row:hover{background:var(--wash)}
.pg-row__n{font-family:"IBM Plex Mono",monospace;color:var(--acc)}
"""

def quarry_home(t, pages):
    e = H.esc
    h1, lead, faqs, top = _home_head(t, pages, QUARRY_FONTS, "Get a quote")
    call = _tel(t, label=f'Call {e(t["phone"])}', cls="qy-btn") or ""
    meta = "".join(f'<span class="mono">{m}</span>' for m in [
        f'{e(t["city"])}, {e(t["st"])}', "Repair / Install / Service",
        "Same-day on most repairs", "Written pricing"])
    return (top
            + f'<section class="qy-hero"><span class="mono">Garage door specialists</span>'
              f'<h1>{e(h1)}</h1><p>{e(lead)}</p>'
              f'<div class="qy-acts">{call}<a class="qy-btn qy-btn--alt" href="/services/">What we fix</a></div>'
              f'<div class="qy-slab"><img src="{PHOTOS}{_hero(t)}" alt="{e(t["city"])} garage door" '
              f'width="1600" height="900" fetchpriority="high" decoding="async"></div>'
              f'<div class="qy-meta">{meta}</div></section>'
            + hb_stack(t, pages, faqs, pin=("symptoms", "safety"))
            + _chrome_footer(t, pages) + "</body></html>")


# ---------------------------------------------------------------- VERDANT
# fresh geometric: off-white ground, deep brand panels, pill accents, wide photo band
VERDANT_FONTS = "family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600"
VERDANT_CSS = r"""
:root{--p:__P__;--pd:__PD__;--acc:__ACCENT__;--ink:#191d24;--soft:#5b6470;--line:#e4e8ec;--wash:#f6f8f7}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Inter,sans-serif;background:#fbfcfb;color:var(--ink);line-height:1.68}
h1,h2,h3{font-family:Sora,sans-serif;font-weight:700;line-height:1.14;letter-spacing:-.02em}
h1{font-size:clamp(2.2rem,4.8vw,3.6rem)}h2{font-size:clamp(1.7rem,3vw,2.4rem)}
a{color:inherit}img{display:block;max-width:100%}
.tc-bar{background:rgba(251,252,251,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}
.tc-brand__txt{font-family:Sora,sans-serif;font-weight:700}
.tc-trigger,.tc-link,.tc-msum{font-weight:500;font-size:.92rem;border-radius:999px}
.tc-trigger:hover,.tc-link:hover{background:var(--wash);color:var(--p)}
.tc-drop,.tc-mobile{background:#fff;border:1px solid var(--line);border-radius:20px;
  box-shadow:0 20px 44px rgba(25,29,36,.12)}
.tc-drop a{border-radius:12px}
.tc-drop a:hover{background:var(--wash);color:var(--p)}
.tc-drop a:first-child{color:var(--p);font-weight:700}
.tc-tel{font-family:Sora,sans-serif;font-weight:700;color:var(--p)}
.tc-cta,.hb-cta__btn,.pg-btn{background:var(--p);color:#fff;border-radius:999px;font-weight:600}
.tc-msum,.tc-mlink{border-bottom:1px solid var(--line)}
.tc-foot{background:var(--pd);color:#fff}
.tc-fcol h3{font-family:Sora,sans-serif;font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;color:var(--acc)}
.tc-fcol a,.tc-fbrand p,.tc-fbrand address{color:#b8c0ca;font-size:.93rem}
.tc-fcol a:hover{color:#fff}
.tc-flegal{border-top:1px solid rgba(255,255,255,.14);color:#8f99a5;font-size:.84rem}
/* hero: centred type over a full-width photo band */
.vd-hero{text-align:center;padding:74px 28px 0;max-width:900px;margin:0 auto}
.vd-kick{display:inline-block;background:var(--wash);border:1px solid var(--line);border-radius:999px;
  padding:8px 18px;font-size:.78rem;font-weight:600;color:var(--p);margin-bottom:22px}
.vd-hero p{color:var(--soft);font-size:1.12rem;margin:20px auto 30px;max-width:56ch}
.vd-acts{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:52px}
.vd-btn{display:inline-block;padding:15px 30px;background:var(--p);color:#fff;text-decoration:none;
  border-radius:999px;font-weight:600}
.vd-btn--alt{background:#fff;color:var(--p);border:1px solid var(--line)}
.vd-band{max-width:1320px;margin:0 auto;padding:0 28px}
.vd-band img{width:100%;height:min(48vh,420px);object-fit:cover;border-radius:28px}
.vd-pills{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;padding:30px 28px 0}
.vd-pills span{background:var(--wash);border:1px solid var(--line);border-radius:999px;padding:9px 18px;
  font-size:.86rem;font-weight:600;color:var(--soft)}
/* blocks */
.hb-eyebrow{color:var(--acc);font-weight:700}
.hb--svc,.hb--faq{background:var(--wash)}
.hb-svc,.hb-guide{background:#fff;border:1px solid var(--line);border-radius:22px;transition:transform .2s,box-shadow .2s}
.hb-svc:hover,.hb-guide:hover{transform:translateY(-4px);box-shadow:0 18px 38px rgba(25,29,36,.10)}
.hb-more{color:var(--p);font-weight:600}
.hb-step__n{background:var(--p);color:#fff}
.hb-sig{background:#fff;border:1px solid var(--line);border-radius:20px;padding:22px}
.hb-areas a{background:#fff;border:1px solid var(--line);border-radius:999px;text-align:center;font-weight:500}
.hb-areas a:hover{border-color:var(--p);color:var(--p)}
.hb-faq{border-bottom:1px solid var(--line)}
.hb--cta{background:var(--p);color:#fff}
.hb--cta .hb-cta__btn{background:#fff;color:var(--p)}
.hb--cta .hb-cta__btn--alt{background:rgba(255,255,255,.15);color:#fff}
/* inner */
.pg-hero{background:var(--wash);border-bottom:1px solid var(--line)}
.pg-crumb{color:var(--soft)}
.pg-body p,.pg-body li{color:#414a56}
.pg-body img{border-radius:20px}
.pg-body details{border-bottom:1px solid var(--line)}
.pg-aside{background:var(--wash);border:1px solid var(--line);border-radius:22px}
.pg-tel{color:var(--p);font-family:Sora,sans-serif}
.pg-row{border-bottom:1px solid var(--line)}
.pg-row:hover h2{color:var(--p)}
.pg-row__n{color:var(--acc);font-family:Sora,sans-serif}
"""

def verdant_home(t, pages):
    e = H.esc
    h1, lead, faqs, top = _home_head(t, pages, VERDANT_FONTS, "Request a Quote")
    call = _tel(t, label=f'Call {e(t["phone"])}', cls="vd-btn") or ""
    pills = "".join(f'<span>{p}</span>' for p in [
        "Spring replacement", "Opener repair", "Off-track doors",
        "Cable &amp; roller service", "New door installation"])
    return (top
            + f'<section class="vd-hero"><span class="vd-kick">Garage doors · {e(t["city"])}, {e(t["st"])}</span>'
              f'<h1>{e(h1)}</h1><p>{e(lead)}</p><div class="vd-acts">{call}'
              f'<a class="vd-btn vd-btn--alt" href="/request-a-quote/">Request a quote</a></div></section>'
            + f'<div class="vd-band"><img src="{PHOTOS}{_hero(t)}" alt="{e(t["city"])} garage door" '
              f'width="1600" height="900" fetchpriority="high" decoding="async"></div>'
            + f'<div class="vd-pills">{pills}</div>'
            + hb_stack(t, pages, faqs, pin=("doors", "stats"))
            + _chrome_footer(t, pages) + "</body></html>")


# ---------------------------------------------------------------- registry
# Ten designs total: "garage" is the default in build.py, the nine here are selected
# per site via the "template" key in config/sites.json. Each is a distinct visual
# language -- own typography, own chrome treatment, own homepage composition -- and
# each takes its colour from the site's own brand hex via _paint().
#
# "volt" (dark/neon) was retired earlier and has now been removed rather than left
# lying in the file: it carried the pre-chrome nav markup and would have been a
# working example of exactly the pattern this module exists to prevent.
# `+ DARK_FOOT_LOGO` / `+ DARK_BAR_LOGO` where that design's footer / header is dark
# and the logo artwork would otherwise disappear into it.
REGISTRY = {
    # blocks=True on both: they were written before the shared section blocks existed and
    # rendered only their own markup, so they were registered without PAGE_CSS/BLOCK_CSS.
    # They now compose hb_* sections through hb_stack, and without that stylesheet the
    # block markup arrived completely unstyled -- card images fell back to their width/
    # height attributes (800x600 each), which inflated the guides section to 3704px and
    # the door-styles section to 4378px, and .hb-wrap had no max-width so copy ran to the
    # window edge.
    "ironclad": _mk(IRON_CSS + IRON_BLOCKS + DARK_FOOT_LOGO, iron_home, iron_inner, iron_index, iron_trust,
                    blocks=True),
    "nimbus":   _mk(NIM_CSS + NIM_BLOCKS, nim_home, nim_inner, nim_index, nim_trust, blocks=True),
    "forge":    _design(FORGE_FONTS, FORGE_CSS + DARK_FOOT_LOGO + DARK_BAR_LOGO, forge_home),
    "coastline": _design(COAST_FONTS, COAST_CSS, coast_home),
    "beacon":   _design(BEACON_FONTS, BEACON_CSS + DARK_FOOT_LOGO + DARK_BAR_LOGO, beacon_home, cta="Free Quote"),
    "atlas":    _design(ATLAS_FONTS, ATLAS_CSS + DARK_FOOT_LOGO, atlas_home),
    "hearth":   _design(HEARTH_FONTS, HEARTH_CSS, hearth_home, cta="Book a visit"),
    "quarry":   _design(QUARRY_FONTS, QUARRY_CSS + DARK_FOOT_LOGO, quarry_home, cta="Get a quote"),
    "verdant":  _design(VERDANT_FONTS, VERDANT_CSS + DARK_FOOT_LOGO, verdant_home),
}
