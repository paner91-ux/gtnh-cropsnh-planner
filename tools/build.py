"""Inline data/crops.json into the page template and write index.html.

One file per language: English at the root, every other language in its own
directory. Text lives in tools/i18n/<code>.json and the template refers to it
as {{key}}; nothing about translation survives into the built page.

Usage:  python tools/build.py
"""
import base64
import copy
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)

SITE = 'https://paner91-ux.github.io/gtnh-cropsnh-planner/'

KEY = re.compile(r'\{\{([A-Za-z0-9_.]+)\}\}')
# values are dropped into JS template literals, so these have to survive intact
INTERP = re.compile(r'\$\{[^{}]*\}')
# keys build.py uses itself instead of substituting them into the template
HEAD_KEYS = {'lang.name', 'lang.code', 'meta.title', 'meta.description', 'nav.lang'}
# soil labels go into the data blob rather than the markup, so they never
# appear as {{...}} - they are this page's wording, not the mod's, which is
# why they live in the catalogue and not in data/crops.json
DATA_PREFIXES = ('soil.gloss.', 'soil.short.')


def order(codes):
    """English first: it is the source text and the canonical page."""
    return ['en'] + sorted(c for c in codes if c != 'en')


def url_of(code):
    return SITE if code == 'en' else f'{SITE}{code}/'


def path_from(here, there):
    """Every language but English sits one directory down, and only one."""
    if here == there:
        return './'
    if there == 'en':
        return '../'
    return f'{there}/' if here == 'en' else f'../{there}/'


def head(code, cats):
    """Catalogue values are HTML as written, so only the quote needs escaping."""
    cat = cats[code]
    others = len(cats) > 1
    alt = ''
    if others:
        for c in order(cats):
            alt += f'<link rel="alternate" hreflang="{c}" href="{url_of(c)}">\n'
        alt += f'<link rel="alternate" hreflang="x-default" href="{url_of("en")}">\n'
    return (f'<title>{cat["meta.title"]}</title>\n'
            f'<meta name="description" content="{cat["meta.description"].replace(chr(34), "&quot;")}">\n'
            f'<link rel="canonical" href="{url_of(code)}">\n' + alt)


def langnav(code, cats):
    """Left out entirely while there is only one language to offer.

    A summary naming the current language with the rest folded behind it, and
    plain links inside rather than a <select>: writeHash() hangs the current
    hash on every link, which is what keeps your place across a switch.
    """
    if len(cats) < 2:
        return ''
    links = ''.join(
        f'<a href="{path_from(code, c)}" hreflang="{c}" lang="{c}" role="menuitem"'
        f'{" aria-current=" + chr(34) + "page" + chr(34) if c == code else ""}'
        f'>{cats[c]["lang.name"]}</a>'
        for c in order(cats))
    return (f'<nav class="langs" aria-label="{cats[code]["nav.lang"]}">'
            f'<details class="langpick" id="langpick">'
            f'<summary>{cats[code]["lang.name"]}</summary>'
            f'<div class="langmenu" role="menu">{links}</div>'
            f'</details></nav>')


def sitemap(cats):
    alt = ''.join(f'\n    <xhtml:link rel="alternate" hreflang="{c}" href="{url_of(c)}"/>'
                  for c in order(cats)) if len(cats) > 1 else ''
    urls = ''.join(f'  <url>\n    <loc>{url_of(c)}</loc>{alt}\n  </url>\n' for c in order(cats))
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + urls + '</urlset>\n')


def load_catalogues():
    out = {}
    for path in sorted(glob.glob(os.path.join(HERE, 'i18n', '*.json'))):
        code = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding='utf-8') as f:
            out[code] = json.load(f)
    if 'en' not in out:
        raise SystemExit('tools/i18n/en.json is missing - English is the source text')
    return out


def check(code, cat, base, used, warn):
    """Refuse to build rather than ship a page with a broken string."""
    err = []
    if code == 'en':
        for k in sorted(used - set(base)):
            err.append(f'{k} is used in the template but not in en.json')
        for k in sorted(set(base) - used - HEAD_KEYS):
            if not k.startswith(DATA_PREFIXES):
                err.append(f'{k} is in en.json but nothing uses it')
    else:
        for k in sorted(set(cat) - set(base)):
            err.append(f'{k} is not a key in en.json')
        for k in sorted(HEAD_KEYS - set(cat)):
            err.append(f'{k} has no translation, and the page head needs one')

    for k, v in sorted(cat.items()):
        if not isinstance(v, str):
            err.append(f'{k} is not a string')
            continue
        if '`' in v:
            err.append(f'{k} contains a backtick, which would end a template literal')
        if '{{' in v:
            err.append(f'{k} contains {{{{, which would leave an unresolved key')
        if k not in base:
            continue
        mine, theirs = INTERP.findall(v), INTERP.findall(base[k])
        # inventing a ${...} means referring to something that does not exist there
        for x in sorted(set(mine) - set(theirs)):
            err.append(f'{k} uses {x}, which the English string does not have')
        # dropping one is only ever a translation losing a number, so it warns:
        # English pluralises inside the string and other languages should not
        for x in sorted(set(theirs) - set(mine)):
            warn.append(f'{code}.json: {k} leaves out {x}')
    if err:
        raise SystemExit(f'{code}.json:\n  - ' + '\n  - '.join(err))


