# Regenerating the data

`index.html` in the repository root is **generated**. Do not edit it by hand, your changes will be
overwritten by the next build. Edit `page.src.html` instead.

## Requirements

Python 3 and a **JDK**. A JRE is not enough, `javap` only ships with the JDK.

## Steps

```
python tools/dump.py path/to/cropsnh-X.Y.Z.jar
python tools/extract.py
python tools/langs.py path/to/.minecraft path/to/launcher/assets
python tools/build.py
```

| Script | What it does |
| --- | --- |
| `dump.py` | unpacks the jar and disassembles the classes the extractor needs |
| `extract.py` | parses the disassembly into `data/crops.json` |
| `langs.py` | reads the pack's translations into `data/lang.<code>.json` |
| `build.py` | inlines that JSON into `page.src.html` and writes one page per language |

`dump.py` looks for `javap` on `PATH`, then `JAVA_HOME`, then the usual JDK install locations
including the one Prism Launcher downloads. The unpacked jar and the raw disassembly land in
`tools/_jar/` and `tools/dump_*.txt`, both git-ignored.

`langs.py` is the only script that needs the game installed rather than just the jar, because the
jar carries English alone. Everything else is in the pack: GTNH translates through
`config/txloader/load/<Mod>[modid]/lang/`, and vanilla's own translations are not in the client jar
either - they live in the launcher's content-addressed asset store, which is the second argument.
Both are needed because 29 crops borrow their display name from another mod, `Wheat` answering
`item.wheat.name` and `Belladonna` answering `tile.witchery:belladonna.name`.

Its output is committed, so a normal `build.py` run needs none of that. Re-run it only when the
pack updates. A language whose crop names are less than 90% translated is skipped outright: half a
set would leave the page mixing two languages, and the prose in `i18n` names crops in plain text.

The build is reproducible: the same jar always produces a byte-identical `index.html`, so a diff on
that file means the data genuinely changed.

## Checking a page

```
node tools/checkpage.js index.html pl/index.html ja/index.html zh/index.html
node tools/dumpviews.js index.html before.txt
```

Both take a **built** page, not `page.src.html`, and need only Node. `checkpage.js` exits non-zero
on the first failure, so it can gate a commit; `dumpviews.js` writes out what every view says, for
diffing one build against the next.

They cover what `build.py` cannot: the build checks that every key resolves and that none is
orphaned, but it never runs the page, so a handler wired to a button that no longer exists passes
the build and breaks in the browser.

## Changing the favicon

Edit `favicon.svg` and run `build.py`. It is base64-encoded into the page head as a data URI, so
`index.html` stays a single self-contained file with no external requests.

## Changing the page

Edit `page.src.html`, then run `build.py`. That file holds the whole page - markup, styles, script
and the tips text - with a single `__DATA__` placeholder where the JSON gets inlined.
