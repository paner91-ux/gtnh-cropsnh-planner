"""Read biome dictionary tags out of the pack and write data/biomes.json.

A crop's liked biome tags are worth up to +28 Nutrient Score, more than half
the ceiling, and CropsNH never says which biomes carry which tags - the tags
belong to Forge and each biome is registered by whichever mod added it. So
this reads them from those mods directly, the same way the crop data is read
from CropsNH.

Two facts per biome are needed and both are in the bytecode:

  tags   every call whose descriptor is (BiomeGenBase, Type[]) - Forge's own
         registerBiomeType and the wrappers mods put in front of it
  name   the string literal next to the putstatic that stores the biome, which
         is how both Minecraft and the mods spell it out

Usage:  python tools/biomes.py <path to .minecraft> <path to prism libraries>
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.pardir)
JAVAP = os.environ.get('JAVAP', r'C:\Program Files\Java\jdk-25\bin\javap.exe')

# Forge is shipped obfuscated, so BiomeGenBase is `ahu` there and spelled out
# everywhere else. Both spellings have to be accepted, in the call descriptor
# and in the type of the field holding the biome.
BIOME_T = r'(?:net/minecraft/world/biome/BiomeGenBase|ahu)'
# the call every registration ends in, whoever wraps it
REG = re.compile(r'invoke\w+\s+#\d+\s+// Method [\w/$]*\.?(\w+):'
                 r'\(L' + BIOME_T + r';'
                 r'\[Lnet/minecraftforge/common/BiomeDictionary\$Type;\)')
TAG = re.compile(r'// Field net/minecraftforge/common/BiomeDictionary\$Type\.(\w+):')
# only fields that actually hold a biome, or Blocks.stone starts looking like one
BIOME_REF = re.compile(r'getstatic\s+#\d+\s+// Field (?:([\w/$]+)\.)?(\w+):L' + BIOME_T + r';')
PUT = re.compile(r'putstatic\s+#\d+\s+// Field (?:([\w/$]+)\.)?(\w+):L' + BIOME_T + r';')
STR = re.compile(r'ldc\w*\s+#\d+\s+// String (.+?)\s*$')


def javap(cp, cls):
    out = subprocess.run([JAVAP, '-p', '-c', '-constants', '-cp', cp, cls],
                         capture_output=True)
    return out.stdout.decode('utf-8', 'replace').split('\n')


def classes_mentioning(jar_dir, needle):
    """Class names whose bytes contain a string, so javap runs on few files."""
    out = []
    for base, _, files in os.walk(jar_dir):
        for f in files:
            if not f.endswith('.class'):
                continue
            p = os.path.join(base, f)
            with open(p, 'rb') as fh:
                if needle in fh.read():
                    rel = os.path.relpath(p, jar_dir)[:-6]
                    out.append(rel.replace(os.sep, '.'))
    return sorted(out)


def read_registrations(lines, owner):
    """(owner.field, [tags]) for every registration call in a disassembly.

    javap prints a field of the class being disassembled without its owner, so
    the owner has to be put back or the reference never joins with the name.
    """
    out, biome, tags = [], None, []
    for l in lines:
        m = BIOME_REF.search(l)
        if m and 'BiomeDictionary' not in l:
            biome, tags = f'{m.group(1) or owner}.{m.group(2)}', []
            continue
        m = TAG.search(l)
        if m and biome:
            tags.append(m.group(1))
            continue
        if REG.search(l) and biome and tags:
            out.append((biome, tags))
            biome, tags = None, []
    return out


def read_names(lines, owner):
    """owner.field -> display name, from the string sitting next to the store."""
    out, recent = {}, []
    for l in lines:
        m = STR.search(l)
        if m:
            recent.append(m.group(1))
            continue
        m = PUT.search(l)
        if m and recent:
            out[f'{m.group(1) or owner}.{m.group(2)}'] = recent[-1]
            recent = []
    return out


def scan(jar, label, name_hint=None):
    """Pull registrations and names out of one jar."""
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(jar) as z:
        z.extractall(tmp)
    regs, names = [], {}
    for cls in classes_mentioning(tmp, b'BiomeDictionary'):
        lines = javap(tmp, cls)
        regs.extend(read_registrations(lines, cls.replace('.', '/')))
        names.update(read_names(lines, cls.replace('.', '/')))
    if name_hint:                       # vanilla keeps its names in one class
        names.update(read_names(javap(tmp, name_hint), name_hint))
    return regs, names, label


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    mc, libs = sys.argv[1], sys.argv[2]

    vanilla = os.path.join(libs, 'com', 'mojang', 'minecraft', '1.7.10',
                           'minecraft-1.7.10-client.jar')
    forge = None
    for base, _, files in os.walk(os.path.join(libs, 'net', 'minecraftforge')):
        for f in files:
            if f.endswith('universal.jar'):
                forge = os.path.join(base, f)
    if not forge or not os.path.exists(vanilla):
        raise SystemExit('nie znalazlem jara vanilli albo forge w ' + libs)

    jobs = [(forge, 'minecraft', 'ahu'), (vanilla, 'minecraft', 'ahu')]
    mods = os.path.join(mc, 'mods')
    for f in sorted(os.listdir(mods)):
        if not f.endswith('.jar'):
            continue
        p = os.path.join(mods, f)
        try:
            with zipfile.ZipFile(p) as z:
                hit = any(b'registerBiomeType' in z.read(n)
                          for n in z.namelist() if n.endswith('.class'))
        except Exception:
            continue
        if hit:
            jobs.append((p, f.split('-')[0], None))

    regs, names, source = [], {}, {}
    for jar, label, hint in jobs:
        r, n, _ = scan(jar, label, hint)
        for field, tags in r:
            regs.append((field, tags, label))
        names.update(n)
        print(f'{label:<18} {len(r):>4} registrations, {len(n):>4} names  '
              f'({os.path.basename(jar)})')

    biomes, unresolved = {}, []
    for field, tags, label in regs:
        name = names.get(field)
        if not name:
            unresolved.append(field)
            continue
        e = biomes.setdefault(name, {'tags': [], 'from': label})
        for t in tags:
            if t not in e['tags']:
                e['tags'].append(t)
    for e in biomes.values():
        e['tags'].sort()

    out = {'biomes': dict(sorted(biomes.items()))}
    with io.open(os.path.join(ROOT, 'data', 'biomes.json'), 'w',
                 encoding='utf-8', newline='') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f'\n{len(biomes)} biomes written')
    if unresolved:
        u = sorted(set(unresolved))
        print(f'WARNING: {len(u)} registrations had no name and were dropped')
        for x in u[:12]:
            print('  ' + x)


if __name__ == '__main__':
    main()
