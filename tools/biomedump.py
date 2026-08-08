"""Read NEI's biome dump and put rainfall and the runtime tags into biomes.json.

biomes.py reads biome tags out of the bytecode, from the arguments each mod
hands to registerBiomeType. That is one step removed from what the game
answers, and two things only the running game knows are missing:

  rainfall   CropsNH turns it into up to +14 Nutrient Score, and it is the
             only term that decides whether a crop grows at all in a biome
             whose tags it does not like. Mods set it every which way - RWG
             passes a type number to a shared constructor and branches on it -
             so reading it out of the bytecode is a project of its own.

  the tags the game actually reports. Three of Forge's types are compounds:
  WATER is {OCEAN, RIVER}, DESERT is {SANDY}, FROZEN is {SNOWY}. A biome
  registered as WATER answers OCEAN and RIVER to getTypesForBiome() and never
  answers WATER, and getTypesForBiome() is exactly what CropsNH calls. The
  bytecode reading sees the argument, so it keeps a tag the game never
  produces - and CropsNH's own language file agrees, naming all 28 leaf types
  and none of the three compounds.

So this refines what biomes.py produced rather than replacing it: `from` stays
as the jar scan found it, `tags` and `rain` come from the game. Run it after
biomes.py, not instead of it.

The dump is NEI Options -> Tools -> Data Dumps -> Biome, which writes
<.minecraft>/dumps/biome.csv. It walks the whole biome array rather than
anything the interface is showing, so no filter or panel setting can trim it.

Usage:  python tools/biomedump.py <path to .minecraft>
"""
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    dump = os.path.join(sys.argv[1], 'dumps', 'biome.csv')
    if not os.path.isfile(dump):
        raise SystemExit(f'no dump at {dump} - see the usage note in this file')

    with io.open(dump, encoding='utf-8', errors='replace', newline='') as f:
        rows = [r for r in csv.DictReader(f) if r.get('Name') and r['Name'] != 'null']

    # The array is indexed by biome id and holds one entry per id, so the same
    # biome comes back thousands of times; the first by id is the real one.
    # Two different biomes can still share a display name - BoP and RWG both
    # ship an Oasis - and the page is keyed by name, so that has to be flagged
    # rather than silently resolved.
    first, clash = {}, {}
    for r in rows:
        name = r['Name']
        fact = (r['Rainfall'], r['Types'] or '')
        if name not in first:
            first[name] = r
        elif fact != (first[name]['Rainfall'], first[name]['Types'] or ''):
            clash.setdefault(name, set()).add(fact)

    path = os.path.join(ROOT, 'data', 'biomes.json')
    with io.open(path, encoding='utf-8') as f:
        data = json.load(f)
    biomes = data['biomes']

    missing = sorted(k for k in biomes if k not in first)
    if missing:
        raise SystemExit(
            f'{len(missing)} biomes in data/biomes.json are not in the dump, so '
            f'the two came from different packs: {missing[:8]}')

    changed, rained = [], 0
    for name, e in biomes.items():
        row = first[name]
        tags = sorted(t.strip() for t in (row['Types'] or '').split(',') if t.strip())
        if tags and tags != sorted(e['tags']):
            changed.append((name, sorted(e['tags']), tags))
            e['tags'] = tags
        e['rain'] = float(row['Rainfall'])
        rained += 1

    data['biomes'] = {k: {'tags': v['tags'], 'rain': v['rain'], 'from': v['from']}
                      for k, v in sorted(biomes.items())}
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        json.dump(data, f, indent=1, ensure_ascii=False)

    print(f'{len(first)} biomes in the dump, {rained} matched and given a rainfall')
    if changed:
        print(f'\n{len(changed)} tag lists corrected to what the game reports:')
        for name, was, now in changed:
            print(f'  {name:<22} {",".join(was)}  ->  {",".join(now)}')
    for name, facts in sorted(clash.items()):
        print(f'\nnote: two different biomes are called {name}; kept the one with '
              f'the lowest id, the other is {sorted(facts)}')
    extra = sorted(k for k in first if k not in biomes)
    if extra:
        print(f'\nnote: {len(extra)} biomes are in the dump but not in '
              f'data/biomes.json, so biomes.py never saw them register a tag: '
              f'{", ".join(extra[:6])}...')
    print('\nwrote data/biomes.json\nnow run:  python tools/build.py')


if __name__ == '__main__':
    main()
