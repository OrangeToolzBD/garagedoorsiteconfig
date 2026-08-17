#!/usr/bin/env python
"""Self-designed landing-page generator for the porta-potty city sites.

Not the engine. Hand-built, contrast-checked design:
  - Full marketing landing page: header, hero, trust bar, services grid,
    features, pricing, how-it-works, service areas, FAQ, CTA band, footer.
  - Clean inner-page (service / suburb / guide / trust) article layout.
  - 5 distinct themes (colour + font pairing).
  - Real phone + address, POTTY V1 photos, visible logo, readable buttons.
"""
import html
import json
import os
import re
import shutil
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DATE = date.today().isoformat()
# Shared LeadConnector/GoHighLevel Request-a-Quote form id (porta network default).
# Override per site with "ghl_form_id" in config/sites.json.
GHL_FORM_ID = "oIYc6gL7YSv6tVK2P8IP"
DIST = os.path.join(ROOT, "dist")
POTTY_V1 = os.path.join(ROOT, "POTTY V1")
POTTY_V3 = os.path.join(ROOT, "POTTY V3", "POTTY V3")


def _v3_map():
    """Map canonical slug -> POTTY V3 filename (parallel image set, ' 3' suffix + a few typos)."""
    import difflib
    if not os.path.isdir(POTTY_V3) or not os.path.isdir(POTTY_V1):
        return {}
    v1 = [f[:-5] for f in os.listdir(POTTY_V1) if f.lower().endswith(".webp")]
    lett = lambda s: re.sub("[^a-z0-9]", "", s.lower())
    v1set = set(v1)
    v1n = {lett(s): s for s in v1}
    out = {}
    for f in os.listdir(POTTY_V3):
        if not f.lower().endswith(".webp"):
            continue
        base = f[:-5].replace("`", "").replace(" 3", "").strip()
        if base in v1set:
            out[base] = f; continue
        k = lett(base)
        if k in v1n:
            out[v1n[k]] = f; continue
        m = difflib.get_close_matches(k, list(v1n), n=1, cutoff=0.8)
        if m:
            out[v1n[m[0]]] = f
    return out


V3_MAP = _v3_map()
# sites that use the fresh POTTY V3 imagery (latest batch)
V3_SITES = {
    "desplainesportapros.com", "fountainebleauportapros.com", "bartlettportapros.com",
    "dearbornheightsportapros.com", "downtowndcportapros.com", "eastpensacolaheightslooco.com",
    "ankenyportapros.com", "bradentonportapros.com", "enidportapros.com",
}

# ------------------------------------------------------------------- site config
# Data-driven: sites + themes live in ./config/*.json. Add a city by editing
# config/sites.json (no code change). See README.md.
CONFIG = os.path.join(ROOT, "config")

DEFAULT_LAYOUT = {"hero": "split-right", "nav": "left", "shape": "pill", "bands": "alt", "footer": "dark", "cards": "classic", "feats": "tiles", "steps": "cards"}

def load_config():
    themes = json.load(open(os.path.join(CONFIG, "themes.json"), encoding="utf-8"))
    sdata = json.load(open(os.path.join(CONFIG, "sites.json"), encoding="utf-8"))
    lpath = os.path.join(CONFIG, "layouts.json")
    layouts = json.load(open(lpath, encoding="utf-8")) if os.path.exists(lpath) else {}
    sites, overrides, ports = {}, {}, {}
    for s in sdata["sites"]:
        theme = themes[s["theme"]]
        merged = {k: v for k, v in theme.items() if not k.startswith("_")}
        lay = layouts.get(s.get("layout", ""), DEFAULT_LAYOUT)
        merged["layout"] = {**DEFAULT_LAYOUT, **{k: v for k, v in lay.items() if not k.startswith("_")}}
        merged.update({
            "city": s["city"], "st": s["st"], "area": str(s.get("area", "")),
            "street": s.get("street", ""), "zip": s.get("zip", ""),
            "tagline": s.get("tagline", "Portable Restrooms"),
            "phone_override": s.get("phone", ""),
            "ghl_form_id": s.get("ghl_form_id", GHL_FORM_ID),
        })
        sites[s["domain"]] = merged
        ports[s["domain"]] = s.get("port")
        if s.get("suburbs"):
            overrides[s["domain"]] = [tuple(x) for x in s["suburbs"]]
    return sites, overrides, ports

SITES, SUBURBS_OVERRIDE, PORTS = load_config()

CURATED = ["portable-toilet-rental", "ada-accessible-porta-potty", "deluxe-flushable-porta-potty",
           "restroom-trailer-rental", "luxury-restroom-trailer", "roll-off-dumpster-rental",
           "construction-site-services", "event-restroom-rental", "handwashing-station-rental",
           "porta-potty-monthly-rental", "standard-porta-potty-rental", "portable-restroom-rental"]

MENU = [
    ("Portable Toilets", ["portable-toilet-rental", "standard-porta-potty-rental",
        "deluxe-flushable-porta-potty", "ada-accessible-porta-potty", "porta-potty-monthly-rental",
        "porta-potty-rental-per-day", "portable-restroom-rental", "porta-john-rental",
        "emergency-porta-potty-rental", "home-renovation-porta-potty", "camping-porta-potty"]),
    ("Restroom Trailers", ["restroom-trailer-rental", "2-stall-restroom-trailer",
        "4-stall-restroom-trailer", "8-stall-restroom-trailer", "luxury-restroom-trailer",
        "shower-trailer-rental", "restroom-trailer-rental-cost"]),
    ("Dumpsters", ["roll-off-dumpster-rental", "10-yard-dumpster-rental", "20-yard-dumpster-rental",
        "30-yard-dumpster-rental", "40-yard-dumpster-rental", "construction-dumpster-rental",
        "dumpster-rental-cost", "dumpster-sizes-and-dimensions"]),
    ("Events", ["event-restroom-rental", "wedding-restroom-rental", "festival-restroom-rental",
        "concert-restroom-rental", "marathon-restroom-rental", "golf-tournament-restrooms",
        "county-fair-restrooms", "hand-sanitizer-station-rental", "handwashing-station-rental"]),
    ("Site & Septic", ["construction-site-services", "storage-container-rental",
        "mobile-office-trailer-rental", "temporary-fence-rental", "light-tower-rental",
        "septic-pumping-service", "grease-trap-pumping", "emergency-septic-service"]),
]

# ------------------------------------------------------------------ icons (inline)
def icon(name):
    p = {
        "phone": '<path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.2.4 2.4.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.9 21 3 13.1 3 3c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z"/>',
        "truck": '<path d="M3 6h11v9H3zM14 9h4l3 3v3h-7zM7 18a2 2 0 100 .1zM18 18a2 2 0 100 .1z" fill="none" stroke="currentColor" stroke-width="1.7"/>',
        "clock": '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 7v5l3 2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
        "shield": '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M9 12l2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
        "tag": '<path d="M4 4h7l9 9-7 7-9-9z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><circle cx="8.5" cy="8.5" r="1.4"/>',
        "sparkle": '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
        "pin": '<path d="M12 21s7-6 7-11a7 7 0 10-14 0c0 5 7 11 7 11z" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="10" r="2.5" fill="none" stroke="currentColor" stroke-width="1.7"/>',
        "leaf": '<path d="M4 20c8 0 16-4 16-16C8 4 4 12 4 20z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
        "calendar": '<rect x="4" y="5" width="16" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M4 9.5h16M8.5 3v4M15.5 3v4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
        "check": '<path d="M5 12l4 4 10-10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
        "star": '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.1 1.2 6-5.4-3-5.4 3 1.2-6L3.3 9.3l6.1-.7z"/>',
        "arrow": '<path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    }.get(name, "")
    return f'<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="currentColor">{p}</svg>'

# ------------------------------------------------------------------ markdown
def _inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t

def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", t).lower()).strip("-")

def render_md(md):
    lines = md.split("\n"); out = []; i = 0; n = len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1; continue
        if s.startswith("|") and i + 1 < n and re.match(r"^\|?[\s:|-]+\|?$", lines[i+1].strip()):
            head = [c.strip() for c in s.strip("|").split("|")]; i += 2; rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            out.append('<div class="tw"><table><thead><tr>' + "".join(f"<th>{_inline(c)}</th>" for c in head) + "</tr></thead><tbody>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table></div>"); continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            lv = min(len(m.group(1)), 4)
            out.append(f'<h{lv} id="{slugify(m.group(2))}">{_inline(m.group(2))}</h{lv}>'); i += 1; continue
        if re.match(r"^[-*+]\s+", s):
            out.append("<ul>")
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                out.append(f"<li>{_inline(re.sub(r'^[-*+]\\s+','',lines[i].strip()))}</li>"); i += 1
            out.append("</ul>"); continue
        if re.match(r"^\d+\.\s+", s):
            out.append("<ol>")
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                out.append(f"<li>{_inline(re.sub(r'^\\d+\\.\\s+','',lines[i].strip()))}</li>"); i += 1
            out.append("</ol>"); continue
        buf = [s]; i += 1
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|[-*+]\s|\d+\.\s|\|)", lines[i].strip()):
            buf.append(lines[i].strip()); i += 1
        out.append(f"<p>{_inline(' '.join(buf))}</p>")
    return "\n".join(out)

def synth_suburb(site, name, st):
    """Build a real (non-thin) suburb landing page for a service-area suburb
    that has no content file yet."""
    slug = "porta-potty-rental-" + slugify(name) + "-" + st.lower()
    url = f"/{slug}/"
    city = site["city"]
    h1 = f"Porta Potty Rental in {name}, {st}"
    meta = {
        "url": url, "h1": h1,
        "title_tag": f"{h1} | {city} Porta Pros",
        "meta_description": (f"Porta potty rental in {name}, {st}. Portable toilets, restroom "
                             f"trailers and dumpsters with fast local delivery from {city} Porta Pros."),
    }
    body = f"""# {h1}

{city} Porta Pros delivers portable toilets, restroom trailers and dumpsters across {name}, {st} and the greater {city} metro. Same-day and next-day drop-off is available on most orders — call for a written quote.

## Portable toilet options in {name}

Whether it is a backyard project, a construction site or an outdoor event, we have the right unit: [standard porta potties](/standard-porta-potty-rental/), [deluxe flushable units](/deluxe-flushable-porta-potty/), [ADA-accessible units](/ada-accessible-porta-potty/) and full [restroom trailers](/restroom-trailer-rental/). Every rental includes scheduled cleaning, restock and deodorizing.

## Construction & event service in {name}

Running a job site in {name}? Pair a unit with a [handwashing station](/handwashing-station-rental/) and a [roll-off dumpster](/roll-off-dumpster-rental/) so the whole site is covered from one vendor. Hosting an event? We handle [weddings](/wedding-restroom-rental/), [festivals](/festival-restroom-rental/) and more with clean, well-stocked units.

## How delivery works

Tell us the address in {name}, the dates and the headcount, and we size the order and confirm a delivery window. See our [pricing](/porta-potty-rental-cost/) for real numbers, or the full list of [service areas](/service-areas/) we cover around {city}.

## Frequently asked questions

### Do you deliver to {name}, {st}?

Yes. {name} is within our regular {city} service area, with same-day delivery available on many orders when you book early.

### How much does porta potty rental cost in {name}?

Pricing depends on the unit type and how long you need it. See our [cost breakdown](/porta-potty-rental-cost/) and request a free quote for an exact figure for {name}.

### How often are units serviced?

Standard rentals include weekly service — a pump-out, a clean, a restock and fresh deodorizer. Busy sites and hot-weather jobs can be serviced more often.
"""
    return {"meta": meta, "body": body, "cat": "suburb", "url": url}


