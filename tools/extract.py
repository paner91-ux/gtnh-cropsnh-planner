"""Extract crops, pools and mutations from CropsNH bytecode into crops.json."""
import re, json, os, sys
import jvparse

HERE = os.path.dirname(os.path.abspath(__file__))
JAR = os.path.join(HERE, '_jar')

classes = jvparse.parse([os.path.join(HERE, f) for f in (
    'dump_crops.txt', 'dump_croploader.txt', 'dump_mutationloader.txt',
    'dump_subsoil.txt', 'dump_soil.txt', 'dump_soiltypes.txt')])

# ---------------------------------------------------------------- language file
lang = {}
with open(os.path.join(JAR, 'assets/cropsnh/lang/en_US.lang'), encoding='utf-8', errors='replace') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, _, v = line.partition('=')
            lang[k.strip()] = v.strip()


def L(key, fallback=None):
    return lang.get(key, fallback)


# ---------------------------------------------------------------- CropLoader: FIELD -> class
loader = classes['com.gtnewhorizon.cropsnh.loaders.CropLoader']
loader_code = []
for sig, lines in loader.methods.items():
    loader_code.extend(lines)

field_to_class = {}
loader_biomes = {}          # tags attached by the loader rather than by the crop class
pending_new = []
pending_biomes = []
for line in loader_code:
    m = re.search(r'new\s+#\d+\s+// class ([\w/$]+)', line)
    if m:
        pending_new.append(m.group(1).replace('/', '.'))
        continue
    m = re.search(r'// Field [\w/$]*BiomeDictionary\$Type\.([\w$]+):', line)
    if m:
        pending_biomes.append(m.group(1))
        continue
    m = re.search(r'putstatic\s+#\d+\s+// Field [\w/$]*CropsNHCrops\.([\w$]+):', line)
    if m and pending_new:
        # The crop object is constructed first and its constructor arguments after it,
        # so the last `new` before the store is usually a Color or an ItemStack, not
        # the crop. Take the most recent CropsNH class instead: that skips the
        # arguments, and it also survives a crop that is registered without a field.
        own = [c for c in pending_new if c.startswith('com.gtnewhorizon.cropsnh')]
        if not own:
            raise SystemExit('brak klasy CropsNH przed polem ' + m.group(1))
        field_to_class[m.group(1)] = own[-1]
        loader_biomes[m.group(1)] = pending_biomes[:]
        pending_new = []
        pending_biomes = []

# ---------------------------------------------------------------- class hierarchy
def chain(clsname):
    out = []
    seen = set()
    while clsname and clsname in classes and clsname not in seen:
        seen.add(clsname)
        out.append(classes[clsname])
        clsname = classes[clsname].sup
    return out


# crops whose tier no class in the chain states as a constant, so the default
# below is a guess rather than a reading - see the report at the end
guessed_tier = []


def resolve_int(clsname, method, default=None):
    for k in chain(clsname):
        code = k.code(method)
        if not code:
            continue
        for line in code:
            m = re.search(r'(?:bipush|sipush)\s+(-?\d+)', line)
            if m:
                return int(m.group(1))
            m = re.search(r'ldc\w*\s+#\d+\s+// int (-?\d+)', line)
            if m:
                return int(m.group(1))
            m = re.search(r'\biconst_(m?\d)\b', line)
            if m:
                return -1 if m.group(1) == 'm1' else int(m.group(1))
    return default


def static_soil(k, field):
    """Soil lists assigned to `field` in the class initialiser.

    Rubyne keeps its list in a static field of its own and getSoilTypes() only
    hands that field back, so the constant is nowhere near the getter.
    """
    out = []
    pending = None
    for line in k.code('<clinit>'):
        m = re.search(r'// Field [\w/$]*CropsNHSoilTypes\.([\w$]+):', line)
        if m:
            pending = m.group(1)
            continue
        if pending and re.search(r'putstatic\s+#\d+\s+// Field ' + re.escape(field) + ':', line):
            out.append(pending)
            pending = None
    return out


def resolve_soil(clsname):
    for k in chain(clsname):
        code = k.code('getSoilTypes')
        if code:
            f = jvparse.fieldrefs(code, 'CropsNHSoilTypes')
            if f:
                return f
            own = re.search(r'// Field ([\w$]+):L[\w/$]*ISoilList;', '\n'.join(code))
            if own:
                f = static_soil(k, own.group(1))
                if f:
                    print(f'note: {clsname.split(".")[-1]} reads its soil from a '
                          f'static field, resolved to {f}')
                    return f
    return ['farmland']


CTOR_CACHE = {}


def ctor_code(clsname):
    """Constructor bytecode of the class plus all of its superclasses."""
    if clsname in CTOR_CACHE:
        return CTOR_CACHE[clsname]
    out = []
    for k in chain(clsname):
        simple = k.name.rsplit('.', 1)[-1]
        out.extend(k.code(simple, simple.split('$')[-1]))
    CTOR_CACHE[clsname] = out
    return out


