#!/usr/bin/env python3
"""Render the OpenStatutes.org Texas Constitution and Statutes release into static HTML for a ZIM.

Page split, section order and cross-reference targets come from the Texas Legislative
Council (TLC) chapter HTML in the release's *.htm.zip files. Section text comes from the
release's JSON where it matches TLC's text exactly; otherwise ("hybrid" mode) TLC's own
text is used, because the JSON drops tables, two-column fee lists and heading lines.

Usage: render.py --src DIR --codes StatuteCodes.json --out DIR --snapshot YYYY-MM-DD [--mode hybrid|json]
"""
import argparse, collections, difflib, glob, html, json, os, re, sys, zipfile

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument('--src', required=True, help='folder with <CODE>.json and <CODE>.htm.zip')
ap.add_argument('--codes', required=True, help="TLC's StatuteCodes.json (official code names)")
ap.add_argument('--out', required=True, help='output folder for the HTML site')
ap.add_argument('--snapshot', required=True, help='OpenStatutes release date, YYYY-MM-DD')
ap.add_argument('--current-through', default='the 89th Legislature, 2nd Called Session, 2025; '
                'constitutional amendments approved by voters in November 2025',
                help='"current through" wording for the landing page')
ap.add_argument('--mode', choices=['hybrid', 'json'], default='hybrid')
ap.add_argument('--log', default=None, help='write a JSON log of every decision here')
ARGS = ap.parse_args()
SRC, CODES_JSON, OUT, MODE, SNAPSHOT = ARGS.src, ARGS.codes, ARGS.out, ARGS.mode, ARGS.snapshot
CURRENT = ARGS.current_through

ANCHOR = re.compile(r'<a name=["\']?([^"\'>\s]+)["\']?\s*>', re.I)
STAT = re.compile(r'<a [^>]*href="https?://(?:statutes\.capitol\.texas\.gov|www\.statutes\.legis\.state\.tx\.us)/GetStatute\.aspx\?([^"]*)"[^>]*>(.*?)</a>', re.S | re.I)
TAG = re.compile(r'<[^>]+>')
IDLIKE = re.compile(r'^\d{5,}\.\d{5,}$')
WS = re.compile(r'\s+')

stats = collections.Counter()
log = collections.defaultdict(list)


def natkey(s):
    return [(0, int(p), '') if p.isdigit() else (1, 0, p.lower()) for p in re.findall(r'\d+|\D+', s)]


def parse_q(q):
    d = {}
    for kv in html.unescape(q).split('&'):
        if '=' in kv:
            k, v = kv.split('=', 1)
            d[k.lower()] = v
    return d


def html_to_text_with_links(frag):
    """Plain text of an HTML fragment plus statute link spans [(start,end,code,value)]."""
    frag = re.sub(r'(?s)<style.*?</style>', '', frag)
    out, links, pos = [], [], 0
    for m in STAT.finditer(frag):
        out.append(html.unescape(TAG.sub(' ', frag[pos:m.start()])))
        start = sum(map(len, out))
        txt = html.unescape(TAG.sub('', m.group(2)))
        out.append(txt)
        q = parse_q(m.group(1))
        links.append((start, start + len(txt), q.get('code', ''), q.get('value', '')))
        pos = m.end()
    out.append(html.unescape(TAG.sub(' ', frag[pos:])))
    return ''.join(out), links


def nonws_map(s):
    """Return (string without whitespace, list mapping each kept char -> index in s)."""
    idx = [i for i, c in enumerate(s) if not c.isspace()]
    return ''.join(s[i] for i in idx), idx


def norm(s):
    return WS.sub(' ', s).strip()


# ---------------------------------------------------------------- load
names = {c['code']: c['CodeName'] for c in json.load(open(CODES_JSON))['StatuteCode'] if c['code'] != 'ZZ'}
codes = sorted(c for c in names if os.path.exists(f'{SRC}/{c}.json'))