def _trust_meta(site, url, h1, desc):
    return {"url": url, "h1": h1, "title_tag": f"{h1} | {site['city']} Porta Pros",
            "meta_description": desc}

def synth_about(site):
    c, st = site["city"], site["st"]
    h1 = f"About {c} Porta Pros"
    body = f"""# {h1}

{c} Porta Pros is a local portable sanitation company serving {c}, {st} and the surrounding metro. We rent portable toilets, restroom trailers, roll-off dumpsters, storage containers, temporary fencing and handwashing stations — and we handle the delivery, the scheduled service and the pickup with one local crew.

## What we do

We keep it simple: one call, one crew, one truck. Whether it is a single [standard porta potty](/standard-porta-potty-rental/) for a backyard renovation, a bank of units for a [festival](/festival-restroom-rental/), or a full [construction site setup](/construction-site-services/) with dumpsters and fencing, we size the order, deliver on time and service it on schedule. Need something upscale? Our [restroom trailers](/restroom-trailer-rental/) bring flushing toilets and running water to weddings and corporate events.

## How we work

Every rental includes scheduled service under ANSI/PSAI Z4.3 — a pump-out, a clean, a restock and fresh deodorizer, weekly for normal use and more often for busy sites. On construction jobs we help you hit the OSHA 1926.51(c)(1) unit counts so an inspection is never a surprise. Pricing is flat and written, with delivery and service broken out, so there are no surprises on the invoice. See our [pricing](/porta-potty-rental-cost/) for real ranges.

## Where we serve

We deliver across {c} and nearby communities — check the [service areas](/service-areas/) we cover. Ready to book? [Request a free quote](/request-a-quote/) or call {site['phone']}.
"""
    return {"meta": _trust_meta(site, "/about/", h1,
            f"About {c} Porta Pros — local portable toilet, restroom trailer and dumpster rental in {c}, {st}. On-time delivery, weekly service, transparent pricing."),
            "body": body, "cat": "trust", "url": "/about/"}

def synth_contact(site):
    c, st = site["city"], site["st"]
    zippart = f" {site['zip']}" if site["zip"] else ""
    h1 = f"Contact {c} Porta Pros"
    body = f"""# {h1}

{c} Porta Pros rents portable toilets, restroom trailers, dumpsters and site services across {c}, {st} and the surrounding metro. Call or request a quote and our dispatch team will confirm availability, a delivery window and a flat price — most quotes come back the same working day.

## Phone and office hours

Call **{site['phone']}** during business hours to book a rental or check availability. Our team handles every service: standard and [deluxe flushable units](/deluxe-flushable-porta-potty/), [ADA accessible units](/ada-accessible-porta-potty/), [roll-off dumpsters](/roll-off-dumpster-rental/), [restroom trailers](/restroom-trailer-rental/), [handwashing stations](/handwashing-station-rental/) and more. Peak season can fill same-day slots, so book ahead for construction sites and events.

## Visit us

{site['street']}, {c}, {st}{zippart}

## Request a quote online

Prefer to send the details? Use our [quote form](/request-a-quote/) — tell us the address in {c}, the dates, the type of rental and how many units you need, and a crew member will follow up with availability and pricing. Not sure how many units you need? Our [sizing guide](/how-many-porta-potties-do-i-need/) and the [service areas](/service-areas/) page can help.
"""
    return {"meta": _trust_meta(site, "/contact/", h1,
            f"Contact {c} Porta Pros. Call {site['phone']} for porta potty, restroom trailer and dumpster rental in {c}, {st}. Fast quotes, on-time delivery."),
            "body": body, "cat": "trust", "url": "/contact/"}

def synth_faq(site):
    c, st = site["city"], site["st"]
    h1 = f"Frequently Asked Questions in {c}, {st}"
    body = f"""# {h1}

{c} Porta Pros handles portable toilets, restroom trailers, dumpsters, handwashing stations and site services across {c}. Here are the questions we hear most — on sizing, cost, placement and service. A standard portable toilet holds 60 to 70 gallons and gets serviced weekly under normal use.

## Do I need a permit to place a portable toilet in {c}?

On private property — a driveway, yard or fenced lot — you usually do not. Placing a unit on a public street, sidewalk or right of way needs confirming with the city first, and we will not cite a rule we cannot verify. Most of our residential and jobsite drops land on private ground for exactly this reason.

## How many portable toilets do I need?

For a job site, OSHA 1926.51(c)(1) sets the floor: one toilet for up to 20 workers, then one seat and one urinal per 40 workers above that. For an [event](/event-restroom-rental/), budget roughly one unit per 50 guests over a four-hour window, plus 15–20% if you are serving alcohol. Our [sizing guide](/how-many-porta-potties-do-i-need/) does the math for your crew.

## What does porta potty rental cost in {c}?

Pricing depends on the unit and how long you need it — daily rates run higher per day than weekly or monthly. See the full breakdown on our [pricing page](/porta-potty-rental-cost/) and [request a written quote](/request-a-quote/) for your exact job. Delivery is billed separately and depends on distance and access.

## How often are units serviced?

Standard rentals include weekly service under ANSI/PSAI Z4.3 — a pump-out, a wash, a restock and fresh deodorizer. Busy sites and hot-weather jobs get serviced more often. [ADA accessible units](/ada-accessible-porta-potty/) follow the same schedule.

## What is the difference between a standard and a deluxe unit?

A [standard porta potty](/standard-porta-potty-rental/) is a self-contained non-sewer toilet with a holding tank and no running water. A [deluxe flushable unit](/deluxe-flushable-porta-potty/) adds a foot-pump flush and a sink, which suits weddings and longer events. For upscale crowds, a [restroom trailer](/restroom-trailer-rental/) brings flushing toilets and climate control.

## How fast can you deliver in {c}?

Most orders placed by early afternoon go out the same day or the next morning across {c}. Emergencies move first through [emergency porta potty rental](/emergency-porta-potty-rental/). The hold-up is rarely the truck — it is usually a locked gate or a blocked approach, so tell us about access up front. Ready to book? Call {site['phone']} or [request a quote](/request-a-quote/).
"""
    return {"meta": _trust_meta(site, "/faq/", h1,
            f"Frequently asked questions about porta potty, restroom trailer and dumpster rental in {c}, {st} — permits, sizing, cost, service and delivery."),
            "body": body, "cat": "trust", "url": "/faq/"}

def synth_request_quote(site):
    """A /request-a-quote/ page (the GHL form target + primary CTA). Generated
    when a city's content lacks one, so quote CTAs never break."""
    city, st = site["city"], site["st"]
    h1 = f"Request a Quote in {city}, {st}"
    meta = {"url": "/request-a-quote/", "h1": h1,
            "title_tag": f"Request a Quote | {city} Porta Pros",
            "meta_description": (f"Request a free porta potty, restroom trailer or dumpster quote for "
                                 f"any {city}, {st} address. Real pricing, fast turnaround, no hidden fees.")}
    body = f"""# {h1}

Tell us the address, the dates and the headcount, and {city} Porta Pros sizes the order and sends a written price — most quotes come back the same working day. Prefer to talk it through? Call {site['phone']}.

## What we need for an accurate quote

- The delivery address in {city} and the dates you need the unit.
- A rough headcount, or the type of job (construction, event, home project).
- Whether the unit sits on private property or the public right of way.

## What happens next

We confirm availability, a delivery window and a flat price — no surprises, no hidden fees. See our [pricing](/porta-potty-rental-cost/) for typical ranges, or browse the [service areas](/service-areas/) we cover around {city}.
"""
    return {"meta": meta, "body": body, "cat": "trust", "url": "/request-a-quote/"}


def parse_fm(text):
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1); meta[k.strip()] = v.strip()
            body = text[end+4:].lstrip("\n")
    return meta, body

def split_sections(body):
    lines = body.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith("# "):
        lines.pop(0)
    parts = re.split(r"(?m)^##\s+", "\n".join(lines))
    pre = parts[0].strip(); secs = []
    for part in parts[1:]:
        nl = part.find("\n")
        title, rest = (part.strip(), "") if nl == -1 else (part[:nl].strip(), part[nl+1:])
        secs.append((title, rest))
    return pre, secs

