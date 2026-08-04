# Regenerating the data

`index.html` in the repository root is **generated**. Do not edit it by hand, your changes will be
overwritten by the next build. Edit `page.src.html` instead.

## Requirements

Python 3 and a **JDK**. A JRE is not enough, `javap` only ships with the JDK.

## Steps

```
python tools/dump.py path/to/cropsnh-X.Y.Z.jar
python tools/extract.py
python tools/build.py
```

| Script | What it does |
| --- | --- |
| `dump.py` | unpacks the jar and disassembles the classes the extractor needs |
| `extract.py` | parses the disassembly into `data/crops.json` |
| `build.py` | inlines that JSON into `page.src.html` and writes `index.html` |

`dump.py` looks for `javap` on `PATH`, then `JAVA_HOME`, then the usual JDK install locations
including the one Prism Launcher downloads. The unpacked jar and the raw disassembly land in
`tools/_jar/` and `tools/dump_*.txt`, both git-ignored.

The build is reproducible: the same jar always produces a byte-identical `index.html`, so a diff on
that file means the data genuinely changed.

## Changing the page

Edit `page.src.html`, then run `build.py`. That file holds the whole page - markup, styles, script
and the tips text - with a single `__DATA__` placeholder where the JSON gets inlined.