pages = {}          # (code, pagekey) -> dict(title, file, segs=[...], head_html)
target = {}         # (code, value_lower) -> (code, pagekey, anchor or None)
ordered_pages = collections.defaultdict(list)

for code in codes:
    z = zipfile.ZipFile(f'{SRC}/{code}.htm.zip')
    files = [n for n in z.namelist() if n.lower().endswith('.htm')]
    old = [n for n in files if re.search(r'old|copy', n, re.I)]
    for n in old:
        log['skipped_old_file'].append(f'{code}:{n}')
    files = [n for n in files if n not in old]
    segs_by_key = collections.defaultdict(list)
    for n in sorted(files, key=lambda n: natkey(n)):
        raw = z.read(n).decode('utf-8', 'replace').lstrip('﻿')
        base = n[:-4]
        pagekey = base.split('.', 1)[1] if '.' in base else base       # '22', '20a', '103.0'
        if pagekey.startswith('.'):                                     # es..2.htm -> 'x2'
            log['renamed_page'].append(f'{code}:{n}')
            pagekey = 'x' + pagekey.lstrip('.')
        tm = re.search(r'(?is)<title>(.*?)</title>', raw)
        title = norm(html.unescape(tm.group(1))) if tm else f'{code} {pagekey}'
        body = re.sub(r'(?is)^.*?<body[^>]*>', '', raw)
        body = re.sub(r'(?is)</body>.*$', '', body)
        anchors = list(ANCHOR.finditer(body))
        # group anchors: a human anchor (num) optionally followed by an id anchor
        segs, i = [], 0
        while i < len(anchors):
            a = anchors[i].group(1)
            num, ident = (None, a) if IDLIKE.match(a) else (a, None)
            j = i + 1
            if (num is not None and j < len(anchors)
                    and re.fullmatch(r'\s*</a>\s*', body[anchors[i].end():anchors[j].start()])
                    and re.fullmatch(r'\d+\.\d+', anchors[j].group(1))):
                ident = anchors[j].group(1); j += 1
                stats['anchor_pairs'] += 1
            segs.append({'num': num, 'id': ident, 'start': anchors[i].start(), 'json': None})
            i = j
        for k, s in enumerate(segs):
            s['end'] = segs[k + 1]['start'] if k + 1 < len(segs) else len(body)
            s['html'] = body[s['start']:s['end']]
            s['text'], s['links'] = html_to_text_with_links(s['html'])
            s['page'] = (code, pagekey)
            for key in (s['num'], s['id']):
                if key:
                    segs_by_key[key].append(s)
        head = body[:segs[0]['start']] if segs else body
        pages[(code, pagekey)] = {'title': title, 'file': n, 'segs': segs, 'head': head}
        ordered_pages[code].append(pagekey)
        target.setdefault((code, pagekey.lower()), (code, pagekey, None))

    # ---- assign JSON sections to zip segments
    data = json.load(open(f'{SRC}/{code}.json'))['sections']
    stats['json_entries'] += len(data)
    groups = collections.OrderedDict()
    for x in data:
        groups.setdefault(x['section']['number'], []).append(x)
    for key, xs in groups.items():
        uniq, seen = [], set()
        for x in xs:
            sig = (x['sectionBody'], str(x.get('history')))
            if sig in seen:
                stats['dropped_exact_copy'] += 1
                continue
            seen.add(sig); uniq.append(x)
        cands = [s for s in segs_by_key.get(key, []) if s['json'] is None]
        if not cands:
            stats['json_unplaced'] += len(uniq)
            log['json_unplaced'].append(f'{code}:{key}')
            continue
        pairs = []
        if len(uniq) > 1:
            for x in list(uniq):
                xa = nonws_map(x['sectionBody'] + str(x.get('history') or ''))[0]
                for s in cands:
                    if nonws_map(s['text'])[0] == xa:
                        pairs.append((x, s)); uniq.remove(x); cands.remove(s); break
        if not uniq:
            pass
        elif not cands:
            stats['dropped_stale_version'] += len(uniq)
            log['dropped_stale_version'].extend(f'{code}:{key}' for _ in uniq)
        elif len(uniq) == 1:
            pairs.append((uniq[0], cands[0]))
        else:
            # best text match, greedy
            sc = []
            for a, x in enumerate(uniq):
                xt = norm(x['sectionBody'])[:3000]
                for b, s in enumerate(cands):
                    r = difflib.SequenceMatcher(None, xt, norm(s['text'])[:3000], autojunk=False).ratio()
                    sc.append((r, a, b))
            sc.sort(reverse=True)
            ua, ub = set(), set()
            for r, a, b in sc:
                if a in ua or b in ub:
                    continue
                ua.add(a); ub.add(b); pairs.append((uniq[a], cands[b]))
            for a, x in enumerate(uniq):
                if a not in ua:
                    stats['dropped_stale_version'] += 1
                    log['dropped_stale_version'].append(f'{code}:{key}')
        for x, s in pairs:
            s['json'] = x