def first_para(pre):
    if not pre:
        return ""
    blk = re.split(r"\n\s*\n", pre.strip())[0]
    return re.sub(r"[*`]", "", re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", blk)).strip()

def parse_faq(md):
    parts = re.split(r"(?m)^###\s+", md); items = []
    for part in parts[1:]:
        nl = part.find("\n")
        q, a = (part.strip(), "") if nl == -1 else (part[:nl].strip(), part[nl+1:].strip())
        items.append((q, a))
    return items

# ------------------------------------------------------------------ images
IMG = {fn[:-5] for fn in os.listdir(POTTY_V1) if fn.lower().endswith(".webp")} if os.path.isdir(POTTY_V1) else set()

def img_for(slug, default="portable-toilet-rental"):
    if slug in IMG:
        return slug
    return default if default in IMG else (sorted(IMG)[0] if IMG else "")

def short(text, n=95):
    text = re.sub(r"\.\s.*$", ".", text.strip()) if "." in text else text
    return (text[:n].rstrip() + "…") if len(text) > n else text

# ------------------------------------------------------------------ CSS
def css(t):
    shape = t.get("layout", {}).get("shape", "pill")
    btnr = {"pill": "999px", "round": "12px", "sharp": "3px"}.get(shape, "999px")
    cardr = {"pill": "16px", "round": "14px", "sharp": "4px"}.get(shape, "16px")
    return CSS_TMPL.replace("__P__", t["p"]).replace("__PD__", t["pd"]) \
        .replace("__ACCENT__", t["accent"]).replace("__ONACCENT__", t["on_accent"]) \
        .replace("__DISPLAY__", t["display"]).replace("__BODY__", t["body"]) \
        .replace("__BTNR__", btnr).replace("__CARDR__", cardr)

CSS_TMPL = """
:root{
  --p:__P__;--pd:__PD__;--accent:__ACCENT__;--on-accent:__ONACCENT__;
  --ink:#182029;--muted:#5c6773;--bg:#ffffff;--soft:#f5f7f9;--soft2:#eef2f6;
  --line:#e3e8ee;--card:#ffffff;--radius:__CARDR__;--btn-r:__BTNR__;--maxw:1180px;
  --shadow:0 1px 2px rgba(16,32,48,.05),0 8px 24px rgba(16,32,48,.06);
  --shadow-lg:0 12px 40px rgba(16,32,48,.14);
  --disp:'__DISPLAY__',system-ui,sans-serif;--body:'__BODY__',system-ui,sans-serif;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
html,body{overflow-x:clip;max-width:100%}
body{margin:0;font-family:var(--body);color:var(--ink);background:var(--bg);line-height:1.65;font-size:17px}
h1,h2,h3,h4{font-family:var(--disp);line-height:1.12;letter-spacing:-.02em;margin:0 0 .5em;font-weight:700}
h1{font-size:clamp(2.1rem,4.2vw,3.3rem);font-weight:800}
h2{font-size:clamp(1.6rem,3vw,2.3rem)}
h3{font-size:1.25rem}
p{margin:0 0 1rem}
a{color:var(--p);text-decoration:none}
a:hover{text-decoration:underline}
img{max-width:100%;display:block}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 24px}
.eyebrow{font-family:var(--disp);font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:.8rem;color:var(--accent);margin:0 0 .6rem}
.sec{padding:76px 0}
.sec--soft{background:var(--soft)}
.sec-head{max-width:720px;margin:0 auto 46px;text-align:center}
.sec-head p{color:var(--muted);font-size:1.08rem;margin:0}
/* buttons — always high contrast */
.btn{display:inline-flex;align-items:center;gap:9px;font-family:var(--disp);font-weight:700;font-size:1rem;
  padding:14px 26px;border-radius:var(--btn-r);border:2px solid transparent;cursor:pointer;transition:.16s;white-space:nowrap;text-decoration:none}
.btn svg{width:18px;height:18px}
.btn--primary{background:var(--accent);color:var(--on-accent)}
.btn--primary:hover{filter:brightness(1.06);text-decoration:none;transform:translateY(-1px)}
.btn--dark{background:var(--p);color:#fff}
.btn--dark:hover{background:var(--pd);text-decoration:none;transform:translateY(-1px)}
.btn--ghost{background:transparent;color:#fff;border-color:rgba(255,255,255,.55)}
.btn--ghost:hover{background:rgba(255,255,255,.12);text-decoration:none}
.btn--outline{background:#fff;color:var(--p);border-color:var(--line)}
.btn--outline:hover{border-color:var(--p);text-decoration:none}
/* header */
.top{background:var(--pd);color:#fff;font-size:.85rem}
.top .wrap{display:flex;align-items:center;gap:14px;padding:8px 24px}
.top a{color:#fff;font-weight:600}
.top a svg{width:12px;height:12px;fill:var(--accent);vertical-align:-1px;margin-right:4px}
.top .dot{opacity:.4}
.top .tsp{flex:1}
.nav-cta-m{display:none}
.nav-quote{display:none}
header.site{position:sticky;top:0;z-index:60;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.hd{display:flex;align-items:center;gap:12px;padding:12px 0}
.brand{display:flex;align-items:center;gap:10px;font-family:var(--disp);font-weight:800;font-size:.9rem;color:var(--ink);flex:0 0 auto}
.brand:hover{text-decoration:none}
.brand>span{white-space:nowrap;line-height:1.08}
.brand__chip{width:42px;height:42px;border-radius:11px;flex:0 0 auto;background:#fff;border:1px solid var(--line);box-shadow:var(--shadow);display:flex;align-items:center;justify-content:center;padding:5px}
.brand__chip img{width:100%;height:100%;object-fit:contain;display:block}
.brand__full{display:inline-flex;align-items:center;flex:0 0 auto}
.brand__full img{height:44px;width:auto;max-width:250px;object-fit:contain;display:block}
.brand__full--ft{background:#fff;border-radius:12px;padding:8px 12px;box-shadow:var(--shadow)}
.brand__full--ft img{height:40px;max-width:230px}
@media(max-width:560px){.brand__full img{height:38px;max-width:180px}}
.brand small{display:block;font-size:.64rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin-top:1px}
nav.main{margin-left:auto;display:flex;align-items:center;gap:2px;flex:0 1 auto}
nav.main>a,.nav-item>button{font-family:var(--disp);font-weight:600;font-size:.88rem;color:var(--ink);background:none;border:0;padding:8px 9px;border-radius:10px;cursor:pointer;white-space:nowrap}
nav.main>a:hover,.nav-item>button:hover{background:var(--soft);text-decoration:none}
.nav-item{position:relative}
.nav-item>button::after{content:"";display:inline-block;width:7px;height:7px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(45deg);margin-left:7px;vertical-align:2px}
.mega{position:absolute;top:calc(100% + 8px);left:50%;transform:translateX(-50%) translateY(6px);
  background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow-lg);
  padding:14px;min-width:280px;opacity:0;visibility:hidden;transition:.16s;z-index:70}
.nav-item:hover .mega{opacity:1;visibility:visible;transform:translateX(-50%) translateY(0)}
.mega a{display:block;padding:9px 12px;border-radius:9px;color:var(--ink);font-size:.94rem;font-weight:500}
.mega a:hover{background:var(--soft);color:var(--p);text-decoration:none}
.mega--areas{min-width:380px;display:grid;grid-template-columns:1fr 1fr;gap:2px 8px}
.mega--areas .mega-all{grid-column:1/-1;font-weight:700;color:var(--p);border-bottom:1px solid var(--line);border-radius:0;margin-bottom:6px}
.hd .tel{margin-left:4px;display:inline-flex;align-items:center;gap:7px;font-family:var(--disp);font-weight:700;color:var(--p);white-space:nowrap;flex:0 0 auto;font-size:.95rem}
.hd .tel svg{fill:var(--accent);flex:0 0 auto}
.hd .btn{margin-left:2px;flex:0 0 auto;padding:12px 20px}
.burger{display:none;margin-left:auto;background:none;border:0;cursor:pointer;padding:8px}
.burger span{display:block;width:24px;height:2.5px;background:var(--ink);border-radius:2px;margin:5px 0}
/* hero (variant-aware) */
.hero{position:relative;background:linear-gradient(155deg,var(--pd),var(--p));color:#fff;overflow:hidden}
.hero::after{content:"";position:absolute;right:-140px;top:-140px;width:420px;height:420px;border-radius:50%;background:var(--accent);opacity:.14}
.hero h1{color:#fff}
.hero .eyebrow{color:var(--accent)}
.hero .lead{font-size:1.18rem;color:rgba(255,255,255,.9);max-width:42ch;margin:0 0 26px}
.hero .cta{display:flex;gap:13px;flex-wrap:wrap;margin-bottom:26px}
.hero .chips{display:flex;flex-wrap:wrap;gap:10px 20px;list-style:none;padding:0;margin:0}
.hero .chips li{display:flex;align-items:center;gap:8px;font-size:.94rem;color:rgba(255,255,255,.92)}
.hero .chips svg{width:18px;height:18px;fill:var(--accent)}
.hero__media{position:relative}
.hero__media img{border-radius:calc(var(--radius) + 4px);box-shadow:var(--shadow-lg);aspect-ratio:4/3;object-fit:cover;width:100%}
.hero__badge{position:absolute;left:-18px;bottom:-18px;background:#fff;color:var(--ink);border-radius:var(--radius);padding:14px 18px;box-shadow:var(--shadow-lg);display:flex;align-items:center;gap:12px}
.hero__badge b{font-family:var(--disp);font-size:1.5rem;display:block;line-height:1;color:var(--p)}
.hero__badge span{font-size:.8rem;color:var(--muted)}
/* -- split (right/left) -- */
.hero--split .wrap{position:relative;display:grid;grid-template-columns:1.05fr .95fr;gap:52px;align-items:center;padding:76px 24px 82px}
.hero--left .wrap{grid-template-columns:.95fr 1.05fr}
/* -- stacked: centered copy, wide image below -- */
.hero--stacked .wrap{position:relative;padding:66px 24px 0;text-align:center}
.hero--stacked .hero__copy{max-width:760px;margin:0 auto}
.hero--stacked .lead{margin:0 auto 26px}
.hero--stacked .cta,.hero--stacked .chips{justify-content:center}
.hero__media--wide{margin:36px auto -64px;max-width:1000px}
.hero__media--wide img{width:100%;aspect-ratio:21/9;object-fit:cover;border-radius:calc(var(--radius) + 4px) calc(var(--radius) + 4px) 0 0;box-shadow:var(--shadow-lg)}
/* -- center: big centered copy on gradient + faint photo, no side image -- */
.hero--center{background:linear-gradient(155deg,color-mix(in srgb,var(--pd) 90%,transparent),color-mix(in srgb,var(--p) 84%,transparent)),var(--hero-bg) center/cover no-repeat}
.hero--center .wrap{position:relative;text-align:center;padding:96px 24px 104px;max-width:840px}
.hero--center h1{font-size:clamp(2.4rem,5vw,3.9rem)}
.hero--center .lead{margin:0 auto 26px}
.hero--center .cta,.hero--center .chips{justify-content:center}
/* -- banner: full-bleed photo + dark overlay, centered copy -- */
.hero--banner{background:linear-gradient(rgba(11,18,28,.74),rgba(11,18,28,.66)),var(--hero-bg) center/cover no-repeat}
.hero--banner::after{display:none}
.hero--banner .wrap{position:relative;padding:106px 24px;max-width:840px;text-align:center}
.hero--banner .cta,.hero--banner .chips{justify-content:center}
.hero--banner .lead{margin:0 auto 26px}
/* -- overlap: image band with a floating copy card -- */
.hero--overlap{background:none;color:#fff;overflow:visible}
.hero--overlap::after{display:none}
.hero__bgimg{height:clamp(300px,40vw,480px)}
.hero__bgimg img{width:100%;height:100%;object-fit:cover;display:block}
.hero--overlap .wrap{position:relative;margin-top:clamp(-170px,-14vw,-130px);padding-bottom:44px}
.hero__card{background:linear-gradient(155deg,var(--pd),var(--p));border-radius:calc(var(--radius) + 6px);padding:clamp(28px,4vw,46px);max-width:660px;box-shadow:var(--shadow-lg)}
/* -- navbar variants -- */
.lay-nav-center .hd{position:relative;flex-wrap:wrap;justify-content:center;row-gap:4px;padding:12px 0 10px}
.lay-nav-center .brand{margin:2px auto}
.lay-nav-center nav.main{order:5;flex-basis:100%;justify-content:center;margin-left:0;gap:2px}
.lay-nav-center .hd>.btn{order:4;position:absolute;right:0;top:14px}
.lay-nav-pill nav.main{background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:5px 7px;gap:2px}
.lay-nav-pill nav.main>a,.lay-nav-pill .nav-item>button{border-radius:999px;padding:9px 14px}
.lay-nav-pill nav.main>a:hover,.lay-nav-pill .nav-item>button:hover{background:#fff}
/* -- section band rhythm -- */
.lay-bands-flat .sec--soft{background:#fff;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.lay-bands-flat .trust{background:var(--pd)}
/* trust bar */
.trust{background:var(--p);color:#fff}
.trust .wrap{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;padding:22px 24px}
.trust div{display:flex;align-items:center;gap:12px;justify-content:center;font-weight:600;font-size:.96rem}
.trust svg{fill:none;stroke:var(--accent);color:var(--accent);flex:0 0 auto}
.trust b{color:var(--accent)}
/* generic grid */
.grid{display:grid;gap:24px}
.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
/* service cards */
.scard{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow);transition:.18s;display:flex;flex-direction:column}
.scard:hover{transform:translateY(-5px);box-shadow:var(--shadow-lg)}
.scard img{aspect-ratio:16/10;object-fit:cover;width:100%}
.scard__b{padding:20px 22px 22px;display:flex;flex-direction:column;flex:1}
.scard h3{margin:0 0 6px;font-size:1.12rem}
.scard p{color:var(--muted);font-size:.94rem;margin:0 0 14px;flex:1}
.scard .more{font-family:var(--disp);font-weight:700;color:var(--p);display:inline-flex;align-items:center;gap:6px;font-size:.92rem}
.scard .more svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2}
/* -- service-card style variants (What We Rent) -- */
/* overlay: photo-forward, title + arrow over a gradient */
.scards--overlay .scard{position:relative}
.scards--overlay .scard img{aspect-ratio:3/4}
.scards--overlay .scard__b{position:absolute;inset:auto 0 0 0;background:linear-gradient(to top,rgba(10,14,20,.9) 12%,rgba(10,14,20,.45) 55%,transparent);padding:18px 20px 18px}
.scards--overlay .scard h3{color:#fff;margin:0 0 4px}
.scards--overlay .scard p{display:none}
.scards--overlay .scard .more{color:#fff}
.scards--overlay .scard .more svg{stroke:#fff}
/* side: horizontal card, image left */
.scards--side{grid-template-columns:repeat(2,1fr)}
.scards--side .scard{flex-direction:row;align-items:stretch}
.scards--side .scard img{width:42%;aspect-ratio:auto;object-fit:cover;flex:0 0 42%}
.scards--side .scard__b{padding:20px 22px}
/* bold: accent top bar, uppercase title, whole card is the link (no "more" row) */
.scards--bold .scard{border-top:4px solid var(--accent)}
.scards--bold .scard h3{text-transform:uppercase;letter-spacing:.02em;font-size:1.06rem}
.scards--bold .scard .more{display:none}
.scards--bold .scard__b{padding-bottom:22px}
/* feature tiles */
.feat{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:26px;box-shadow:var(--shadow)}
.feat .ic{width:50px;height:50px;border-radius:13px;background:color-mix(in srgb,var(--accent) 16%,#fff);color:var(--p);display:flex;align-items:center;justify-content:center;margin-bottom:14px}
.feat .ic svg{fill:none;stroke:currentColor;color:var(--p)}
.feat h3{margin:0 0 6px;font-size:1.08rem}
.feat p{color:var(--muted);font-size:.95rem;margin:0}
/* steps */
.steps{counter-reset:s;display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.step{position:relative;padding:28px 24px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
.step::before{counter-increment:s;content:counter(s);position:absolute;top:-18px;left:24px;width:44px;height:44px;border-radius:12px;background:var(--p);color:#fff;font-family:var(--disp);font-weight:800;display:flex;align-items:center;justify-content:center;font-size:1.2rem}
.step h3{margin:14px 0 6px}
.step p{color:var(--muted);margin:0;font-size:.95rem}
.step__b{min-width:0}
/* -- feature-section variants (Why Us) -- */
.feats--list .feat{display:flex;gap:16px;align-items:flex-start}
.feats--list .feat .ic{margin-bottom:0;flex:0 0 50px}
.feats--bar .feat{border-top:3px solid var(--accent)}
.feats--minimal{gap:0}
.feats--minimal .feat{display:flex;gap:16px;align-items:flex-start;background:none;border:0;border-top:1px solid var(--line);border-radius:0;box-shadow:none;padding:22px 4px}
.feats--minimal .feat .ic{background:none;width:36px;height:36px;margin-bottom:0;color:var(--accent);flex:0 0 36px}
.feats--minimal .feat .ic svg{color:var(--accent)}
/* -- how-it-works variants -- */
.steps--bignum{grid-template-columns:1fr;gap:0}
.steps--bignum .step{display:flex;gap:22px;align-items:center;background:none;border:0;border-bottom:1px solid var(--line);border-radius:0;box-shadow:none;padding:22px 2px}
.steps--bignum .step:last-child{border-bottom:0}
.steps--bignum .step::before{position:static;width:auto;height:auto;min-width:54px;background:none;border-radius:0;color:var(--accent);font-size:2.8rem;line-height:1;display:block;text-align:center}
.steps--bignum .step h3{margin:0 0 4px}
.steps--timeline{position:relative}
.steps--timeline .step{text-align:center;background:none;border:0;box-shadow:none;padding:58px 12px 0}
.steps--timeline .step::before{left:50%;transform:translateX(-50%);top:4px}
.steps--timeline .step h3{margin:0 0 6px}
@media(min-width:721px){.steps--timeline::before{content:"";position:absolute;top:26px;left:16.6%;right:16.6%;height:2px;background:var(--line);z-index:0}.steps--timeline .step::before{z-index:1}}
/* pricing */
.pricewrap{max-width:760px;margin:0 auto}
.pricewrap table{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow)}
table{width:100%;border-collapse:collapse}
.pricewrap th,.pricewrap td,.tw th,.tw td{padding:14px 18px;text-align:left;border-bottom:1px solid var(--line)}
.pricewrap thead th,.tw thead th{background:var(--p);color:#fff;font-family:var(--disp);border-bottom:0}
.pricewrap tbody tr:last-child td{border-bottom:0}
.pricewrap tbody tr:nth-child(even){background:var(--soft)}
.pricenote{text-align:center;color:var(--muted);margin:18px 0 0;font-size:.92rem}
/* areas */
.areas{display:flex;flex-wrap:wrap;gap:12px;justify-content:center;max-width:900px;margin:0 auto}
.areas a{background:#fff;border:1px solid var(--line);border-radius:999px;padding:10px 20px;font-weight:600;font-size:.95rem;color:var(--ink);box-shadow:var(--shadow)}
.areas a:hover{border-color:var(--p);color:var(--p);text-decoration:none}
/* faq */
.faq{max-width:820px;margin:0 auto;display:flex;flex-direction:column;gap:12px}
.faq details{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);overflow:hidden}
.faq summary{list-style:none;cursor:pointer;padding:18px 22px;font-family:var(--disp);font-weight:700;font-size:1.05rem;display:flex;justify-content:space-between;align-items:center;gap:16px}
.faq summary::-webkit-details-marker{display:none}
.faq summary::after{content:"+";font-size:1.5rem;color:var(--accent);font-weight:400;transition:.2s}
.faq details[open] summary::after{transform:rotate(45deg)}
.faq .a{padding:0 22px 20px;color:var(--muted)}
.faq .a p{margin:0 0 .7rem}
/* cta band */
.cta-band{background:linear-gradient(135deg,var(--p),var(--pd));color:#fff;border-radius:24px;padding:52px;text-align:center;box-shadow:var(--shadow-lg);position:relative;overflow:hidden}
.cta-band h2{color:#fff;margin:0 0 10px}
.cta-band p{color:rgba(255,255,255,.9);max-width:52ch;margin:0 auto 26px}
.cta-band .cta{display:flex;gap:18px;justify-content:center;flex-wrap:wrap}
/* footer */
footer.site{background:#0f151b;color:#aeb9c5;padding:60px 0 26px;margin-top:0}
footer.site .cols{display:grid;grid-template-columns:1.5fr 1fr 1fr 1.3fr;gap:34px;padding-bottom:34px;border-bottom:1px solid rgba(255,255,255,.1)}
footer.site h4{color:#fff;font-size:.95rem;margin:0 0 14px;letter-spacing:.04em;text-transform:uppercase}
footer.site a{color:#c4cdd8;display:block;padding:5px 0;font-size:.95rem}
footer.site a:hover{color:#fff}
footer.site .fbrand p{font-size:.95rem;max-width:32ch}
footer.site .flogo{display:flex;align-items:center;gap:10px;color:#fff;font-family:var(--disp);font-weight:800;font-size:1.15rem;margin-bottom:14px}
footer.site .addr{font-style:normal;line-height:1.7;font-size:.95rem}
footer.site .addr a{display:inline;padding:0;color:#fff;font-weight:700}
.legal{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;padding-top:22px;font-size:.86rem;color:#7d8894}
/* -- footer variants (footer.site prefix so they beat the base specificity) -- */
footer.site.ft--dark{border-top:4px solid var(--accent)}
footer.site.ft--brand{background:var(--pd)}
footer.site.ft--brand h4{color:var(--accent)}
footer.site.ft--light{background:var(--soft);color:var(--muted);border-top:1px solid var(--line)}
footer.site.ft--light h4{color:var(--ink)}
footer.site.ft--light a{color:var(--muted)}
footer.site.ft--light a:hover{color:var(--p)}
footer.site.ft--light .flogo{color:var(--ink)}
footer.site.ft--light .addr,footer.site.ft--light .fbrand p{color:var(--muted)}
footer.site.ft--light .addr a{color:var(--p)}
footer.site.ft--light .cols{border-bottom-color:var(--line)}
footer.site.ft--light .legal{color:var(--muted)}
footer.site.ft--cta .ft-cta{background:linear-gradient(135deg,var(--p),var(--pd))}
.ft-cta{padding:40px 0;margin-bottom:44px}
.ft-cta__in{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}
.ft-cta h3{color:#fff;margin:0 0 4px;font-size:clamp(1.3rem,2.4vw,1.8rem)}
.ft-cta p{color:rgba(255,255,255,.88);margin:0}
.ft-cta__btns{display:flex;gap:16px;flex-wrap:wrap}
footer.site.ft--center{text-align:center;background:var(--soft);color:var(--muted);border-top:1px solid var(--line)}
footer.site.ft--center .flogo{justify-content:center;color:var(--ink);font-size:1.3rem}
footer.site.ft--center .ft-tag{max-width:52ch;margin:0 auto 18px}
footer.site.ft--center .ft-inline{display:flex;flex-wrap:wrap;gap:6px 22px;justify-content:center;margin:0 auto 18px;max-width:820px}
footer.site.ft--center .ft-inline a{color:var(--muted);padding:3px 0;font-weight:600}
footer.site.ft--center .ft-inline a:hover{color:var(--p)}
footer.site.ft--center .addr{color:var(--muted)}
footer.site.ft--center .addr a{color:var(--p)}
footer.site.ft--center .legal{justify-content:center;border-top:1px solid var(--line);margin-top:22px}
footer.site.ft--split .ft-split{display:grid;grid-template-columns:1.1fr 1.9fr;gap:40px;padding-bottom:34px;border-bottom:1px solid rgba(255,255,255,.1)}
footer.site.ft--split .ft-panel{background:var(--pd);border-radius:calc(var(--radius) + 4px);padding:28px}
footer.site.ft--split .ft-panel .btn{margin-top:8px}
footer.site.ft--split .ft-links{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
/* restore .btn styling inside footers (base "footer.site a" would clobber it) */
footer.site a.btn{display:inline-flex;padding:14px 26px;font-size:1rem}
footer.site a.btn--primary,footer.site a.btn--primary:hover{color:var(--on-accent)}
footer.site a.btn--ghost,footer.site a.btn--ghost:hover{color:#fff}
/* inner page */
.page-hero{background:linear-gradient(155deg,var(--pd),var(--p));color:#fff;padding:52px 0}
.page-hero .crumb{font-size:.85rem;color:rgba(255,255,255,.7);margin-bottom:10px}
.page-hero .crumb a{color:rgba(255,255,255,.85)}
.page-hero h1{color:#fff;margin:0}
.article{display:grid;grid-template-columns:1fr 320px;gap:48px;padding:56px 0}
.article .body>h2{margin-top:1.8em}
.article .body>h2:first-child{margin-top:0}
.article .body img{border-radius:14px;margin:1.2em 0}
.article .body ul,.article .body ol{padding-left:1.2em}
.article .body li{margin:.35em 0}
.article .tw{overflow-x:auto;margin:1.4em 0}
.aside{position:sticky;top:96px;align-self:start}
.qcard{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:26px;text-align:center}
.qcard h3{margin:0 0 8px}
.qcard p{color:var(--muted);font-size:.94rem}
.qcard .tel{font-family:var(--disp);font-weight:800;font-size:1.5rem;color:var(--p);display:block;margin:8px 0 16px}
.qcard .btn{width:100%;justify-content:center;margin-bottom:10px}
.article .faq{margin:1.4em 0 0}
/* GoHighLevel quote form embed (+ shimmer skeleton) */
.quote-embed{padding:clamp(1.6rem,3.5vw,2.8rem) 0;background:var(--soft)}
.quote-embed .wrap{max-width:1080px;margin:0 auto;padding:0 clamp(20px,4vw,44px)}
.quote-embed__h{font-family:var(--disp);margin:0 0 1rem;font-weight:700;font-size:clamp(1.4rem,2.6vw,2rem)}
.quote-embed__box{position:relative;min-height:720px;border-radius:16px;overflow:hidden;background:#fff;box-shadow:var(--shadow)}
.quote-embed__frame{position:relative;z-index:1;display:block;width:100%;min-height:720px;border:0;background:transparent}
.quote-embed__skel{position:absolute;inset:0;z-index:0;display:flex;flex-direction:column;gap:12px;padding:clamp(20px,4vw,30px);transition:opacity .4s ease}
.quote-embed__box.is-loaded .quote-embed__skel{opacity:0}
.sk-f{display:flex;flex-direction:column;gap:6px}
.sk-r{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.sk-l,.sk-i,.sk-btn{border-radius:6px;background:linear-gradient(90deg,#e9e9e9 25%,#f5f5f5 37%,#e9e9e9 63%);background-size:400% 100%;animation:sk 1.4s ease infinite}
.sk-l{height:10px;width:32%}
.sk-i{height:40px}
.sk-i--area{height:88px}
.sk-i--cb{height:14px;width:82%}
.sk-btn{height:44px;width:100%;margin-top:4px}
@keyframes sk{0%{background-position:100% 0}100%{background-position:-100% 0}}
/* animations — page load + scroll reveal (gated on .anim, respects reduced-motion) */
@media (prefers-reduced-motion: no-preference){
  html.anim .reveal{opacity:0;transform:translateY(22px);transition:opacity .6s ease,transform .7s cubic-bezier(.2,.75,.25,1)}
  html.anim .reveal.in{opacity:1;transform:none}
  html.anim .top{animation:aFade .6s ease both}
  html.anim header.site{animation:aDrop .55s cubic-bezier(.2,.75,.25,1) both}
  html.anim .hero__copy>*{opacity:0;animation:aUp .7s cubic-bezier(.2,.75,.25,1) forwards}
  html.anim .hero__copy>*:nth-child(1){animation-delay:.15s}
  html.anim .hero__copy>*:nth-child(2){animation-delay:.27s}
  html.anim .hero__copy>*:nth-child(3){animation-delay:.39s}
  html.anim .hero__copy>*:nth-child(4){animation-delay:.51s}
  html.anim .hero__copy>*:nth-child(5){animation-delay:.63s}
  html.anim .hero__media{opacity:0;animation:aPop .8s cubic-bezier(.2,.75,.25,1) .35s forwards}
  html.anim .page-hero>.wrap>*{opacity:0;animation:aUp .6s cubic-bezier(.2,.75,.25,1) forwards}
  html.anim .page-hero>.wrap>*:nth-child(2){animation-delay:.1s}
}
@keyframes aUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}
@keyframes aFade{from{opacity:0}to{opacity:1}}
@keyframes aPop{from{opacity:0;transform:scale(.96) translateY(10px)}to{opacity:1;transform:none}}
@keyframes aDrop{from{transform:translateY(-14px);opacity:0}to{transform:none;opacity:1}}
/* responsive */
@media(max-width:1120px){
  nav.main{display:none;position:absolute;top:100%;left:0;right:0;background:#fff;border-bottom:1px solid var(--line);flex-direction:column;align-items:stretch;padding:12px;gap:2px;box-shadow:var(--shadow-lg);max-height:calc(100vh - 70px);overflow-y:auto}
  nav.main.open{display:flex}
  /* pill-nav variant: reset the desktop pill so the mobile panel isn't a giant ellipse */
  .lay-nav-pill nav.main{border-radius:0;padding:12px;gap:2px;background:#fff}
  .lay-nav-pill nav.main>a,.lay-nav-pill .nav-item>button{border-radius:10px;padding:12px 14px}
  nav.main>a,.nav-item>button{width:100%;text-align:left;font-size:1rem;padding:12px 14px}
  .nav-item{position:static}
  .mega{position:static;transform:none;opacity:1;visibility:visible;box-shadow:none;border:0;padding:2px 10px 12px;min-width:0;left:auto}
  .nav-item:hover .mega,.nav-item.open .mega{transform:none;left:auto}
  .mega--areas{min-width:0;grid-template-columns:1fr}
  .nav-item .mega{display:none}.nav-item.open .mega{display:block}
  .nav-cta-m{display:block}
  .nav-quote{display:block;background:var(--accent);color:var(--on-accent);text-align:center;font-weight:700;margin-top:10px;padding:13px}
  .brand{margin-right:auto}
  .burger{display:block;order:3}
  .hd .btn{display:none}
  .hd .tel{display:none}
}
@media(max-width:720px){
  .top .wrap{gap:10px;font-size:.8rem;justify-content:center}
  .top span,.top .dot{display:none}
  .top a:not([href^="tel"]){display:none}
}
@media(max-width:960px){
  .hero--split .wrap{grid-template-columns:1fr;gap:32px;padding:52px 24px}
  .hero--split .hero__media{order:-1}
  .hero--overlap .wrap{margin-top:-90px}
  .trust .wrap{grid-template-columns:repeat(2,1fr);gap:16px}
  .g4{grid-template-columns:repeat(2,1fr)}
  .g3,.steps{grid-template-columns:1fr}
  .article{grid-template-columns:1fr}
  .aside{position:static}
  footer.site .cols{grid-template-columns:1fr 1fr}
  footer.site.ft--split .ft-split{grid-template-columns:1fr}
  .ft-cta__in{flex-direction:column;align-items:flex-start}
}
@media(max-width:560px){
  body{font-size:16px}
  .sec{padding:52px 0}
  .wrap{padding:0 18px}
  .g4,.g3{grid-template-columns:1fr}
  .scards--side{grid-template-columns:1fr}
  .trust .wrap{grid-template-columns:1fr}
  .cta-band{padding:34px 20px}
  .hero h1{font-size:2rem}
  .hero .cta .btn,.cta-band .cta .btn{width:100%;justify-content:center}
  .brand small{display:none}
  footer.site .cols{grid-template-columns:1fr}
  footer.site.ft--split .ft-links{grid-template-columns:1fr}
}
"""

NAVJS = """(function(){
 var b=document.querySelector('.burger'),n=document.querySelector('nav.main');
 if(b)b.addEventListener('click',function(){n.classList.toggle('open')});
 document.querySelectorAll('.nav-item>button').forEach(function(btn){
   btn.addEventListener('click',function(e){
     if(window.matchMedia('(max-width:960px)').matches){e.preventDefault();btn.parentNode.classList.toggle('open')}
   });
 });
 // scroll-reveal entrance animations
 (function(){
   var root=document.documentElement;
   if(!root.classList.contains('anim')) return;
   if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
   var sel='.sec-head,.scard,.feat,.step,.pricewrap,.areas a,.cta-band,.faq details,'+
           '.article .body>h2,.article .body>h3,.article .body>p,.article .body>ul,.article .body>ol,'+
           '.article .body>.tw,.article .body>.faq,.article .body>img,.aside';
   var els=[].slice.call(document.querySelectorAll(sel));
   if(!els.length) return;
   els.forEach(function(el){el.classList.add('reveal')});
   // stagger items inside grids/lists
   [].forEach.call(document.querySelectorAll('.grid,.steps,.areas,.faq'),function(g){
     var i=0;[].forEach.call(g.children,function(c){if(c.classList.contains('reveal')){c.style.transitionDelay=(Math.min(i,6)*80)+'ms';i++;}});
   });
   function showAll(){els.forEach(function(el){el.classList.add('in')});}
   if(!('IntersectionObserver' in window)){showAll();return;}
   var io=new IntersectionObserver(function(ents){
     ents.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});
   },{threshold:0.08,rootMargin:'0px 0px -5% 0px'});
   els.forEach(function(el){io.observe(el)});
   // safety net: never leave content hidden if the observer never fires
   setTimeout(showAll,2600);
 })();
})();"""

# ------------------------------------------------------------------ GHL quote form
QUOTE_EMBED_TMPL = """<section class="quote-embed"><div class="wrap"><h2 class="quote-embed__h">Request a quote</h2>
<div class="quote-embed__box"><div class="quote-embed__skel" aria-hidden="true">
<div class="sk-f"><span class="sk-l"></span><span class="sk-i"></span></div>
<div class="sk-f"><span class="sk-l"></span><span class="sk-i"></span></div>
<div class="sk-f"><span class="sk-l"></span><span class="sk-i"></span></div>
<div class="sk-f"><span class="sk-l"></span><span class="sk-i"></span></div>
<div class="sk-f"><span class="sk-l"></span><span class="sk-i"></span></div>
<div class="sk-r"><div class="sk-f"><span class="sk-l"></span><span class="sk-i"></span></div>
<div class="sk-f"><span class="sk-l"></span><span class="sk-i"></span></div></div>
<div class="sk-f"><span class="sk-l"></span><span class="sk-i"></span></div>
<div class="sk-f"><span class="sk-l"></span><span class="sk-i sk-i--area"></span></div>
<span class="sk-i sk-i--cb"></span><span class="sk-btn"></span></div>
<iframe class="quote-embed__frame" src="https://api.leadconnectorhq.com/widget/form/__FID__"
 title="Request a Quote" scrolling="no" id="inline-__FID__" data-form-id="__FID__"
 data-layout='{"id":"INLINE"}' data-height="640"
 onload="this.closest('.quote-embed__box').classList.add('is-loaded')"></iframe>
</div></div></section>
<script src="https://link.msgsndr.com/js/form_embed.js" defer></script>"""

def quote_embed(form_id):
    return QUOTE_EMBED_TMPL.replace("__FID__", form_id or GHL_FORM_ID)

# ------------------------------------------------------------------ logo
def favicon_svg(t):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44">'
            f'<rect width="44" height="44" rx="10" fill="{t["p"]}"/>'
            f'<rect x="12" y="9" width="20" height="17" rx="3" fill="#fff"/>'
            f'<rect x="20.2" y="26" width="3.6" height="10" rx="1.6" fill="{t["accent"]}"/>'
            f'<circle cx="27.5" cy="17.5" r="2.3" fill="{t["accent"]}"/></svg>')

