#!/usr/bin/env python
"""Serve the preview_bundle.py output on a single port (default 8100).

One port, so one ngrok tunnel covers every bundled site -- which is what ngrok's free
plan allows. Binds 0.0.0.0 so it is reachable over the LAN too.

  python preview_bundle.py && python serve_preview.py
  ngrok http 8100
"""
import functools
import os
import socket
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
PREVIEW = os.path.join(ROOT, "preview")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8100


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        # previews get reshared and rebuilt constantly; never let one get cached
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        # it is a preview of unfinished sites -- keep it out of search results
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        super().end_headers()


def main():
    if not os.path.isdir(PREVIEW):
        print("! preview/ not found - run: python preview_bundle.py"); return
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT),
                                functools.partial(Handler, directory=PREVIEW))
    print(f"  local:   http://localhost:{PORT}/")
    print(f"  network: http://{lan_ip()}:{PORT}/")
    print(f"  tunnel:  ngrok http {PORT}\n")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