# ---------------------------------------------------------------- crop properties
def light_reqs(code):
    """(maxLight, minLight) read from the light requirement constructor args."""
    res = {}
    joined = list(code)
    for i, line in enumerate(joined):
        m = re.search(r'Method [\w/$]*(Max|Min)LightLevelGrowthRequirement\."<init>":\(I\)V', line)
        if not m:
            continue
        val = None
        for back in range(i - 1, max(-1, i - 6), -1):
            mm = re.search(r'(?:bipush|sipush)\s+(-?\d+)', joined[back])
            if mm:
                val = int(mm.group(1)); break
            mm = re.search(r'\biconst_(\d)\b', joined[back])
            if mm:
                val = int(mm.group(1)); break
        res[m.group(1).lower()] = val
    return res.get('max'), res.get('min')


def tier_of(field, clsname):
    """getTier() reading an instance field means the value is a constructor
    argument, which this extractor does not walk. Fall back, but say so."""
    t = resolve_int(clsname, 'getTier')
    if t is None:
        guessed_tier.append(field)
        return 1
    return t


# crops whose language key could not be read, so the name below is this
# script's own construction rather than the mod's string - see the report
guessed_name = []


def internal_of(field, clsname):
    """The internalId the constructor hands to CropCard.

    Usually the field name with a lower first letter, but not always: the
    field KnightmetalBerry holds a crop built by CropOreBerry, whose
    constructor appends "OreBerry" to the material it is given, making the
    real id knightmetalOreBerry. So a candidate only stands if the language
    file has a key for it - the field name alone is not evidence.
    """
    cand = field[0].lower() + field[1:]
    if f'cropsnh_crops.{cand}' in lang:
        return cand
    simple = clsname.rsplit('.', 1)[-1]
    own = jvparse.strings(classes[clsname].code(simple))
    # whatever the parent constructors append to the name they are handed
    suffixes = [''] + [s for k in chain(clsname)[1:]
                       for s in jvparse.strings(k.code(k.name.rsplit('.', 1)[-1]))]
    for s in own:
        for suffix in suffixes:
            if f'cropsnh_crops.{s}{suffix}' in lang:
                return s + suffix
    return cand


def name_key(field, clsname):
    """The key the game itself renders the crop through.

    CropCard.getUnlocalizedName() returns "cropsnh_crops." + internalId, but
    29 crops override it with a key borrowed from whichever mod owns the
    plant - Wheat answers item.wheat.name, Belladonna answers
    tile.witchery:belladonna.name. Those keys are absent from CropsNH's own
    en_US.lang, which is why their English name is built from the field name
    instead; a translation for them has to be looked up in that other mod.
    """
    for k in chain(clsname):
        lit = jvparse.strings(k.code('getUnlocalizedName'))
        if not lit:
            continue
        # the base implementation builds the key, so its literal is the prefix
        if lit[0] != 'cropsnh_crops.':
            return lit[0]
        break
    return 'cropsnh_crops.' + internal_of(field, clsname)


crops = {}
for field, clsname in sorted(field_to_class.items()):
    if field in ('Weed', 'Migrator'):
        continue
    code = ctor_code(clsname)
    key = name_key(field, clsname)
    internal = key[len('cropsnh_crops.'):] if key.startswith('cropsnh_crops.') else key
    display = L(key)
    if display is None:
        guessed_name.append(field)
    subsoil = jvparse.fieldrefs(code, 'CropsNHSubSoilTypes')
    # addLikedBiomes() does addAll on a set, so the class chain and the loader
    # site both contribute rather than one overriding the other
    biomes = set(jvparse.fieldrefs(code, 'BiomeDictionary$Type')) | set(loader_biomes.get(field, []))
    for line in code:
        m = re.search(r'// String (\w+)$', line)
    # addSubSoilRequirement(String) - rare variant
    maxl, minl = light_reqs(code)
    crops[field] = {
        'id': field,
        'internal': internal,
        # the key a translation has to be looked up under, kept so langs.py
        # can resolve it in whichever mod's language file actually owns it
        'nameKey': key,
        'name': display or re.sub(r'(?<!^)(?=[A-Z])', ' ', field),
        'cls': clsname,
        'tier': tier_of(field, clsname),
        'soil': resolve_soil(clsname),
        'subsoil': sorted(set(subsoil)),
        'biomes': sorted(biomes),
        'maxLight': maxl,
        'minLight': minl,
        'growth': resolve_int(clsname, 'getGrowthDuration'),
        # An ordinary item registered as a stand-in for the seed. Every call
        # sits in a constructor, so the chain ctor_code() already walks is the
        # whole search: the eight bonsai inherit theirs from CropBonsai.
        'altSeed': any('addAlternateSeed:' in line for line in code),
        'pools': [],
        'flavour': L(f'cropsnh_crops.{internal}.flavour'),
    }

