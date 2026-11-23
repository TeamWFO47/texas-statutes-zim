#!/usr/bin/env python3
"""Compare the text of every rendered chapter page with TLC's chapter page from the release.

Whitespace and markup are ignored. Usage: verify.py SRC_DIR SITE_DIR [N_EXAMPLES]
Exit status 1 if any page differs.
"""
import collections, glob, html, os, re, sys, zipfile
src, site = sys.argv[1], sys.argv[2]
nshow = int(sys.argv[3]) if len(sys.argv) > 3 else 5

def txt(s):
    s = re.sub(r'(?is)<(style|script|nav|footer|title)[^>]*>.*?</\1>', '', s)
    return re.sub(r'\s+', '', html.unescape(re.sub(r'<[^>]+>', '', s))).replace('﻿', '')

res, bad = collections.Counter(), []
for f in sorted(glob.glob(os.path.join(src, '*.htm.zip'))):
    code = os.path.basename(f).split('.')[0]
    z = zipfile.ZipFile(f)
    for n in z.namelist():
        if not n.lower().endswith('.htm') or re.search(r'old|copy', n, re.I):
            continue
        pk = n[:-4].split('.', 1)[1]
        pk = 'x' + pk.lstrip('.') if pk.startswith('.') else pk
        a = txt(z.read(n).decode('utf-8', 'replace'))
        b = txt(open(os.path.join(site, code, pk + '.html'), encoding='utf-8').read())
        if a == b:
            res['identical'] += 1
            continue
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        res['differs'] += 1
        bad.append((code, pk, a[max(0, i - 60):i + 80], b[max(0, i - 60):i + 80]))
print(f"pages identical to TLC: {res['identical']}, differing: {res['differs']}")
for code, pk, x, y in bad[:nshow]:
    print(f'--- {code}/{pk}\n  TLC:  {x}\n  ours: {y}')
sys.exit(1 if bad else 0)