def logo_mark(t, ctx="header"):
    mode = t.get("logo_mode")
    if mode == "full":
        # whole lockup (baked-in name is too small to read on its own -> pair with wordmark)
        box = "brand__full brand__full--ft" if ctx == "footer" else "brand__full"
        return f'<span class="{box}"><img src="/assets/logo-full.png" alt="{t["city"]} Porta Pros logo"></span>'
    if mode == "text":
        # no usable brand mark -> text wordmark only, no chip
        return ""
    return (f'<span class="brand__chip"><img src="/assets/logo-mark.png" '
            f'alt="{t["city"]} Porta Pros logo" width="40" height="40"></span>')

def wordmark(t):
    """Readable business name shown beside the logo (every mode)."""
    return f'<span>{t["city"]} Porta Pros<small>{t["tagline"]}</small></span>'

# ------------------------------------------------------------------ header/footer
def header(site, pages, suburbs=None):
    t = site
    present = pages
    suburbs = suburbs or []
    menu_html = ""
    for name, slugs in MENU:
        links = "".join(f'<a href="/{s}/">{label_for(s, present)}</a>' for s in slugs if f"/{s}/" in present)
        if links:
            menu_html += f'<div class="nav-item"><button type="button">{name}</button><div class="mega">{links}</div></div>'
    # Service Areas: dropdown of suburbs (from the master sheet where provided)
    if suburbs:
        all_link = ('<a class="mega-all" href="/service-areas/">All Service Areas</a>'
                    if "/service-areas/" in present else "")
        sub_links = "".join(f'<a href="{u}">{suburb_label(u, present)}</a>' for u in suburbs)
        areas = (f'<div class="nav-item"><button type="button">Service Areas</button>'
                 f'<div class="mega mega--areas">{all_link}{sub_links}</div></div>')
    elif "/service-areas/" in present:
        areas = '<a href="/service-areas/">Service Areas</a>'
    else:
        areas = ""
    about = '<a href="/about/">About</a>' if "/about/" in present else ""
    contact = '<a href="/contact/">Contact</a>' if "/contact/" in present else ""
    top_links = (('<span class="dot">&bull;</span>' + about) if about else "") + \
                (('<span class="dot">&bull;</span>' + contact) if contact else "")
    # mobile-menu items — only emit when the page exists (else the dead-link
    # fixer would strip the anchor and leave orphan text visible on desktop)
    about_m = '<a class="nav-cta-m" href="/about/">About</a>' if "/about/" in present else ""
    contact_m = '<a class="nav-cta-m" href="/contact/">Contact</a>' if "/contact/" in present else ""
    quote_m = ('<a class="nav-quote" href="/request-a-quote/">Request a Quote</a>'
               if "/request-a-quote/" in present else "")
    return f"""<div class="top"><div class="wrap"><span>Serving {t['city']} &amp; the surrounding metro</span><span class="dot">&bull;</span><span>Same-day &amp; next-day delivery</span><span class="tsp"></span><a href="tel:{t['tel']}">{icon('phone')}{t['phone']}</a>{top_links}</div></div>
<header class="site"><div class="wrap hd">
<a class="brand" href="/">{logo_mark(t)}{wordmark(t)}</a>
<button class="burger" aria-label="Menu"><span></span><span></span><span></span></button>
<nav class="main">{menu_html}{areas}{about_m}{contact_m}{quote_m}</nav>
<a class="btn btn--primary" href="/request-a-quote/">Free Quote</a>
</div></header>"""

