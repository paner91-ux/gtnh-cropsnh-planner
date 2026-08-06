"""Read the pack's translations and write data/lang.<code>.json.

The jar carries only en_US.lang, so every other language comes from the pack:
GTNH translates through config/txloader/load/<Mod>[modid]/lang/<code>.lang,
and vanilla's own translations are not in the client jar either - they sit in
the launcher's content-addressed asset store, listed by assets/indexes.

Both have to be read, because 29 crops borrow their display name from another
mod: CropCard.getUnlocalizedName() is overridden to return item.wheat.name,
tile.witchery:belladonna.name and the like. extract.py records that key as
nameKey, and this script resolves it wherever it happens to live.

Biome names are deliberately absent. In 1.7.10 a biome name is a plain string
passed to setBiomeName(), with no language key anywhere in the pack, so the
game shows them in English too and translating them here would only break the
match with Nature's Compass.

Usage:  python tools/langs.py <path to .minecraft> <path to launcher assets>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)

# our page code -> the code Minecraft files use
MC_CODE = {'ja': 'ja_JP', 'pl': 'pl_PL', 'zh': 'zh_CN'}

# share of crop names a language has to reach before the page uses any of
# them at all - see the note where it is applied
MIN_NAMES = 0.9


def read_lang(path_or_text, is_text=False):
    out = {}
    lines = path_or_text.splitlines() if is_text else open(
        path_or_text, encoding='utf-8', errors='replace')
    for line in lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, _, v = line.partition('=')
            out.setdefault(k.strip(), v.strip())
    return out


def from_txloader(mc, code):
    """Every mod's catalogue for one language, merged into a single table."""
    base = os.path.join(mc, 'config', 'txloader', 'load')
    if not os.path.isdir(base):
        raise SystemExit(f'no txloader directory under {mc}')
    out = {}
    used = 0
    for mod in sorted(os.listdir(base)):
        p = os.path.join(base, mod, 'lang', code + '.lang')
        if os.path.isfile(p):
            out.update(read_lang(p))
            used += 1
    return out, used


def from_vanilla(assets, code):
    """Vanilla ships one language in the jar and the rest through the asset
    store, so this goes through the index rather than looking for a file."""
    idx = os.path.join(assets, 'indexes', '1.7.10.json')
    if not os.path.isfile(idx):
        print(f'  note: no asset index at {idx}, skipping vanilla')
        return {}
    with open(idx, encoding='utf-8') as f:
        objects = json.load(f)['objects']
    entry = objects.get(f'minecraft/lang/{code}.lang')
    if not entry:
        print(f'  note: vanilla has no {code}, skipping')
        return {}
    h = entry['hash']
    blob = os.path.join(assets, 'objects', h[:2], h)
    if not os.path.isfile(blob):
        print(f'  note: {code} is in the index but not downloaded, skipping')
        return {}
    with open(blob, encoding='utf-8', errors='replace') as f:
        return read_lang(f.read(), is_text=True)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    mc, assets = sys.argv[1], sys.argv[2]

    with open(os.path.join(ROOT, 'data', 'crops.json'), encoding='utf-8') as f:
        data = json.load(f)
    crops = data['crops']

    codes = sorted(c for c in MC_CODE
                   if os.path.isfile(os.path.join(HERE, 'i18n', c + '.json')))
    if not codes:
        raise SystemExit('no catalogue in tools/i18n needs translated data')

    for code in codes:
        mcc = MC_CODE[code]
        table, mods = from_txloader(mc, mcc)
        vanilla = from_vanilla(assets, mcc)
        # a mod that ships its own copy of a vanilla key wins over vanilla
        merged = dict(vanilla)
        merged.update(table)

        # only what differs from the English the page already carries, so a
        # language that has not translated a string simply falls back to it
        def pick(key, english):
            v = merged.get(key)
            return v if v and v != english else None

        out = {}
        names = {c['id']: pick(c['nameKey'], c['name']) for c in crops.values()}
        out['crops'] = {k: v for k, v in sorted(names.items()) if v}
        # The pack's catalogues track a newer CropsNH than the jar the data was
        # read from, and one namespace was renamed on the way: the sub-soil
        # descriptions are cropsnh_growthReq.subSoil.* in 2.0.101 and
        # cropsnh_growthReq.blockUnder.* in the translations. Try both rather
        # than silently returning nothing.
        for field, prefixes in (
                ('poolNames', ['cropsnh_mutationPool.']),
                ('subsoilDesc', ['cropsnh_growthReq.blockUnder.',
                                 'cropsnh_growthReq.subSoil.']),
                ('biomeNames', ['cropsnh_tooltip.biomeTag.'])):
            got = {}
            for k, v in data[field].items():
                got[k] = next((t for t in (pick(p + k, v) for p in prefixes) if t), None)
            out[field] = {k: v for k, v in sorted(got.items()) if v}

        print(f'{code} ({mcc}): {mods} mod catalogues'
              f'{", vanilla" if vanilla else ""}')
        print(f'   crop names   {len(out["crops"]):>4} / {len(crops)}')
        for field in ('poolNames', 'subsoilDesc', 'biomeNames'):
            print(f'   {field:<12} {len(out[field]):>4} / {len(data[field])}')

        # Half a set of names is worse than none: the page would mix two
        # languages, and the prose in tools/i18n names crops in plain text,
        # so those sentences would stop matching the lists beside them.
        share = len(out['crops']) / len(crops)
        path = os.path.join(ROOT, 'data', f'lang.{code}.json')
        if share < MIN_NAMES:
            if os.path.exists(path):
                os.remove(path)
                print(f'   removed {os.path.relpath(path, ROOT)}')
            print(f'   skipped: only {share:.0%} of the names are translated, '
                  f'and the page keeps English below {MIN_NAMES:.0%}')
            continue

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=1, ensure_ascii=False, sort_keys=True)
        missing = [c['name'] for c in crops.values() if c['id'] not in out['crops']]
        if missing:
            print(f'   untranslated: {", ".join(sorted(missing))}')
        print(f'   wrote {os.path.relpath(path, ROOT)}')


main()
