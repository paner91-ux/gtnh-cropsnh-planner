"""Inline data/crops.json into the page template and write index.html.

One file per language: English at the root, every other language in its own
directory. Text lives in tools/i18n/<code>.json and the template refers to it
as {{key}}; nothing about translation survives into the built page.

Usage:  python tools/build.py
"""
import base64
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)

KEY = re.compile(r'\{\{([A-Za-z0-9_.]+)\}\}')
# values are dropped into JS template literals, so these have to survive intact
INTERP = re.compile(r'\$\{[^{}]*\}')
# keys build.py uses itself instead of substituting them into the template
HEAD_KEYS = {'lang.name', 'lang.code', 'meta.title', 'meta.description'}


def load_catalogues():
    out = {}
    for path in sorted(glob.glob(os.path.join(HERE, 'i18n', '*.json'))):
        code = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding='utf-8') as f:
            out[code] = json.load(f)
    if 'en' not in out:
        raise SystemExit('tools/i18n/en.json is missing - English is the source text')
    return out


def check(code, cat, base, used):
    """Refuse to build rather than ship a page with a broken string."""
    err = []
    if code == 'en':
        for k in sorted(used - set(base)):
            err.append(f'{k} is used in the template but not in en.json')
        for k in sorted(set(base) - used - HEAD_KEYS):
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
        # a translation that drops or invents a ${...} breaks the page it is on
        if k in base and sorted(INTERP.findall(v)) != sorted(INTERP.findall(base[k])):
            err.append(f'{k} does not carry the same ${{...}} as English:\n'
                       f'      en: {sorted(INTERP.findall(base[k]))}\n'
                       f'      {code}: {sorted(INTERP.findall(v))}')
    if err:
        raise SystemExit(f'{code}.json:\n  - ' + '\n  - '.join(err))


with open(os.path.join(ROOT, 'data', 'crops.json'), encoding='utf-8') as f:
    data = json.load(f)

# fields the page never reads
for c in data['crops'].values():
    c.pop('cls', None)
    c.pop('internal', None)
for m in data['mutations']:
    m.pop('req', None)

with open(os.path.join(HERE, 'page.src.html'), encoding='utf-8') as f:
    src = f.read()

if '__DATA__' not in src:
    raise SystemExit('page.src.html has no __DATA__ placeholder')

cats = load_catalogues()
base = cats['en']
used = set(KEY.findall(src))
for code, cat in cats.items():
    check(code, cat, base, used)

blob = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

# favicon goes in as a data URI so each page stays a single self-contained file
with open(os.path.join(HERE, 'favicon.svg'), encoding='utf-8') as f:
    icon = base64.b64encode(f.read().encode()).decode()

# English first, so its line of output reads as the main one
for code in ['en'] + sorted(k for k in cats if k != 'en'):
    cat = cats[code]
    # an untranslated string falls back to English rather than showing its key
    text = KEY.sub(lambda m: cat.get(m.group(1), base[m.group(1)]), src)
    page = (f'<!doctype html>\n<html lang="{code}">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
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

print(f'{"":<16}{len(data["crops"])} crops, {len(data["mutations"])} recipes')