def footer(site, pages, suburbs):
    t = site; present = pages
    variant = t.get("layout", {}).get("footer", "dark")
    def fl(u, label):
        return f'<a href="{u}">{label}</a>' if u in present else ""
    services = (fl("/portable-toilet-rental/", "Portable Toilets") + fl("/restroom-trailer-rental/", "Restroom Trailers")
                + fl("/roll-off-dumpster-rental/", "Dumpster Rental") + fl("/event-restroom-rental/", "Event Restrooms")
                + fl("/construction-site-services/", "Construction Services"))
    company = (fl("/about/", "About Us") + fl("/contact/", "Contact") + fl("/service-areas/", "Service Areas")
               + fl("/porta-potty-rental-cost/", "Pricing") + fl("/request-a-quote/", "Request a Quote"))
    area_links = "".join(f'<a href="{u}">{suburb_label(u, present)}</a>' for u in suburbs[:8])
    zippart = f" {t['zip']}" if t["zip"] else ""
    addr = f"{t['street']}, {t['city']}, {t['st']}{zippart}"
    logo = logo_mark(t, "footer")
    flogo_html = logo + f'{t["city"]} Porta Pros'
    blurb = (f"Portable toilets, restroom trailers, dumpsters and site services delivered on "
             f"time across {t['city']} and nearby.")
    brand_block = (f'<div class="fbrand"><div class="flogo">{flogo_html}</div>'
                   f'<p>{blurb}</p><address class="addr">{addr}<br>'
                   f'<a href="tel:{t["tel"]}">{t["phone"]}</a></address></div>')
    cols = (f'<div><h4>Services</h4>{services}</div><div><h4>Company</h4>{company}</div>'
            f'<div><h4>Service Areas</h4>{area_links}</div>')
    legal = (f'<div class="legal"><span>&copy; {t["city"]} Porta Pros. All rights reserved.</span>'
             f'<span>{addr}</span></div>')
    js = '<script src="/assets/nav.js" defer></script>'

    if variant == "center":
        inline = services + company
        return (f'<footer class="site ft--center"><div class="wrap">'
                f'<div class="flogo">{flogo_html}</div>'
                f'<p class="ft-tag">{blurb}</p>'
                f'<nav class="ft-inline">{inline}</nav>'
                f'<address class="addr">{addr} &middot; <a href="tel:{t["tel"]}">{t["phone"]}</a></address>'
                f'{legal}</div></footer>{js}')

    if variant == "cta":
        cta = (f'<div class="ft-cta"><div class="wrap ft-cta__in"><div>'
               f'<h3>Speak to {t["city"]} dispatch</h3>'
               f'<p>Same-day and next-day delivery across {t["city"]} &mdash; call for a fast quote.</p></div>'
               f'<div class="ft-cta__btns"><a class="btn btn--primary" href="tel:{t["tel"]}">{icon("phone")}Call {t["phone"]}</a></div></div></div>')
        return (f'<footer class="site ft--cta">{cta}<div class="wrap">'
                f'<div class="cols">{brand_block}{cols}</div>{legal}</div></footer>{js}')

    if variant == "split":
        return (f'<footer class="site ft--split"><div class="wrap"><div class="ft-split">'
                f'<div class="ft-panel"><div class="flogo">{flogo_html}</div>'
                f'<p>{blurb}</p><address class="addr">{addr}<br><a href="tel:{t["tel"]}">{t["phone"]}</a></address>'
                f'<a class="btn btn--primary" href="/request-a-quote/">Get a Free Quote</a></div>'
                f'<div class="ft-links">{cols}</div></div>{legal}</div></footer>{js}')

    # dark / brand / light share the 4-column structure (styled by class)
    return (f'<footer class="site ft--{variant}"><div class="wrap">'
            f'<div class="cols">{brand_block}{cols}</div>{legal}</div></footer>{js}')