# ---------------------------------------------------------------- MutationLoader
ml = classes['com.gtnewhorizon.cropsnh.loaders.MutationLoader']
ml_code = []
for sig, lines in ml.methods.items():
    ml_code.extend(lines)

mutations = []
stack = []          # queue of CropsNHCrops.* arguments
strbuf = []
i = 0
while i < len(ml_code):
    line = ml_code[i]
    m = re.search(r'getstatic\s+#\d+\s+// Field [\w/$]*CropsNHCrops\.([\w$]+):', line)
    if m:
        stack.append(m.group(1)); i += 1; continue
    m = re.search(r'ldc\w*\s+#\d+\s+// String (.+)$', line)
    if m:
        strbuf.append(m.group(1)); i += 1; continue
    # pool registration: register(ICropCard, String[])
    if 'MutationRegistry.register:(Lcom/gtnewhorizon/cropsnh/api/ICropCard;[Ljava/lang/String;)V' in line:
        if stack:
            crop = stack.pop()
            if crop in crops:
                crops[crop]['pools'] = strbuf[:]
        strbuf = []; i += 1; continue
    # mutation constructor
    m = re.search(r'Method [\w/$]*CropMutation\."<init>":\((Lcom/gtnewhorizon/cropsnh/api/ICropCard;)+\)V', line)
    if m:
        n = line.count('Lcom/gtnewhorizon/cropsnh/api/ICropCard;')
        args = stack[-n:] if n <= len(stack) else stack[:]
        del stack[len(stack) - len(args):]
        mutations.append({'out': args[0], 'parents': args[1:], 'req': [], 'machineOnly': False})
        strbuf = []; i += 1; continue
    if 'CropMutation.addSubSoilRequirement:(Ljava/lang/String;)' in line:
        if mutations and strbuf:
            mutations[-1]['req'].append(strbuf[-1])
        strbuf = []; i += 1; continue
    if 'CropMutation.machineOnly:()' in line:
        if mutations:
            mutations[-1]['machineOnly'] = True
        i += 1; continue
    if 'CropMutation.removeExistingSubSoilRequirements' in line:
        if mutations:
            mutations[-1]['noInheritedSubSoil'] = True
        i += 1; continue
    if 'CropMutation.register:()V' in line:
        stack = []; strbuf = []; i += 1; continue
    i += 1

# ---------------------------------------------------------------- SubSoilRequirementLoader
ssl = classes.get('com.gtnewhorizon.cropsnh.loaders.SubSoilRequirementLoader')
subsoil_info = {}
if ssl:
    code = []
    for sig, lines in ssl.methods.items():
        code.extend(lines)
    cur = None
    str_arr_start = None          # index of the last `anewarray java/lang/String`
    for idx, line in enumerate(code):
        m = re.search(r'// Field [\w/$]*CropsNHSubSoilTypes\.([\w$]+):', line)
        if m:
            cur = m.group(1)
            subsoil_info.setdefault(cur, {'oredict': [], 'materials': [], 'modBlocks': []})
            continue
        if cur is None:
            continue
        if 'anewarray' in line and 'class java/lang/String' in line:
            str_arr_start = idx
            continue
        m = re.search(r'// Field [\w/$]*Materials\.([\w$]+):', line)
        if m:
            subsoil_info[cur]['materials'].append(m.group(1))
            continue
        # addOreDict(String...) - strings from the most recent String[] array
        if 'SubSoilRequirement.addOreDict:([Ljava/lang/String;)' in line and str_arr_start is not None:
            subsoil_info[cur]['oredict'] += jvparse.strings(code[str_arr_start:idx])
            str_arr_start = None
            continue
        # addBlockAndOreDict() with no args -> block<Name> / ore<Name> ore dict entries
        if 'SubSoilRequirement.addBlockAndOreDict:()' in line:
            cap = cur[0].upper() + cur[1:]
            subsoil_info[cur]['oredict'] += [f'block{cap}', f'ore{cap}']
            continue
        if 'SubSoilRequirement.addBlockAndOreDict:([Ljava/lang/String;)' in line and str_arr_start is not None:
            for s in jvparse.strings(code[str_arr_start:idx]):
                cap = s[0].upper() + s[1:]
                subsoil_info[cur]['oredict'] += [f'block{cap}', f'ore{cap}']
            str_arr_start = None
            continue
        # ModUtils.getBlock("name") -> a block from another mod
        m = re.search(r'// String (.+)$', line)
        if m and idx + 1 < len(code) and 'ModUtils.getBlock' in code[idx + 1]:
            subsoil_info[cur]['modBlocks'].append(m.group(1))

    for v in subsoil_info.values():
        for k in v:
            v[k] = sorted(set(v[k]))

