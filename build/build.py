#!/usr/bin/env python3
"""Export the OMSC design-canvas pages to a plain static website.

Each *.dc.html page is split into: <helmet> (head styles), the template markup,
and the page's Component class. The template is compiled to a JS function that
returns an HTML string; Node runs it once to pre-render each page, and the same
function runs in the browser (via js/dc.js) to keep sliders and viewers live.
"""
import html, json, os, re, shutil, subprocess, sys
from html.parser import HTMLParser

SRC = sys.argv[1]
OUT = sys.argv[2]
BLOBMAP = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
HERE = os.path.dirname(os.path.abspath(__file__))

PAGES = {
    'Main.dc.html': 'index.html',
    'Pickleball.dc.html': 'pickleball.html',
    'Cornhole.dc.html': 'cornhole.html',
    'Pentathlon.dc.html': 'pentathlon.html',
    'Contact.dc.html': 'contact.html',
    'ChampionsCorner.dc.html': 'champions-corner.html',
    'EventStatistics.dc.html': 'event-statistics.html',
    'LeaderBoards.dc.html': 'leader-boards.html',
}
EXT = {'image/jpeg': 'jpg', 'image/png': 'png', 'video/mp4': 'mp4', 'image/webp': 'webp', 'image/gif': 'gif'}
VOID = {'img', 'input', 'br', 'meta', 'link', 'source', 'hr', 'area', 'base', 'col', 'embed', 'track', 'wbr', 'path', 'circle', 'rect', 'line', 'polyline', 'polygon'}
BOOL_ATTRS = {'muted', 'loop', 'playsinline', 'autoplay', 'disabled', 'checked', 'selected', 'hidden', 'controls', 'open', 'required'}
ACCENT = '#F2A93B'

# Rebuild pages and scripts; keep the images folder (photos live there permanently).
os.makedirs(os.path.join(OUT, 'images'), exist_ok=True)
shutil.rmtree(os.path.join(OUT, 'js'), ignore_errors=True)
os.makedirs(os.path.join(OUT, 'js'))
for f in os.listdir(OUT):
    if f.endswith('.html'):
        os.remove(os.path.join(OUT, f))


def blob_path(m):
    bid = m.group(1)
    for f in os.listdir(os.path.join(OUT, 'images')):
        if f.startswith(bid + '.'):
            return 'images/' + f
    src, typ = BLOBMAP[bid]
    name = bid + '.' + EXT[typ]
    dst = os.path.join(OUT, 'images', name)
    if not os.path.exists(dst):
        shutil.copyfile(src, dst)
    return 'images/' + name


def rewrite_refs(s):
    s = re.sub(r'/_blob/([0-9a-f]{32})', blob_path, s)
    for a, b in PAGES.items():
        s = s.replace(a, b)
    return s


HOLE = re.compile(r'\{\{(.*?)\}\}', re.S)
PATH = re.compile(r'^[A-Za-z_$][\w$]*(\.[\w$]+)*$')