def label_for(slug, present):
    p = present.get(f"/{slug}/")
    if p:
        return html.escape(re.sub(r"\s+in\s+.*$", "", p["meta"].get("h1", slug)).split(" | ")[0])
    return slug.replace("-", " ").title()

def suburb_label(u, present):
    """'Rumford, RI' style label for a suburb page (from its H1 or its slug)."""
    p = present.get(u)
    if p:
        m = re.search(r"\bin\s+(.+)$", p["meta"].get("h1", ""))
        if m:
            return html.escape(m.group(1).split("|")[0].strip())
    s = u.strip("/").replace("porta-potty-rental-", "")
    parts = s.rsplit("-", 1)
    if len(parts) == 2 and len(parts[1]) == 2:
        return html.escape(parts[0].replace("-", " ").title() + ", " + parts[1].upper())
    return html.escape(s.replace("-", " ").title())

# ------------------------------------------------------------------ SEO / schema
def clean_text(md):
    """Plain-text (for schema/llms) from a markdown fragment."""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    t = re.sub(r"[#>*`_]", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def seo_title(raw, brand):
    """Keep titles <=60 chars: drop the brand suffix first, then truncate."""
    raw = (raw or "").strip()
    if len(raw) <= 60:
        return raw
    base = raw.split(" | ")[0].strip()
    if len(base) <= 60:
        return base
    return base[:57].rstrip() + "…"

def org_schema(site):
    t = site
    addr = {"@type": "PostalAddress", "streetAddress": t["street"],
            "addressLocality": t["city"], "addressRegion": t["st"]}
    if t["zip"]:
        addr["postalCode"] = t["zip"]
    return {"@type": "LocalBusiness", "@id": f"https://{t['domain']}/#business",
            "name": f"{t['city']} Porta Pros", "url": f"https://{t['domain']}/",
            "telephone": t["phone"], "priceRange": "$$",
            "image": f"https://{t['domain']}/assets/photos/portable-toilet-rental.webp",
            "logo": f"https://{t['domain']}/assets/logo-mark.png",
            "address": addr, "areaServed": {"@type": "City", "name": f"{t['city']}, {t['st']}"}}

def faq_schema(faqs):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": clean_text(q),
         "acceptedAnswer": {"@type": "Answer", "text": clean_text(a)}} for q, a in faqs]}

def service_schema(site, h1, url):
    return {"@type": "Service", "name": h1, "serviceType": h1,
            "provider": {"@id": f"https://{site['domain']}/#business"},
            "areaServed": {"@type": "City", "name": f"{site['city']}, {site['st']}"},
            "url": f"https://{site['domain']}{url}"}

def breadcrumb_schema(site, h1, url):
    b = f"https://{site['domain']}"
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": b + "/"},
        {"@type": "ListItem", "position": 2, "name": h1, "item": b + url}]}

def synth_service_faq(site, h1, label):
    c = site["city"]
    return [
        (f"Do you deliver {label.lower()} in {c}?",
         f"Yes. {c} Porta Pros delivers {label.lower()} across {c} and the surrounding metro, with same-day and next-day drop-off available on most orders."),
        (f"How much does {label.lower()} cost in {c}?",
         f"Pricing depends on the unit and how long you need it. See our [cost breakdown](/porta-potty-rental-cost/) and [request a free quote](/request-a-quote/) for an exact figure."),
        ("How does servicing work?",
         "Standard rentals include scheduled service — a pump-out, a clean, a restock and fresh deodorizer. Busy or hot-weather sites can be serviced more often."),
    ]

# ------------------------------------------------------------------ pages
def hero_section(t, h1, lead, heroimg):
    """Distinct hero markup per site layout (split-right/left, stacked, center, banner, overlap)."""
    variant = t.get("layout", {}).get("hero", "split-right")
    ph = icon("phone")
    call = f'<a class="btn btn--primary" href="tel:{t["tel"]}">{ph}Call {t["phone"]}</a>'
    quote = '<a class="btn btn--ghost" href="/request-a-quote/">Get a Free Quote</a>'
    eyebrow = f'<p class="eyebrow">{html.escape(t["city"])}, {html.escape(t["st"])} &middot; Porta Potty Rental</p>'
    leadh = f'<p class="lead">{html.escape(lead)}</p>'
    chips = ('<ul class="chips">'
             f'<li>{icon("check")}Same-day delivery</li><li>{icon("check")}Weekly service included</li>'
             f'<li>{icon("check")}Clean, stocked units</li><li>{icon("check")}No hidden fees</li></ul>')
    copy = (f'<div class="hero__copy">{eyebrow}<h1>{html.escape(h1)}</h1>{leadh}'
            f'<div class="cta">{call}{quote}</div>{chips}</div>')
    alt = f'Porta potty rental in {html.escape(t["city"])}, {html.escape(t["st"])}'
    src = f'/assets/photos/{heroimg}.webp'
    badge = f'<div class="hero__badge">{icon("star")}<div><b>5&#9733;</b><span>Local service</span></div></div>'
    media = f'<div class="hero__media"><img src="{src}" alt="{alt}" fetchpriority="high">{badge}</div>'

    if variant == "split-left":
        return f'<section class="hero hero--split hero--left"><div class="wrap">{media}{copy}</div></section>'
    if variant == "stacked":
        wide = f'<div class="hero__media--wide"><img src="{src}" alt="{alt}" fetchpriority="high"></div>'
        return f'<section class="hero hero--stacked"><div class="wrap">{copy}{wide}</div></section>'
    if variant == "center":
        return f'<section class="hero hero--center" style="--hero-bg:url({src})"><div class="wrap">{copy}</div></section>'
    if variant == "banner":
        return f'<section class="hero hero--banner" style="--hero-bg:url({src})"><div class="wrap">{copy}</div></section>'
    if variant == "overlap":
        return (f'<section class="hero hero--overlap"><div class="hero__bgimg"><img src="{src}" alt="{alt}" fetchpriority="high"></div>'
                f'<div class="wrap"><div class="hero__card">{copy}</div></div></section>')
    return f'<section class="hero hero--split hero--right"><div class="wrap">{copy}{media}</div></section>'