# descriptions from the language file
subsoil_desc = {}
for k, v in lang.items():
    if k.startswith('cropsnh_growthReq.subSoil.'):
        subsoil_desc[k.split('.')[-1]] = v

pool_names = {k.split('.', 1)[1]: v for k, v in lang.items() if k.startswith('cropsnh_mutationPool.')}

# ---------------------------------------------------------------- pools -> members
pool_members = {}
for c in crops.values():
    for p in c['pools']:
        pool_members.setdefault(p, []).append(c['id'])
# MutationRegistry.pruneMutationPools() drops pools with fewer than 2 members
pool_members = {p: sorted(v) for p, v in pool_members.items() if len(v) >= 2}
for c in crops.values():
    c['pools'] = [p for p in c['pools'] if p in pool_members]

# ---------------------------------------------------------------- soils (top block)
# Some lists are unions of other lists (CompoundSoilList). We rebuild them from the
# static initialiser bytecode rather than guessing what e.g. "netherMushroom" means.
soil_parts = {}
_st = classes.get('com.gtnewhorizon.cropsnh.api.CropsNHSoilTypes')
if _st:
    st_lines = []
    for sig, lines in _st.methods.items():
        st_lines.extend(lines)
    buf, pending = [], []
    for line in st_lines:
        m = re.search(r'getstatic\s+#\d+\s+// Field ([\w$]+):Lcom/gtnewhorizon/cropsnh/api/ISoilList;', line)
        if m:
            buf.append(m.group(1)); continue
        if 'CompoundSoilList."<init>"' in line:
            pending, buf = buf[:], []
            continue
        m = re.search(r'putstatic\s+#\d+\s+// Field ([\w$]+):Lcom/gtnewhorizon/cropsnh/api/ISoilList;', line)
        if m:
            if pending:
                soil_parts[m.group(1)] = pending
                pending = []
            buf = []


def flatten(key, seen=None):
    seen = set() if seen is None else seen
    if key in seen:
        return []
    seen.add(key)
    if key not in soil_parts:
        return [key]
    out = []
    for p in soil_parts[key]:
        for f in flatten(p, seen):
            if f not in out:
                out.append(f)
    return out


# BASE lists only; unions are assembled from these at render time. The labels
# are this page's own wording rather than anything the mod says, so they live
# in tools/i18n/*.json under soil.gloss.* and soil.short.* and build.py puts
# them back - that is what lets them be translated along with the rest.
soil_base = [
    'brick', 'dirtGrass', 'end', 'farmland', 'gravel', 'graveyard', 'mycelium',
    'netherrack', 'oilSands', 'sand', 'slimy', 'soulsand', 'stone', 'thaumLogs',
]
# sorted, because Python randomises string hashing per process and an unsorted
# set here would make every rebuild produce a byte-different index.html
soil_expand = {k: flatten(k) for k in sorted(set(soil_base + list(soil_parts)))}

# the mod's own display names for the biome tags, so the page reads like NEI
biome_names = {t: L(f'cropsnh_tooltip.biomeTag.{t}', t.capitalize())
               for t in sorted({b for c in crops.values() for b in c['biomes']})}

out = {
    'crops': crops,
    'mutations': mutations,
    'subsoil': subsoil_info,
    'subsoilDesc': subsoil_desc,
    'poolNames': pool_names,
    'poolMembers': pool_members,
    'soilBase': soil_base,
    'soilExpand': soil_expand,
    'biomeNames': biome_names,
}
OUT = os.path.join(HERE, os.pardir, 'data', 'crops.json')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, ensure_ascii=False)

print(f'crops             {len(crops)}')
print(f'recipes           {len(mutations)}')
print(f'mutation pools    {len(pool_members)}')
print(f'sub-soil types    {len(subsoil_info)}')
print(f'recipe-only crops {sum(1 for c in crops.values() if not c["pools"])}')
borrowed = sum(1 for c in crops.values() if not c['nameKey'].startswith('cropsnh_crops.'))
print(f'names from other mods {borrowed}')
if guessed_tier:
    print(f'\nWARNING: no class states the tier as a constant, assumed 1 for '
          f'{len(guessed_tier)}: {", ".join(guessed_tier)}')
    print('         read the constructor argument in the loader and check by hand')
if guessed_name:
    print(f'\nnote: {len(guessed_name)} names are built from the field name, because their key '
          f'is not in CropsNH\'s own en_US.lang.\n      That is expected for crops borrowing '
          f'another mod\'s key - langs.py resolves those.')

print(f'\nwrote {os.path.relpath(OUT, os.path.join(HERE, os.pardir))}')
print('now run:  python tools/build.py')