# anchor ids + section targets
for (code, pk), p in pages.items():
    used = collections.Counter()
    for s in p['segs']:
        label = s['num'] or s['id']
        used[label] += 1
        s['anchor'] = 'sec-' + label + ('' if used[label] == 1 else f'-v{used[label]}')
        for key in (s['num'], s['id']):
            if key:
                target.setdefault((code, key.lower()), (code, pk, s['anchor']))


def href_for(from_code, code, value):
    stats['links_total'] += 1
    t = target.get((code.upper(), value.lower()))
    if not t:
        stats['links_unresolved'] += 1
        log['unresolved'].append(f'{code}:{value}')
        return None
    stats['links_resolved'] += 1
    c, pk, anc = t
    url = ('' if c == from_code else f'../{c}/') + f'{pk}.html'
    return url + (f'#{anc}' if anc else '')


def link_spans(body_text, seg_text, seg_links):
    """Map link spans from the zip segment text onto body_text. Returns [(s,e,code,value)], unmatched count."""
    if not seg_links:
        return [], 0
    bn, bidx = nonws_map(body_text)
    sn, sidx = nonws_map(seg_text)
    rev = {orig: k for k, orig in enumerate(sidx)}
    off = bn.find(sn) if len(sn) <= len(bn) else -1
    if off < 0 and sn.find(bn) >= 0:
        off = -sn.find(bn)          # body is a substring of the segment text
    exact = bn == sn or (off != -1 and (off >= 0 and bn[off:off + len(sn)] == sn or off < 0))
    stats['align_exact' if exact else 'align_search'] += 1
    spans, miss, cursor = [], 0, 0
    for st, en, c, v in seg_links:
        ks = [rev[i] for i in range(st, en) if i in rev]
        if not ks:
            miss += 1; continue
        k0, k1 = ks[0], ks[-1]
        b0 = None
        if exact:
            b0 = k0 + off
            if not (0 <= b0 and b0 + (k1 - k0) < len(bn) and bn[b0:b0 + k1 - k0 + 1] == sn[k0:k1 + 1]):
                b0 = None
        if b0 is None:
            # anchored search: preceding context + link text, from the cursor onward
            lt = sn[k0:k1 + 1]
            for ctx in (30, 15, 6, 0):
                pat = sn[max(0, k0 - ctx):k0] + lt
                f = bn.find(pat, cursor)
                if f >= 0:
                    b0 = f + (len(pat) - len(lt)); break
        if b0 is None:
            miss += 1; continue
        b1 = b0 + (k1 - k0)
        spans.append((bidx[b0], bidx[b1] + 1, c, v))
        cursor = b1 + 1
    return spans, miss


HEADING = re.compile(r'^((?:Sec|Art|Section)\.?\s+[\w.\-()]+\.\s+[^a-z]{2,}?\.)(?=\s|$)')