def head_html(site, title, desc, url, schemas):
    t = site
    lay = t.get("layout", {})
    bodycls = f'lay-nav-{lay.get("nav", "left")} lay-bands-{lay.get("bands", "alt")} shape-{lay.get("shape", "pill")}'
    graph = {"@context": "https://schema.org", "@graph": schemas}
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<script>document.documentElement.classList.add('anim')</script>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="https://{t['domain']}{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{t['city']} Porta Pros">
<meta property="og:url" content="https://{t['domain']}{url}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="https://{t['domain']}/assets/photos/portable-toilet-rental.webp">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{html.escape(desc)}">
<meta name="twitter:image" content="https://{t['domain']}/assets/photos/portable-toilet-rental.webp">
<link rel="icon" type="image/png" href="/assets/favicon.png">
<link rel="apple-touch-icon" href="/assets/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={t['fonts']}&display=swap">
<link rel="stylesheet" href="/assets/site.css">
<script type="application/ld+json">{json.dumps(graph)}</script>
</head><body class="{bodycls}">"""

def home_page(site, home, service_pages, suburbs, pages):
    t = site
    pre, secs = split_sections(home["body"])
    lead = first_para(pre) or home["meta"].get("meta_description", "")
    heroimg = img_for("", "portable-toilet-rental")

    # services grid
    curated = [s for s in CURATED if f"/{s}/" in pages][:9]
    if len(curated) < 6:
        curated += [u.strip("/") for u in pages if pages[u]["cat"] == "service" and u.strip("/") not in curated][:9-len(curated)]
    cards = ""
    for s in curated[:9]:
        p = pages[f"/{s}/"]
        blurb = short(re.sub(r"\s*(in|near)\s+.*$", "", p["meta"].get("meta_description", "").split(".")[0]))
        cards += f"""<a class="scard" href="/{s}/"><img src="/assets/photos/{img_for(s)}.webp" alt="{label_for(s, pages)} in {t['city']}" loading="lazy"><div class="scard__b"><h3>{label_for(s, pages)}</h3><p>{html.escape(blurb)}</p><span class="more">Learn more {icon('arrow')}</span></div></a>"""

    # pricing table from home body
    price_html = ""
    mt = re.search(r"(?m)^(\|.+\|\n\|[\s:|-]+\|\n(?:\|.+\|\n?)+)", home["body"])
    if mt:
        price_html = f"""<section class="sec sec--soft"><div class="wrap"><div class="sec-head"><p class="eyebrow">Straightforward Pricing</p><h2>{t['city']} porta potty rental rates</h2><p>Real numbers, no surprises. Delivery, weekly service and pickup are spelled out on your quote.</p></div><div class="pricewrap">{render_md(mt.group(1))}<p class="pricenote">Weekend and monthly rates available. <a href="/porta-potty-rental-cost/">See full pricing →</a></p></div></div></section>"""

    # features
    feats = [("clock", "On-time delivery", "Order by early afternoon and most drops go out same or next day."),
             ("sparkle", "Clean, stocked units", "Every rental includes scheduled service, restock and deodorizing."),
             ("shield", "OSHA &amp; ADA ready", "Correct unit counts and accessible options for compliant job sites."),
             ("tag", "Transparent pricing", "Flat, written quotes with delivery and service broken out."),
             ("truck", "Local crew", f"One {t['city']} team handles drop-off, service and pickup."),
             ("calendar", "Flexible terms", "Daily, weekly, monthly and event rentals — scale up any time.")]
    feat_html = "".join(f'<div class="feat"><div class="ic">{icon(ic)}</div><div class="feat__b"><h3>{h}</h3><p>{d}</p></div></div>' for ic, h, d in feats)

    # feature story blocks from real content sections (image + text alternating)
    story_imgs = [img_for("construction-site-services"), img_for("event-restroom-rental"), img_for("restroom-trailer-rental")]
    stories = ""
    prose = [(ti, md) for ti, md in secs if "frequently asked" not in ti.lower()][:2]

    # areas
    area_html = ""
    if suburbs:
        chips = "".join(f'<a href="{u}">{label_for(u.strip("/"), pages)}</a>' for u in suburbs[:14])
        alllink = '<a href="/service-areas/">View all areas →</a>' if "/service-areas/" in pages else ""
        area_html = f"""<section class="sec"><div class="wrap"><div class="sec-head"><p class="eyebrow">Where We Deliver</p><h2>Serving {t['city']} &amp; nearby communities</h2><p>Fast local delivery across the metro. Not sure if we reach you? Just ask.</p></div><div class="areas">{chips}{alllink}</div></div></section>"""

    # faq
    faq_html = ""
    faqsec = next((md for ti, md in secs if "frequently asked" in ti.lower()), "")
    faqs = parse_faq(faqsec)[:6]
    if faqs:
        items = "".join(f'<details{" open" if i==0 else ""}><summary>{_inline(q)}</summary><div class="a">{render_md(a)}</div></details>' for i, (q, a) in enumerate(faqs))
        faq_html = f"""<section class="sec sec--soft"><div class="wrap"><div class="sec-head"><p class="eyebrow">Good to Know</p><h2>Frequently asked questions</h2></div><div class="faq">{items}</div></div></section>"""

    stats = f"""<section class="trust"><div class="wrap">
<div>{icon('clock')}<span><b>Same-day</b> dispatch available</span></div>
<div>{icon('shield')}<span>Licensed &amp; <b>fully insured</b></span></div>
<div>{icon('sparkle')}<span><b>Weekly</b> service included</span></div>
<div>{icon('star')}<span><b>Trusted</b> by local crews</span></div>
</div></section>"""

    stepstyle = t.get("layout", {}).get("steps", "cards")
    steps = f"""<section class="sec"><div class="wrap"><div class="sec-head"><p class="eyebrow">How It Works</p><h2>Renting is three easy steps</h2></div><div class="steps steps--{stepstyle}">
