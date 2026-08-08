"""Read NEI's data dumps and write data/altseeds.json.

An alternate seed is an ordinary item registered as a stand-in for a crop's
seed: planted on a crop stick it becomes that crop at 1/1/1. extract.py can
tell from the bytecode *which* crops have one, because every
addAlternateSeed() call sits in a crop constructor, but not *what* the item
is - the argument is a registry id, an ore dictionary name or an obfuscated
vanilla field, none of which is the name a player reads in NEI.

The game knows, and CropsNH ships a dumper for it. Two CSVs are needed, both
written to <.minecraft>/dumps by NEI Options -> Tools -> Data Dumps:

  Crops NH -> Alternate Seeds   alternateSeed.csv   item, meta -> crop
  Item Panel (mode CSV)         itempanel.csv       item, meta -> display name

Turn *off* Collapsible Items (NEI Options -> Inventory) before dumping the
item panel. With groups collapsed the panel holds one entry per group, so
every sapling but oak and every flower but one are missing from the dump.

The display names are in whatever language the game was running, so the code
of that language is the second argument. A run adds one language and leaves
the others alone.

Usage:  python tools/altseeds.py <path to .minecraft> [language code]
"""
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)


def read_csv(path):
    if not os.path.isfile(path):
        raise SystemExit(f'no dump at {path} - see the usage note in this file')
    with open(path, encoding='utf-8', errors='replace', newline='') as f:
        return list(csv.DictReader(f))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    mc = sys.argv[1]
    code = sys.argv[2] if len(sys.argv) > 2 else 'en'

    dumps = os.path.join(mc, 'dumps')
    seeds = read_csv(os.path.join(dumps, 'alternateSeed.csv'))
    panel = read_csv(os.path.join(dumps, 'itempanel.csv'))

    with open(os.path.join(ROOT, 'data', 'crops.json'), encoding='utf-8') as f:
        crops = json.load(f)['crops']

    # The dump names a crop by its internalId. That is usually what extract.py
    # stored, but 29 crops override getUnlocalizedName() and borrow another
    # mod's key, so for those `internal` holds the borrowed key instead. The
    # field name with a lower first letter is the internalId in every one of
    # those cases, so both spellings map to the same crop.
    by_id = {}
    for field, c in crops.items():
        by_id[c['internal']] = field
        by_id.setdefault(field[0].lower() + field[1:], field)

    names = {}
    wildcard = collections.defaultdict(dict)
    for row in panel:
        key = (row['Item Name'], row['Item meta'])
        names.setdefault(key, row['Display Name'])
        wildcard[row['Item Name']].setdefault(row['Item meta'], row['Display Name'])

    def display(item, meta):
        if (item, meta) in names:
            return names[(item, meta)]
        # a null meta in the registry dumps as *, meaning any subtype of that
        # item plants the crop; the panel lists them one by one
        if meta == '*' and wildcard.get(item):
            metas = sorted(wildcard[item], key=lambda m: int(m) if m.isdigit() else 0)
            return wildcard[item][metas[0]]
        return None

    found = collections.defaultdict(set)
    unknown_crop = set()
    unnamed = []
    for row in seeds:
        cid = row['CropCard'].split(':', 1)[-1]
        if cid not in by_id:
            unknown_crop.add(cid)
            continue
        name = display(row['Item'], row['Meta'])
        if name is None:
            unnamed.append(f"{row['Item']}:{row['Meta']}")
            continue
        found[by_id[cid]].add(name)

    if unknown_crop:
        raise SystemExit('alternateSeed.csv names crops that data/crops.json '
                         'does not have, so the two were built from different '
                         f'mod versions: {sorted(unknown_crop)}')
    if unnamed:
        raise SystemExit(
            f'{len(unnamed)} items are in alternateSeed.csv but not in '
            f'itempanel.csv: {unnamed[:8]}\n'
            'Turn off NEI Options -> Inventory -> Collapsible Items and dump '
            'the item panel again - a collapsed group dumps as one entry.')

    # The bytecode said which crops have an alternate seed and the running
    # game says it again; disagreeing means one of the two is being read wrong.
    flagged = {f for f, c in crops.items() if c.get('altSeed')}
    if flagged != set(found):
        raise SystemExit(
            'the dump and the altSeed flag in data/crops.json disagree.\n'
            f'  flagged but not in the dump: {sorted(flagged - set(found))}\n'
            f'  in the dump but not flagged: {sorted(set(found) - flagged)}')

    path = os.path.join(ROOT, 'data', 'altseeds.json')
    out = {}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            out = json.load(f)
    # Several mods can offer the same plant, and the four turnip entries carry
    # two names between them, so the list is of names rather than of items.
    out[code] = {k: sorted(v) for k, v in sorted(found.items())}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({k: out[k] for k in sorted(out)}, f, indent=1, ensure_ascii=False)
        f.write('\n')

    total = sum(len(v) for v in out[code].values())
    print(f'{len(panel)} items in the panel, {len(seeds)} alternate seeds')
    print(f'{code}: {len(out[code])} crops, {total} names')
    print(f'languages in the file: {", ".join(sorted(out))}')
    print('wrote data/altseeds.json\nnow run:  python tools/build.py')


if __name__ == '__main__':
    main()
