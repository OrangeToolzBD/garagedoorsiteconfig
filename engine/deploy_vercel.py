#!/usr/bin/env python
"""Deploy built sites to Vercel, one project per domain.

Each dist/<domain>/ is already a complete static site with root-relative links, so
Vercel needs no build step: the folder is uploaded as-is and served from the CDN.
build.py writes a vercel.json into each folder (trailingSlash + headers), so there is
nothing to configure in the dashboard.

One project per domain is deliberate. These sites are built to be served at a domain
root -- their internal links, canonical tags, sitemap and robots.txt all assume it --
so they cannot share a project behind path prefixes. (engine/preview_bundle.py does
that trick for previews, and rewrites every URL to make it work; it is not a
deployable artifact.)

Prerequisites (both are yours to run -- they involve your Vercel credentials):
    npm i -g vercel          # or use npx, as below
    vercel login

Usage:
    python deploy_vercel.py --list                 # show what would deploy
    python deploy_vercel.py                        # preview deploys (safe, throwaway URLs)
    python deploy_vercel.py --prod                 # production deploys
    python deploy_vercel.py --prod <domain> ...    # only these
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")

DEFAULT = ["dallasdoorpros.com", "austingaragedoorguys.com",
           "pickeringtongaragedoorpros.com", "richmonddoorpros.com",
           "auroragaragedoorpros.com"]


def project_name(domain):
    """Vercel project names allow [a-z0-9._-]; a dot is legal but reads badly in URLs."""
    return domain.replace(".", "-")


def vercel_cmd():
    exe = shutil.which("vercel")
    if exe:
        return [exe]
    if shutil.which("npx"):
        return ["npx", "--yes", "vercel"]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domains", nargs="*", default=[])
    ap.add_argument("--prod", action="store_true", help="production deploy (default is a preview)")
    ap.add_argument("--list", action="store_true", help="show what would deploy, run nothing")
    a = ap.parse_args()

    domains = a.domains or DEFAULT
    ready, missing = [], []
    for d in domains:
        (ready if os.path.isdir(os.path.join(DIST, d)) else missing).append(d)

    for d in missing:
        print(f"  ! {d}: not built -- run `python build.py` first")

    if a.list or not ready:
        for d in ready:
            n = sum(len(fs) for _, _, fs in os.walk(os.path.join(DIST, d)))
            print(f"  {d:34} -> project {project_name(d):34} ({n} files)")
        if not ready:
            print("nothing to deploy")
        return

    cmd = vercel_cmd()
    if not cmd:
        print("! vercel CLI not found. Install it (`npm i -g vercel`) or ensure npx is available.")
        return

    print(f"Deploying {len(ready)} site(s) as {'PRODUCTION' if a.prod else 'preview'}...\n")
    urls, failed = [], []
    for d in ready:
        args = cmd + ["deploy", os.path.join(DIST, d), "--yes", "--name", project_name(d)]
        if a.prod:
            args.append("--prod")
        print(f"  -> {d}")
        r = subprocess.run(args, capture_output=True, text=True)
        out = (r.stdout or "").strip().splitlines()
        url = next((l.strip() for l in reversed(out) if l.strip().startswith("https://")), "")
        if r.returncode != 0 or not url:
            failed.append(d)
            print(f"     FAILED ({r.returncode})")
            for line in (r.stderr or "").strip().splitlines()[-4:]:
                print(f"     {line}")
            continue
        urls.append((d, url))
        print(f"     {url}")

    if urls:
        print("\nDeployed:")
        for d, u in urls:
            print(f"  {d:34} {u}")
        print("\nAdd the real domain to each project (Vercel dashboard > Project > Settings >")
        print("Domains), then point that domain's DNS at Vercel.")
    if failed:
        print(f"\n{len(failed)} failed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
