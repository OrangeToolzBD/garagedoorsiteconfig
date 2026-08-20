#!/usr/bin/env python
"""Give each built site its own Git repository, so it can be pushed, built and deployed
independently of the engine and of every other site.

Why a repo per site rather than one repo of 1000 sites: a deploy platform watches a
repo, and a single repo means every site redeploys when any site changes, one bad build
blocks all of them, and the checkout grows to gigabytes. Separate repos keep each
domain's history, rollbacks and deploy hooks to itself.

The engine repo stays the source of truth. These are *output* repos: the working tree is
replaced from dist/ on every publish, so nothing should ever be hand-edited in them --
which is why each one gets a README saying so.

Layout:  <out>/<domain>/   a git repo whose working tree is that site's dist/ folder

Usage:
  python site_repos.py --list                       # what would be published
  python site_repos.py                              # create/update repos under ../sites-out
  python site_repos.py --out DIR --remote "git@github.com:org/{domain}.git"
  python site_repos.py --push                       # commit and push (remote required)
  python site_repos.py <domain> ...                 # limit to specific sites

`--remote` is a template: {domain} and {slug} are substituted per site. Nothing is
pushed unless --push is given, and no remote is ever invented.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
DEFAULT_OUT = os.path.join(os.path.dirname(ROOT), "sites-out")

README = """# {brand} — {domain}

Generated static site. **Do not edit these files by hand.**

Everything here is produced by the site engine and is overwritten on every publish.
Change the source (content JSON, `config/sites.json`, brand assets) in the engine repo
and re-publish instead.

- City: {city}, {st}
- Design: `{design}`
- Pages: {pages}
- Last published: {built}

## Deploy

The whole repo is the site: static HTML with root-relative links, meant to be served at
the domain root. `vercel.json` is included, so on Vercel this needs no build step and no
framework preset — point a project at this repo and deploy.
"""

GITIGNORE = "*.log\n.DS_Store\nThumbs.db\n"


def sites_config():
    cfg = json.load(open(os.path.join(ROOT, "config", "sites.json"), encoding="utf-8"))
    return {s["domain"]: s for s in cfg["sites"]}


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}:\n{r.stderr.strip()}")
    return r


def publish(domain, meta, out_root, remote_tmpl, do_push):
    src = os.path.join(DIST, domain)
    repo = os.path.join(out_root, domain)
    fresh = not os.path.isdir(os.path.join(repo, ".git"))
    os.makedirs(repo, exist_ok=True)
    if fresh:
        git(repo, "init", "-q", "-b", "main")

    # Replace the tree rather than merging: dist/ is the whole truth, and a file that
    # stopped being generated should stop existing here too. .git is preserved so the
    # site keeps its history.
    for name in os.listdir(repo):
        if name == ".git":
            continue
        p = os.path.join(repo, name)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for name in os.listdir(src):
        s, d = os.path.join(src, name), os.path.join(repo, name)
        shutil.copytree(s, d) if os.path.isdir(s) else shutil.copy2(s, d)

    pages = sum(1 for dp, _, fs in os.walk(repo) if ".git" not in dp for f in fs if f.endswith(".html"))
    open(os.path.join(repo, "README.md"), "w", encoding="utf-8").write(README.format(
        brand=meta.get("brand", domain), domain=domain, city=meta.get("city", ""),
        st=meta.get("st", ""), design=meta.get("template", "garage"),
        pages=pages, built=date.today().isoformat()))
    open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8").write(GITIGNORE)

    git(repo, "add", "-A")
    if not git(repo, "status", "--porcelain").stdout.strip():
        return repo, pages, "no change"

    git(repo, "-c", "user.name=site-engine", "-c", "user.email=engine@localhost",
        "commit", "-q", "-m", f"Publish {domain} ({pages} pages) {date.today().isoformat()}")

    status = "committed"
    if remote_tmpl:
        url = remote_tmpl.format(domain=domain, slug=domain.rsplit(".", 1)[0])
        have = git(repo, "remote", check=False).stdout.split()
        if "origin" in have:
            git(repo, "remote", "set-url", "origin", url)
        else:
            git(repo, "remote", "add", "origin", url)
        if do_push:
            r = git(repo, "push", "-u", "origin", "main", check=False)
            status = "pushed" if r.returncode == 0 else f"PUSH FAILED: {r.stderr.strip().splitlines()[-1][:70]}"
    elif do_push:
        status = "committed (no --remote, nothing to push to)"
    return repo, pages, status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domains", nargs="*")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--remote", default="", help="URL template, e.g. git@github.com:org/{slug}.git")
    ap.add_argument("--push", action="store_true", help="push after committing (needs --remote)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    meta = sites_config()
    built = sorted(d for d in os.listdir(DIST) if os.path.isdir(os.path.join(DIST, d))) \
        if os.path.isdir(DIST) else []
    targets = [d for d in (a.domains or built) if d in built]
    missing = [d for d in a.domains if d not in built]
    for d in missing:
        print(f"  ! {d}: not built - run `python build.py` first")
    if not targets:
        print("nothing to publish"); return

    if a.list:
        for d in targets:
            print(f"  {d:34} -> {os.path.join(a.out, d)}")
        if a.remote:
            print(f"\n  remote template: {a.remote}")
        return

    os.makedirs(a.out, exist_ok=True)
    print(f"Publishing {len(targets)} site(s) -> {a.out}\n")
    failed = 0
    for d in targets:
        try:
            repo, pages, status = publish(d, meta.get(d, {}), a.out, a.remote, a.push)
        except Exception as e:
            print(f"  {d:34} ERROR {e}"); failed += 1; continue
        if "FAILED" in status:
            failed += 1
        print(f"  {d:34} {pages:3} pages  {status}")
    if not a.remote:
        print("\nNo --remote given, so these are local repos only. Add one with:")
        print('  python site_repos.py --remote "git@github.com:YOUR-ORG/{slug}.git" --push')
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
