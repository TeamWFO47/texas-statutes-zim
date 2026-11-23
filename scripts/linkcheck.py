#!/usr/bin/env python3
"""Check that every internal link in the rendered site points at an existing page and #id.

Usage: linkcheck.py SITE_DIR. Exit status 1 if any link is dead.
"""
import collections, html, os, re, sys
root = sys.argv[1]
ids, links = {}, []
for d, _, fs in os.walk(root):
    for f in fs:
        if f.endswith('.html'):
            p = os.path.join(d, f); s = open(p, encoding='utf-8').read(); rel = os.path.relpath(p, root)
            ids[rel] = set(re.findall(r' id="([^"]+)"', s))
            links += [(rel, html.unescape(h)) for h in re.findall(r'<a href="([^"]+)"', s)]
c, bad = collections.Counter(), []
for src, h in links:
    if re.match(r'[a-z]+:', h):
        c['external'] += 1; continue
    path, _, frag = h.partition('#')
    tgt = os.path.normpath(os.path.join(os.path.dirname(src), path)) if path else src
    if tgt not in ids or (frag and frag not in ids[tgt]):
        c['dead'] += 1; bad.append((src, h)); continue
    c['ok'] += 1
print(f"pages: {len(ids)}, links: {len(links)}, ok: {c['ok']}, dead: {c['dead']}, external: {c['external']}")
for b in bad[:10]:
    print('  dead:', *b)
sys.exit(1 if bad else 0)
