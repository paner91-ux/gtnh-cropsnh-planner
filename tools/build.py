"""Inline data/crops.json into the page template and write index.html.

Usage:  python tools/build.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)

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

body = src.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')))

page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '</head>\n<body>\n' + body + '\n</body>\n</html>\n')

out = os.path.join(ROOT, 'index.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(page)

print(f'index.html  {len(page):,} bytes')
print(f'            {len(data["crops"])} crops, {len(data["mutations"])} recipes')