def render_text(code, text, spans):
    """Escape text, insert links, split lines into paragraphs."""
    spans = sorted(spans)
    out, pos = [], 0
    for st, en, c, v in spans:
        if st < pos or '\n' in text[st:en]:
            continue
        h = href_for(code, c, v)
        out.append(html.escape(text[pos:st]))
        inner = html.escape(text[st:en])
        out.append(f'<a href="{html.escape(h)}">{inner}</a>' if h else inner)
        pos = en
    out.append(html.escape(text[pos:]))
    paras = []
    for line in ''.join(out).split('\n'):
        if not line.strip():
            continue
        plain = TAG.sub('', html.unescape(line)).strip()
        if plain.startswith('Text of ') and len(plain) < 400:
            paras.append(f'<p class="ver">{line.strip()}</p>')
            continue
        m = HEADING.match(line)
        if m:
            line = f'<strong>{m.group(1)}</strong>' + line[m.end():]
        paras.append(f'<p>{line.strip()}</p>')
    return '\n'.join(paras)


from html.parser import HTMLParser

KEEP = {'p', 'br', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'pre', 'b', 'strong',
        'i', 'em', 'u', 'sup', 'sub', 'div', 'span', 'ul', 'ol', 'li', 'caption'}
VOID = {'br'}


class TLCClean(HTMLParser):
    """Sanitise TLC chapter HTML: keep structure and tables, rewrite statute links, unwrap others."""
    def __init__(self, code):
        super().__init__(convert_charrefs=True)
        self.code, self.out, self.stack, self.skip, self.open, self.tables = code, [], [], 0, [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('style', 'script', 'title', 'head'):
            self.skip += 1; return
        if tag == 'a':
            m = re.match(r'https?://(?:statutes\.capitol\.texas\.gov|www\.statutes\.legis\.state\.tx\.us)/GetStatute\.aspx\?(.*)', a.get('href') or '', re.I)
            h = None
            if m:
                q = parse_q(m.group(1))
                h = href_for(self.code, q.get('code', ''), q.get('value', ''))
            self.stack.append(bool(h))
            if h:
                self.out.append(f'<a href="{html.escape(h)}">')
            return
        if tag not in KEEP:
            return
        keep = []
        cls = a.get('class')
        if cls in ('center', 'right', 'left', 'justify'):
            keep.append(f' class="{cls}"')
        for k in ('colspan', 'rowspan'):
            if a.get(k) and a[k].isdigit():
                keep.append(f' {k}="{a[k]}"')
        if tag == 'pre' and not self.tables:
            return                      # TLC wraps whole chapters in <pre>; drop the wrapper
        if tag == 'table':
            self.tables += 1
        self.out.append(f'<{tag}{"".join(keep)}>')
        if tag not in VOID:
            self.open.append(tag)

    def handle_endtag(self, tag):
        if tag in ('style', 'script', 'title', 'head'):
            self.skip = max(0, self.skip - 1); return
        if tag == 'a':
            if self.stack and self.stack.pop():
                self.out.append('</a>')
            return
        if tag in KEEP and tag not in VOID and tag in self.open:
            while self.open:                # close anything left open inside it
                t = self.open.pop()
                self.out.append(f'</{t}>')
                if t == 'table':
                    self.tables -= 1
                if t == tag:
                    break

    def finish(self):
        while self.open:
            self.out.append(f'</{self.open.pop()}>')
        while self.stack:
            if self.stack.pop():
                self.out.append('</a>')

    def handle_startendtag(self, tag, attrs):
        if tag in VOID:
            self.out.append('<br>')

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))


def render_zip_fragment(code, frag):
    """Render a TLC HTML fragment faithfully (tables, headings, line breaks) with rewritten links."""
    p = TLCClean(code)
    p.feed(frag); p.close(); p.finish()
    out = ''.join(p.out)
    out = re.sub(r'<p( class="\w+")?>\s*</p>', '', out)
    out = re.sub(r'^(\s*<br>\s*)+|(\s*<br>\s*)+$', '', out.strip())
    return out.strip()