with open(os.path.join(ROOT, 'data', 'crops.json'), encoding='utf-8') as f:
    data = json.load(f)

# biome tags come from Forge and the mods that add biomes, not from CropsNH,
# so they are extracted separately and merged in here
bpath = os.path.join(ROOT, 'data', 'biomes.json')
if os.path.exists(bpath):
    with open(bpath, encoding='utf-8') as f:
        data['biomes'] = json.load(f)['biomes']

# fields the page never reads
for c in data['crops'].values():
    c.pop('cls', None)
    c.pop('internal', None)
for m in data['mutations']:
    m.pop('req', None)


def localise(code, cat, base):
    """One data blob per language.

    Crop, pool, sub-soil and biome-tag names are the mod's own strings, so a
    translation of them is read out of the pack by langs.py and lands in
    data/lang.<code>.json. Anything that file leaves out keeps the English the
    jar gave us, which is also what the game shows for that language.

    The soil labels are the other way round: they are this page's wording, so
    they come from the catalogue and are translated like any other string.
    """
    d = copy.deepcopy(data)
    path = os.path.join(ROOT, 'data', f'lang.{code}.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            tr = json.load(f)
        for cid, name in tr.get('crops', {}).items():
            if cid in d['crops']:
                d['crops'][cid]['name'] = name
        for field in ('poolNames', 'subsoilDesc', 'biomeNames'):
            d[field].update(tr.get(field, {}))

    d['soilGloss'] = {k: cat.get(f'soil.gloss.{k}', base[f'soil.gloss.{k}'])
                      for k in d['soilBase']}
    d['soilShort'] = {k: cat.get(f'soil.short.{k}', base[f'soil.short.{k}'])
                      for k in d['soilBase']}
    del d['soilBase']
    for c in d['crops'].values():
        c.pop('nameKey', None)
    return d

with open(os.path.join(HERE, 'page.src.html'), encoding='utf-8') as f:
    src = f.read()

if '__DATA__' not in src:
    raise SystemExit('page.src.html has no __DATA__ placeholder')

cats = load_catalogues()
base = cats['en']
used = set(KEY.findall(src))
warn = []
for code, cat in cats.items():
    check(code, cat, base, used, warn)
for w in warn:
    print('warning: ' + w)

# every base soil needs both labels, or the page would print a bare key
for k in data['soilBase']:
    for kind in ('gloss', 'short'):
        if f'soil.{kind}.{k}' not in base:
            raise SystemExit(f'en.json has no soil.{kind}.{k}, which data/crops.json asks for')

# favicon goes in as a data URI so each page stays a single self-contained file
with open(os.path.join(HERE, 'favicon.svg'), encoding='utf-8') as f:
    icon = base64.b64encode(f.read().encode()).decode()

for code in order(cats):
    cat = cats[code]
    blob = json.dumps(localise(code, cat, base), ensure_ascii=False, separators=(',', ':'))
    # an untranslated string falls back to English rather than showing its key
    text = KEY.sub(lambda m: cat.get(m.group(1), base[m.group(1)]), src)
    nav = langnav(code, cats)
    text = re.sub(r'[ \t]*__LANGS__\n', f'    {nav}\n' if nav else '', text)
    page = (f'<!doctype html>\n<html lang="{code}">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            + head(code, cats) +
            f'<link rel="icon" href="data:image/svg+xml;base64,{icon}">\n'
            '<meta name="theme-color" content="#3D7A33">\n'
            '</head>\n<body>\n' + text.replace('__DATA__', blob) + '\n</body>\n</html>\n')

    out = os.path.join(ROOT, 'index.html') if code == 'en' else os.path.join(ROOT, code, 'index.html')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(page)

    done = sum(1 for k in base if k in cat)
    where = os.path.relpath(out, ROOT).replace(os.sep, '/')
    print(f'{where:<16}{len(page):>9,} bytes  {code}  {done}/{len(base)} strings')

with open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8') as f:
    f.write(sitemap(cats))

print(f'{"":<16}{len(data["crops"])} crops, {len(data["mutations"])} recipes')