<div class="step"><div class="step__b"><h3>Get a fast quote</h3><p>Tell us the location, dates and headcount. We size the order and send a written price.</p></div></div>
<div class="step"><div class="step__b"><h3>We deliver &amp; place</h3><p>Our crew drops and sets each unit exactly where you need it, on your schedule.</p></div></div>
<div class="step"><div class="step__b"><h3>We service &amp; pick up</h3><p>Scheduled cleaning keeps units fresh; we collect the moment you're done.</p></div></div>
</div></div></section>"""

    quote = f"""<section class="sec"><div class="wrap"><div class="cta-band"><h2>Ready to book your {t['city']} rental?</h2><p>Call now or request a free quote — most orders placed by early afternoon go out same or next day.</p><div class="cta"><a class="btn btn--primary" href="tel:{t['tel']}">{icon('phone')}Call {t['phone']}</a><a class="btn btn--ghost" href="/request-a-quote/">Request a Quote</a></div></div></div></section>"""

    hero = hero_section(t, home["meta"].get("h1", f'Porta Potty Rental in {t["city"]}'), lead, heroimg)

    cardstyle = t.get("layout", {}).get("cards", "classic")
    services = f"""<section class="sec sec--soft"><div class="wrap"><div class="sec-head"><p class="eyebrow">What We Rent</p><h2>Units &amp; services for every job</h2><p>From a single backyard unit to a full event or construction site — we have the right equipment.</p></div><div class="grid g3 scards scards--{cardstyle}">{cards}</div></div></section>"""

    featstyle = t.get("layout", {}).get("feats", "tiles")
    features = f"""<section class="sec"><div class="wrap"><div class="sec-head"><p class="eyebrow">Why {t['city']} Chooses Us</p><h2>Reliable service, honest pricing</h2></div><div class="grid g3 feats feats--{featstyle}">{feat_html}</div></div></section>"""

    title = seo_title(home["meta"].get("title_tag", f"Porta Potty Rental in {t['city']}, {t['st']}"),
                      f"{t['city']} Porta Pros")
    desc = home["meta"].get("meta_description", "")
    schemas = [org_schema(t)]
    if faqs:
        schemas.append(faq_schema(faqs))
    return (head_html(t, title, desc, "/", schemas) + header(t, pages, suburbs) + hero + stats + services
            + features + steps + price_html + area_html + faq_html + quote
            + footer(t, pages, suburbs) + "</body></html>")

def inner_page(site, page, suburbs, pages):
    t = site
    meta = page["meta"]; h1 = meta.get("h1", ""); url = page["url"]
    pre, secs = split_sections(page["body"])
    # build body: intro + sections; FAQ as accordion
    parts = []
    if pre.strip():
        parts.append(render_md(pre))
    hero_img = img_for(url.strip("/"), "portable-toilet-rental")
    inserted = False
    faqs_used = []
    for idx, (ti, md) in enumerate(secs):
        if "frequently asked" in ti.lower():
            faqs = parse_faq(md)
            if faqs:
                faqs_used = faqs
                items = "".join(f'<details{" open" if i==0 else ""}><summary>{_inline(q)}</summary><div class="a">{render_md(a)}</div></details>' for i, (q, a) in enumerate(faqs))
                parts.append(f'<h2 id="faq">{_inline(ti)}</h2><div class="faq">{items}</div>')
            else:
                parts.append(f'<h2 id="{slugify(ti)}">{_inline(ti)}</h2>{render_md(md)}')
            continue
        parts.append(f'<h2 id="{slugify(ti)}">{_inline(ti)}</h2>{render_md(md)}')
        if not inserted and idx == 0 and page["cat"] in ("service", "money"):
            parts.append(f'<img src="/assets/photos/{hero_img}.webp" alt="{html.escape(h1)}" loading="lazy">')
            inserted = True

    # AEO: ensure service pages carry a short FAQ (+ FAQPage schema)
    if not faqs_used and page["cat"] == "service":
        label = re.sub(r"\s+in\s+.*$", "", h1).strip() or "porta potty rental"
        faqs_used = synth_service_faq(t, h1, label)
        items = "".join(f'<details{" open" if i==0 else ""}><summary>{_inline(q)}</summary><div class="a">{render_md(a)}</div></details>' for i, (q, a) in enumerate(faqs_used))
        parts.append(f'<h2 id="faq">Frequently asked questions</h2><div class="faq">{items}</div>')

    crumb = f'<div class="crumb"><a href="/">Home</a> › {html.escape(h1)}</div>'
    aside = f"""<aside class="aside"><div class="qcard">{icon('phone')}<h3>Get a free quote</h3><p>Fast answers, real pricing, on-time delivery in {t['city']}.</p><a class="tel" href="tel:{t['tel']}">{t['phone']}</a><a class="btn btn--primary" href="/request-a-quote/">Request a Quote</a><a class="btn btn--outline" href="/service-areas/">Service Areas</a></div></aside>"""

    embed = quote_embed(t.get("ghl_form_id")) if url == "/request-a-quote/" else ""
    body = f"""<section class="page-hero"><div class="wrap">{crumb}<h1>{html.escape(h1)}</h1></div></section>
{embed}
<div class="wrap"><div class="article"><div class="body">{''.join(parts)}</div>{aside}</div></div>
<section class="sec" style="padding-top:0"><div class="wrap"><div class="cta-band"><h2>Book your {t['city']} rental today</h2><p>Call now or request a free quote — clean units, on-time delivery, transparent pricing.</p><div class="cta"><a class="btn btn--primary" href="tel:{t['tel']}">{icon('phone')}Call {t['phone']}</a><a class="btn btn--ghost" href="/request-a-quote/">Request a Quote</a></div></div></div></section>"""

    title = seo_title(meta.get("title_tag", h1), f"{t['city']} Porta Pros")
    schemas = [org_schema(t), breadcrumb_schema(t, h1, url)]
    if page["cat"] == "service":
        schemas.append(service_schema(t, re.sub(r"\s+in\s+.*$", "", h1).strip() or h1, url))
    if faqs_used:
        schemas.append(faq_schema(faqs_used))
    return (head_html(t, title, meta.get("meta_description", ""), url, schemas) + header(t, pages, suburbs)
            + body + footer(t, pages, suburbs) + "</body></html>")

# ------------------------------------------------------------------ link hygiene
def fix_links(html_str, valid_urls):
    """Neutralize internal links whose target page doesn't exist (keep the text).
    Prevents 404s from template or content links to pages a given site lacks."""
    def repl(m):
        href, inner = m.group(1), m.group(2)
        if href.startswith("/") and not href.startswith("/assets/"):
            path = href.split("#")[0].split("?")[0]
            if path and path != "/" and not path.endswith("/"):
                path += "/"
            if path and path not in valid_urls:
                return inner
        return m.group(0)
    return re.sub(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>', repl, html_str, flags=re.S)

# ------------------------------------------------------------------ build
def build():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    cards = []
    catmap = {"01-money-pages": "money", "02-service-lines": "service", "03-guides": "guide",
              "04-suburbs": "suburb", "05-trust": "trust"}
    for domain, cfg in SITES.items():
        cdir = os.path.join(ROOT, domain, "content")
        if not os.path.isdir(cdir):
            print("  skip:", domain); continue
        phone = cfg.get("phone_override") or f"({cfg['area']}) 555-0100"
        digits = re.sub(r"\D", "", phone)
        tel = "+1" + digits if len(digits) == 10 else "+" + digits
        site = dict(cfg, domain=domain, phone=phone, tel=tel)
        pages = {}
        for dp, _, files in os.walk(cdir):
            cat = catmap.get(os.path.basename(dp), "other")
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                meta, body = parse_fm(open(os.path.join(dp, fn), encoding="utf-8").read())
                if meta.get("url"):
                    pages[meta["url"]] = {"meta": meta, "body": body, "cat": cat, "url": meta["url"]}
        # RULE: every site must have all four trust pages (about/contact/faq/request-a-quote).
        # Generate any missing from a city-parameterized template so nav/footer links resolve.
        for _u, _fn in (("/about/", synth_about), ("/contact/", synth_contact),
                        ("/faq/", synth_faq), ("/request-a-quote/", synth_request_quote)):
            if _u not in pages:
                pages[_u] = _fn(site)
        if domain in SUBURBS_OVERRIDE:
            # drive the Service Areas menu from the master sheet; synthesize any missing pages
            suburbs = []
            for name, st in SUBURBS_OVERRIDE[domain]:
                sl = "porta-potty-rental-" + slugify(name) + "-" + st.lower()
                u = f"/{sl}/"
                if u not in pages:
                    pages[u] = synth_suburb(site, name, st)
                suburbs.append(u)
        else:
            suburbs = sorted(u for u, p in pages.items() if p["cat"] == "suburb")

        out = os.path.join(DIST, domain)
        # assets
        assets = os.path.join(out, "assets"); os.makedirs(assets, exist_ok=True)
        open(os.path.join(assets, "site.css"), "w", encoding="utf-8").write(css(site))
        open(os.path.join(assets, "nav.js"), "w", encoding="utf-8").write(NAVJS)
        # real brand logo mark/full + favicon (from logo_prep.py output)
        la = os.path.join(ROOT, "logo_assets", domain)
        mode = "icon"
        if os.path.isdir(la):
            mp = os.path.join(la, "mode.txt")
            mode = open(mp, encoding="utf-8").read().strip() if os.path.exists(mp) else "icon"
            if mode == "full" and os.path.exists(os.path.join(la, "full.png")):
                shutil.copy(os.path.join(la, "full.png"), os.path.join(assets, "logo-full.png"))
            elif os.path.exists(os.path.join(la, "mark.png")):
                shutil.copy(os.path.join(la, "mark.png"), os.path.join(assets, "logo-mark.png"))
            if os.path.exists(os.path.join(la, "favicon.png")):
                shutil.copy(os.path.join(la, "favicon.png"), os.path.join(assets, "favicon.png"))
        else:
            open(os.path.join(assets, "favicon.svg"), "w", encoding="utf-8").write(favicon_svg(site))
        # latest batch: a monogram-only fallback shows as plain text (no chip); other sites keep the chip
        if domain in V3_SITES and mode == "monogram":
            mode = "text"
        site["logo_mode"] = mode
        photos = os.path.join(assets, "photos"); os.makedirs(photos, exist_ok=True)
        for fn in os.listdir(POTTY_V1):
            if fn.lower().endswith(".webp"):
                shutil.copy(os.path.join(POTTY_V1, fn), os.path.join(photos, fn))
        # latest-batch sites use the fresh POTTY V3 imagery where available (V1 fills gaps)
        if domain in V3_SITES and V3_MAP:
            for slug, v3fn in V3_MAP.items():
                shutil.copy(os.path.join(POTTY_V3, v3fn), os.path.join(photos, slug + ".webp"))

        service_pages = [p for p in pages.values() if p["cat"] == "service"]
        valid_urls = set(pages.keys())
        count = 0
        for url, page in pages.items():
            slug = url.strip("/")
            odir = os.path.join(out, slug) if slug else out
            os.makedirs(odir, exist_ok=True)
            if url == "/":
                htmlout = home_page(site, page, service_pages, suburbs, pages)
            else:
                htmlout = inner_page(site, page, suburbs, pages)
            htmlout = fix_links(htmlout, valid_urls)
            open(os.path.join(odir, "index.html"), "w", encoding="utf-8").write(htmlout)
            count += 1
        # SEO/GEO technical files — generated to match the built site exactly
        write_sitemap(out, domain, pages)
        write_robots(out, domain)
        write_llms(out, site, pages, suburbs)
        print(f"  {domain}: {count} pages ({site['city']}, {site['st']})")
        cards.append((domain, site))
    write_portal(cards)

def write_sitemap(out, domain, pages):
    lastmod = BUILD_DATE
    urls = []
    for url, p in pages.items():
        lm = p["meta"].get("last_updated", "") or lastmod
        urls.append(f"  <url><loc>https://{domain}{url}</loc><lastmod>{lm}</lastmod>"
                    f"<priority>{'1.0' if url == '/' else '0.7'}</priority></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(sorted(urls)) + "\n</urlset>\n")
    open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8").write(xml)

def write_robots(out, domain):
    open(os.path.join(out, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\n\nSitemap: https://{domain}/sitemap.xml\n")

def write_llms(out, site, pages, suburbs):
    t = site
    b = f"https://{t['domain']}"
    zippart = f" {t['zip']}" if t["zip"] else ""
    lines = [f"# {t['city']} Porta Pros",
             f"> Portable toilet, restroom trailer, and dumpster rental in {t['city']}, {t['st']} "
             f"and the surrounding metro. On-time delivery, weekly service, transparent pricing.",
             "",
             f"- Phone: {t['phone']}",
             f"- Address: {t['street']}, {t['city']}, {t['st']}{zippart}",
             f"- Quote: {b}/request-a-quote/",
             "", "## Services"]
    for s in CURATED:
        u = f"/{s}/"
        if u in pages:
            d = clean_text(pages[u]["meta"].get("meta_description", "").split(".")[0])
            lines.append(f"- [{label_for(s, pages)}]({b}{u}): {d}")
    lines += ["", "## Service Areas"]
    lines.append(", ".join(suburb_label(u, pages) for u in suburbs) or f"{t['city']} metro")
    lines += ["", "## Key Pages"]
    for label, u in [("Pricing", "/porta-potty-rental-cost/"), ("Service Areas", "/service-areas/"),
                     ("About", "/about/"), ("Contact", "/contact/"), ("Request a Quote", "/request-a-quote/")]:
        if u in pages:
            lines.append(f"- [{label}]({b}{u})")
    open(os.path.join(out, "llms.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

def write_portal(cards):
    ports = {d: (PORTS.get(d) or 8001 + i) for i, (d, _) in enumerate(cards)}
    grid = ""
    for d, s in cards:
        p = ports[d]
        grid += (f'<a class="pc" href="http://localhost:{p}/" style="--c:{s["p"]};--a:{s["accent"]}">'
                 f'<div class="sw"><span style="background:{s["p"]}"></span><span style="background:{s["accent"]}"></span></div>'
                 f'<h2>{s["city"]} Porta Pros</h2><p>{s["street"]}, {s["city"]}, {s["st"]}</p>'
                 f'<small>{s["display"]} · localhost:{p}</small></a>')
    open(os.path.join(DIST, "index.html"), "w", encoding="utf-8").write(f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Porta Pros — City Sites</title>
<style>body{{margin:0;font-family:system-ui,sans-serif;background:#0f151b;color:#e6edf3}}
.h{{padding:60px 24px 20px;max-width:1080px;margin:0 auto}}.h h1{{font-size:2.4rem;margin:0 0 8px}}.h p{{color:#9fb0c0;margin:0}}
.g{{max-width:1080px;margin:0 auto;padding:24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}}
.pc{{display:block;background:#18212b;border:1px solid #263241;border-radius:16px;padding:24px;color:#e6edf3;text-decoration:none;transition:.16s}}
.pc:hover{{transform:translateY(-4px);border-color:var(--a)}}
.sw{{display:flex;gap:6px;margin-bottom:14px}}.sw span{{width:34px;height:34px;border-radius:9px}}
.pc h2{{margin:0 0 6px;font-size:1.3rem}}.pc p{{color:#9fb0c0;margin:0 0 10px;font-size:.9rem}}.pc small{{color:var(--a);font-weight:700}}
</style></head><body><div class="h"><h1>Porta Pros — 5 Unique City Sites</h1><p>Hand-built landing pages, each its own theme. Click to open.</p></div><div class="g">{grid}</div></body></html>""")

if __name__ == "__main__":
    print("Building landing pages...")
    build()
    print("Done. Output in", DIST)
