"""Minimal parser for the output of `javap -p -c -constants`."""
import re, os

RE_CLASS = re.compile(r'^(?:public |final |abstract |private |protected )*(?:class|interface|enum) ([\w.$]+)(?: extends ([\w.$]+))?(?: implements ([\w.$, ]+))?\s*\{')
RE_METHOD = re.compile(r'^  (?:[\w.$<>\[\], ]+?)?\b([\w<>$]+)\((.*?)\);\s*$')


class Klass:
    def __init__(self, name, sup):
        self.name = name
        self.sup = sup
        self.methods = {}          # signature -> list of bytecode lines

    def code(self, *method_names):
        """Concatenated bytecode of every method with one of the given names."""
        out = []
        for sig, lines in self.methods.items():
            base = sig.split('(')[0]
            if base in method_names:
                out.extend(lines)
        return out


def parse(paths):
    classes = {}
    cur = None
    cur_sig = None
    for path in paths:
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.rstrip('\n')
                m = RE_CLASS.match(line.strip())
                if m and not line.startswith('  '):
                    cur = Klass(m.group(1), m.group(2))
                    classes[cur.name] = cur
                    cur_sig = None
                    continue
                if cur is None:
                    continue
                # javap writes the class initialiser as `static {};`, which has no
                # argument list and so never matches RE_METHOD. Without this its
                # bytecode would be appended to whichever method came before it.
                if line.strip() == 'static {};':
                    cur_sig = '<clinit>()'
                    cur.methods[cur_sig] = []
                    continue
                m = RE_METHOD.match(line)
                if m and not line.strip().startswith(('Code:', '//')):
                    cur_sig = f'{m.group(1)}({m.group(2)})'
                    cur.methods[cur_sig] = []
                    continue
                if cur_sig is not None and line.startswith('     '):
                    cur.methods[cur_sig].append(line.strip())
    return classes


# --- small helpers for pulling values out of bytecode lines ---

def strings(lines):
    return re.findall(r'// String (.+)$', '\n'.join(lines), re.M)


def fieldrefs(lines, owner_suffix):
    """Field names matching `// Field com/.../<owner_suffix>.<NAME>:...`"""
    pat = re.compile(r'// Field [\w/$]*' + re.escape(owner_suffix) + r'\.([\w$]+):')
    return pat.findall('\n'.join(lines))


def calls(lines, needle):
    return [l for l in lines if needle in l]