CSS = """
:root{--fg:#1d1d1f;--bg:#fdfdfb;--muted:#5f6368;--rule:#d9d9d4;--link:#1a5fb4;--ver:#7a4b00;--verbg:#fff6e5}
@media (prefers-color-scheme:dark){:root{--fg:#e6e6e3;--bg:#17181a;--muted:#a3a7ad;--rule:#33353a;--link:#8ab4f8;--ver:#f2c27b;--verbg:#2a2318}}
html{background:var(--bg)}body{color:var(--fg);background:var(--bg);font:17px/1.55 Georgia,'Times New Roman',serif;max-width:46em;margin:0 auto;padding:1em 16px 4em}
a{color:var(--link)}nav.crumbs{font:14px/1.4 system-ui,sans-serif;color:var(--muted);margin-bottom:1em}
h1{font-size:1.5em;line-height:1.25;margin:.2em 0 .6em}h2{font-size:1.15em;margin:1.6em 0 .4em}
.head p{text-align:center;font-weight:bold;margin:.2em 0}
section.sec{border-top:1px solid var(--rule);padding-top:.8em;margin-top:1em}
section.sec p{margin:.35em 0}p.center{text-align:center;font-weight:bold}
p.ver{font:italic 15px/1.4 system-ui,sans-serif;color:var(--ver);background:var(--verbg);padding:.35em .6em;border-radius:4px}
p.hist{font:13px/1.45 system-ui,sans-serif;color:var(--muted)}
p.asof{background:var(--verbg);padding:.6em .8em;border-radius:4px}
ul.toc{list-style:none;padding:0;columns:1}ul.toc li{margin:.25em 0}
@media (min-width:700px){ul.toc.codes{columns:2}}
footer{margin-top:3em;font:13px/1.5 system-ui,sans-serif;color:var(--muted);border-top:1px solid var(--rule);padding-top:1em}
"""

CREDIT = ('Law text: Texas Legislative Council, Texas Constitution and Statutes '
          f'(statutes.capitol.texas.gov), current through {CURRENT}. '
          f'Structured data: OpenStatutes.org snapshot {SNAPSHOT}, licensed CC BY 4.0 '
          '(creativecommons.org/licenses/by/4.0). Rendered for offline use; not an official publication. '
          'Not affiliated with any government agency.')


def page(title, body, depth, crumbs=''):
    css = '../' * depth + 'style.css'
    return (f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><link rel="stylesheet" href="{css}"></head><body>\n'
            f'{crumbs}{body}\n<footer>{html.escape(CREDIT)}</footer>\n</body></html>\n')