class Compiler(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.code = []
        self.scope = []      # loop variable names currently in scope
        self.stack = []      # open sc-for / sc-if markers

    def expr(self, e):
        e = e.strip()
        if PATH.match(e):
            root = e.split('.')[0]
            if root in self.scope:
                return '(' + e + ')'
            if root in ('true', 'false', 'null', 'undefined'):
                return e
            return '(v.' + e + ')'
        return '(' + e + ')'

    def emit_lit(self, s):
        if s:
            self.code.append('o+=' + json.dumps(s) + ';')

    def text_with_holes(self, s, escape_lit):
        """Return a JS expression concatenating literal parts and holes."""
        parts, pos = [], 0
        for m in HOLE.finditer(s):
            lit = s[pos:m.start()]
            if lit:
                parts.append(json.dumps(html.escape(lit, quote=True) if escape_lit else lit))
            parts.append('E(' + self.expr(m.group(1)) + ')')
            pos = m.end()
        lit = s[pos:]
        if lit:
            parts.append(json.dumps(html.escape(lit, quote=True) if escape_lit else lit))
        return '+'.join(parts) if parts else '""'

    def attrs_code(self, attrs):
        for name, val in attrs:
            if name.startswith('hint-'):
                continue
            if val is None:
                self.emit_lit(' ' + name)
                continue
            m = HOLE.fullmatch(val.strip())
            if m and name.startswith('on'):
                self.code.append('o+=\' data-dc-%s="\'+R(%s)+\'"\';' % (name[2:], self.expr(m.group(1))))
            elif m and name == 'ref':
                self.code.append('o+=\' data-dc-ref="\'+R(%s)+\'"\';' % self.expr(m.group(1)))
            elif m and name in BOOL_ATTRS:
                self.code.append('if(%s)o+=%s;' % (self.expr(m.group(1)), json.dumps(' ' + name)))
            elif HOLE.search(val):
                self.code.append('o+=%s+%s+\'"\';' % (json.dumps(' ' + name + '="'), self.text_with_holes(val, True)))
            else:
                self.emit_lit(' %s="%s"' % (name, html.escape(val, quote=True)))

    def handle_starttag(self, tag, attrs):
        if tag == 'sc-for':
            a = dict(attrs)
            lst = HOLE.fullmatch(a['list'].strip()).group(1)
            var = a.get('as', 'item')
            self.code.append('for(const %s of (%s||[])){' % (var, self.expr(lst)))
            self.scope.append(var)
            self.stack.append('for')
            return
        if tag == 'sc-if':
            a = dict(attrs)
            cond = HOLE.fullmatch(a['value'].strip()).group(1)
            self.code.append('if(%s){' % self.expr(cond))
            self.stack.append('if')
            return
        self.emit_lit('<' + tag)
        self.attrs_code(attrs)
        self.emit_lit('>')

    def handle_startendtag(self, tag, attrs):
        self.emit_lit('<' + tag)
        self.attrs_code(attrs)
        self.emit_lit('/>' if tag in ('path', 'circle', 'rect', 'line', 'polyline', 'polygon') else '>')

    def handle_endtag(self, tag):
        if tag in ('sc-for', 'sc-if'):
            kind = self.stack.pop()
            if kind == 'for':
                self.scope.pop()
            self.code.append('}')
            return
        if tag in VOID and tag not in ('path', 'circle', 'rect', 'line', 'polyline', 'polygon'):
            return
        self.emit_lit('</' + tag + '>')

    def handle_data(self, data):
        if HOLE.search(data):
            self.code.append('o+=' + self.text_with_holes(data, False) + ';')
        else:
            self.emit_lit(data)

    def handle_entityref(self, name):
        self.emit_lit('&%s;' % name)

    def handle_charref(self, name):
        self.emit_lit('&#%s;' % name)

    def handle_comment(self, data):
        pass


def compile_template(markup):
    c = Compiler()
    c.feed(markup)
    c.close()
    return 'export function T(v,R,E){let o="";' + ''.join(c.code) + 'return o;}'


def netlify_form(markup):
    """Turn the Contact page form into a working Netlify form."""
    markup = markup.replace('<form style=', '<form name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="contact.html?sent=1" style=', 1)
    markup = re.sub(r'(<h2[^>]*>Send us a message</h2>)', r'\1\n<input type="hidden" name="form-name" value="contact"><p hidden><label>Leave this empty: <input name="bot-field"></label></p>', markup, count=1)
    markup = markup.replace('<input id="c-name" type="text"', '<input id="c-name" name="name" type="text" required')
    markup = markup.replace('<input id="c-email" type="email"', '<input id="c-email" name="email" type="email" required')
    markup = markup.replace('<select id="c-topic"', '<select id="c-topic" name="topic"')
    markup = markup.replace('<textarea id="c-msg"', '<textarea id="c-msg" name="message" required')
    markup = markup.replace('<button type="button" style="align-self: flex-start; min-height: 48px; padding: 0 28px; border: 0; border-radius: 6px; background: #0E3B2E;', '<button type="submit" style="align-self: flex-start; min-height: 48px; padding: 0 28px; border: 0; border-radius: 6px; background: #0E3B2E;')
    return markup


SENT_BANNER = ('<div id="sent-msg" hidden style="max-width: 1200px; margin: 24px auto 0; padding: 0 24px; box-sizing: border-box">'
               '<div style="background: #FFFFFF; border: 1px solid #DDE3DE; border-left: 6px solid #F2A93B; border-radius: 12px; padding: 18px 22px; font-family: \'Source Sans 3\', system-ui, sans-serif; font-size: 17px; color: #16201B">'
               '<strong>Thanks — your message was sent.</strong> We\'ll get back to you soon.</div></div>'
               '<script>if(location.search.indexOf("sent=1")>-1){document.getElementById("sent-msg").hidden=false;}</script>')

pages_meta = []
for srcname, outname in PAGES.items():
    raw = open(os.path.join(SRC, srcname)).read()
    raw = rewrite_refs(raw)
    title = re.search(r'<title>(.*?)</title>', raw, re.S).group(1).strip()
    helmet = re.search(r'<helmet>(.*?)</helmet>', raw, re.S).group(1)
    body = re.search(r'<x-dc>(.*?)</x-dc>', raw, re.S).group(1)
    body = re.sub(r'<helmet>.*?</helmet>', '', body, flags=re.S)
    if srcname == 'Contact.dc.html':
        body = netlify_form(body)
    script = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', raw, re.S).group(1)
    tpl = compile_template(body)
    base = outname[:-5]
    js = ("import { DCLogic, mount } from './dc.js';\n" + tpl + "\n" + script.strip() +
          "\nexport { Component };\nif (typeof document !== 'undefined') mount(Component, T, { accent: %s }, document.getElementById('app'));\n" % json.dumps(ACCENT))
    open(os.path.join(OUT, 'js', base + '.js'), 'w').write(js)
    pages_meta.append({'out': outname, 'base': base, 'title': title, 'helmet': helmet,
                       'sent': srcname == 'Contact.dc.html'})

shutil.copyfile(os.path.join(HERE, 'dc.js'), os.path.join(OUT, 'js', 'dc.js'))
json.dump({'out': OUT, 'pages': pages_meta}, open(os.path.join(HERE, 'pages.json'), 'w'))

# Pre-render every page with Node
r = subprocess.run(['node', os.path.join(HERE, 'ssr.mjs'), os.path.join(HERE, 'pages.json')], capture_output=True, text=True)
print(r.stdout, r.stderr)
if r.returncode:
    sys.exit(1)

for p in pages_meta:
    body_html = open(os.path.join(OUT, p['base'] + '.ssr.html')).read()
    os.remove(os.path.join(OUT, p['base'] + '.ssr.html'))
    extra = SENT_BANNER if p['sent'] else ''
    doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           '<title>%s</title>\n<link rel="icon" href="images/98b2130be4f89eab382b0331aed8713c.png">\n%s\n</head>\n<body>\n%s<div id="app">%s</div>\n'
           '<script type="module" src="js/%s.js"></script>\n</body>\n</html>\n') % (
        html.escape(p['title']), p['helmet'].strip(), extra, body_html, p['base'])
    open(os.path.join(OUT, p['out']), 'w').write(doc)
print('built', len(pages_meta), 'pages;', len(os.listdir(os.path.join(OUT, 'images'))), 'media files')
