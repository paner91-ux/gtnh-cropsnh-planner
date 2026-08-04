"""Unpack a CropsNH jar and disassemble the classes the extractor needs.

Usage:  python tools/dump.py path/to/cropsnh-2.0.101.jar

Requires a JDK on PATH (javap). Writes dump_*.txt next to this script and
unpacks the jar into tools/_jar/ so the extractor can read the language file.
"""
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
JAR_DIR = os.path.join(HERE, '_jar')

# class -> output file; each entry is disassembled in one javap call
TARGETS = {
    'dump_croploader.txt':  ['com/gtnewhorizon/cropsnh/loaders/CropLoader.class'],
    'dump_mutationloader.txt': ['com/gtnewhorizon/cropsnh/loaders/MutationLoader.class'],
    'dump_subsoil.txt':     ['com/gtnewhorizon/cropsnh/loaders/SubSoilRequirementLoader.class'],
    'dump_soil.txt':        ['com/gtnewhorizon/cropsnh/loaders/SoilLoader.class'],
    'dump_soiltypes.txt':   ['com/gtnewhorizon/cropsnh/api/CropsNHSoilTypes.class'],
}


def find_javap():
    """javap ships with a JDK but not with a JRE, so it is often not on PATH."""
    import glob
    exe = 'javap.exe' if os.name == 'nt' else 'javap'

    found = shutil.which(exe)
    if found:
        return found

    java_home = os.environ.get('JAVA_HOME')
    if java_home and os.path.exists(os.path.join(java_home, 'bin', exe)):
        return os.path.join(java_home, 'bin', exe)

    # sibling of a java on PATH
    java = shutil.which('java.exe' if os.name == 'nt' else 'java')
    if java:
        sibling = os.path.join(os.path.dirname(java), exe)
        if os.path.exists(sibling):
            return sibling

    patterns = [
        r'C:\Program Files\Java\*\bin\javap.exe',
        r'C:\Program Files\Eclipse Adoptium\*\bin\javap.exe',
        r'C:\Program Files\Microsoft\jdk*\bin\javap.exe',
        r'C:\Program Files\Zulu\*\bin\javap.exe',
        os.path.expanduser(r'~\AppData\Roaming\PrismLauncher\java\*\bin\javap.exe'),
        '/usr/lib/jvm/*/bin/javap',
        '/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/javap',
    ]
    for pattern in patterns:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]

    sys.exit('javap not found. Install a JDK (a JRE is not enough) or set JAVA_HOME.')


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    jar = sys.argv[1]
    if not os.path.isfile(jar):
        sys.exit(f'no such file: {jar}')

    javap = find_javap()
    if os.path.isdir(JAR_DIR):
        shutil.rmtree(JAR_DIR)
    os.makedirs(JAR_DIR)
    with zipfile.ZipFile(jar) as z:
        z.extractall(JAR_DIR)
    print(f'unpacked {os.path.basename(jar)}')

    crops = []
    for root, _dirs, files in os.walk(os.path.join(JAR_DIR, 'com/gtnewhorizon/cropsnh/crops')):
        crops += [os.path.join(root, f) for f in files if f.endswith('.class')]
    jobs = dict(TARGETS)
    jobs['dump_crops.txt'] = [os.path.relpath(p, JAR_DIR) for p in crops]

    for out, classes in jobs.items():
        missing = [c for c in classes if not os.path.exists(os.path.join(JAR_DIR, c))]
        if missing:
            sys.exit(f'class missing from the jar: {missing[0]}')
        result = subprocess.run(
            [javap, '-p', '-c', '-constants'] + classes,
            cwd=JAR_DIR, capture_output=True, text=True, encoding='utf-8', errors='replace')
        with open(os.path.join(HERE, out), 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        print(f'  {out:26s} {len(classes):4d} class(es)')

    print('\nnow run:  python tools/extract.py')


if __name__ == '__main__':
    main()