os.makedirs(OUT, exist_ok=True)
open(f'{OUT}/style.css', 'w').write(CSS)
toc_rows = []
for code in codes:
    os.makedirs(f'{OUT}/{code}', exist_ok=True)
    name = names[code]
    rows = []
    for pk in sorted(ordered_pages[code], key=natkey):
        p = pages[(code, pk)]
        parts = []
        head_txt = render_zip_fragment(code, p['head'])
        parts.append(f'<div class="head">{head_txt}</div>')
        for s in p['segs']:
            x = s['json']
            if x is not None:
                h0 = x.get('history') or ''
                h0 = '\n'.join(map(str, h0)) if isinstance(h0, list) else str(h0)
                if nonws_map(x['sectionBody'] + h0)[0] != nonws_map(s['text'])[0]:
                    stats['json_differs_from_tlc'] += 1
                    log['json_differs_from_tlc'].append(f'{code}:{s["num"] or s["id"]}')
                    if MODE == 'hybrid':
                        x = None
                        stats['sections_from_tlc_due_to_mismatch'] += 1
            if x is not None:
                stats['sections_from_json'] += 1
                hist = x.get('history') or ''
                if isinstance(hist, list):
                    hist = '\n'.join(map(str, hist))
                full = x['sectionBody'].rstrip() + '\n' + str(hist).strip()
                spans, miss = link_spans(full, s['text'], s['links'])
                stats['links_not_placed'] += miss
                if miss:
                    log['links_not_placed'].append(f'{code}:{s["num"] or s["id"]}:{miss}')
                cut = len(x['sectionBody'].rstrip())
                b_sp = [t for t in spans if t[1] <= cut]
                h_sp = [(a - cut - 1, b - cut - 1, c, v) for a, b, c, v in spans if a > cut]
                inner = render_text(code, x['sectionBody'].rstrip(), b_sp)
                if str(hist).strip():
                    inner += '\n' + render_text(code, str(hist).strip(), h_sp).replace('<p>', '<p class="hist">')
            else:
                stats['segments_from_zip'] += 1
                if s['num'] and not re.fullmatch(r'[A-Z]{1,3}(-\d+)?', s['num'] or ''):
                    log['segment_no_json'].append(f'{code}:{s["num"]}')
                inner = render_zip_fragment(code, s['html'])
            parts.append(f'<section class="sec" id="{html.escape(s["anchor"])}">\n{inner}\n</section>')
        crumbs = (f'<nav class="crumbs"><a href="../index.html">Texas Statutes</a> › '
                  f'<a href="index.html">{html.escape(name)}</a></nav>\n')
        heading = re.sub(rf'^{re.escape(name.upper())}\s*', '', p['title'], flags=re.I) or p['title']
        open(f'{OUT}/{code}/{pk}.html', 'w').write(
            page(f'{name} — {heading}', '\n'.join(parts), 1, crumbs))
        stats['pages'] += 1
        rows.append(f'<li><a href="{pk}.html">{html.escape(heading.title() if heading.isupper() else heading)}</a></li>')
    crumbs = '<nav class="crumbs"><a href="../index.html">Texas Statutes</a></nav>\n'
    open(f'{OUT}/{code}/index.html', 'w').write(page(
        name, f'<h1>{html.escape(name)}</h1>\n<ul class="toc">\n' + '\n'.join(rows) + '\n</ul>', 1, crumbs))
    toc_rows.append(f'<li><a href="{code}/index.html">{html.escape(name)}</a> <small>({code})</small></li>')

ncodes = len([c for c in codes if c != 'CN'])
intro = (f'<p>The Texas Constitution and the {ncodes} Texas codes, as published by the Texas Legislative Council.</p>\n'
         f'<p class="asof"><strong>Current through:</strong> {html.escape(CURRENT)}.<br>'
         f'<strong>Snapshot date:</strong> {SNAPSHOT} (OpenStatutes.org release). Changes TLC made after this date, '
         'including removal of versions that expired after it, are not included.</p>\n'
         '<p>Cross-references between sections link within this archive and work with no network.</p>')
open(f'{OUT}/index.html', 'w').write(page(
    'Texas Constitution and Statutes',
    '<h1>Texas Constitution and Statutes</h1>\n' + intro + '\n<ul class="toc codes">\n' + '\n'.join(toc_rows) + '\n</ul>'
    '\n<h2>Source and license</h2>\n'
    '<p><strong>Law text:</strong> Texas Legislative Council, Texas Constitution and Statutes '
    '(statutes.capitol.texas.gov). Texas statutes are public law.</p>\n'
    f'<p><strong>Data:</strong> OpenStatutes.org, Texas Constitution and Statutes release {SNAPSHOT}, '
    'licensed under <strong>Creative Commons Attribution 4.0 (CC BY 4.0)</strong>, '
    'creativecommons.org/licenses/by/4.0. Section text comes from the OpenStatutes JSON; where that JSON '
    f'differs from TLC&#x27;s own chapter pages ({stats["json_differs_from_tlc"]:,} sections, mostly tables), the TLC chapter page text '
    'from the same release is used. Cross-reference links were rewritten to point inside this archive.</p>\n'
    '<p>This offline copy is not an official publication and is not affiliated with any government agency. '
    'Check the official source before relying on it.</p>', 0))

if ARGS.log:
    json.dump({k: v for k, v in log.items()}, open(ARGS.log, 'w'), indent=1)
for k in sorted(stats):
    print(f'{k:24} {stats[k]}')
for k, v in log.items():
    print(k, len(v), v[:8])
