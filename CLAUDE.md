# Working on this repo

A single-page planner for crop breeding in GregTech: New Horizons, published with GitHub Pages at
https://paner91-ux.github.io/gtnh-cropsnh-planner/

## The one rule that matters

**`index.html` is generated. Never edit it by hand.** Every change to the page goes into
`tools/page.src.html`, then you run the build. Editing `index.html` directly means your work is
silently thrown away by the next rebuild.

```
python tools/build.py                       # page.src.html + data/crops.json -> index.html
python tools/dump.py path/to/cropsnh-X.Y.Z.jar   # only when the mod version changes
python tools/extract.py                     # only after dump.py, rewrites data/crops.json
```

## Text and languages

No English sentence belongs in `page.src.html`. Text lives in `tools/i18n/en.json` and the template
refers to it as `{{key}}`; the build writes one page per catalogue, English at the root and every
other language in its own directory. Nothing about translation reaches the built page - it is still
a static file with the strings already in it.

`en.json` is the source. Adding a string means adding it there first, and the build refuses to run
if a key is used but undefined, defined but unused, or if a translation drops a `${...}` that the
English string has. A missing translation falls back to English rather than showing its key.

The build is reproducible: the same jar always yields a byte-identical `index.html`. If a rebuild
produces a diff, the data genuinely changed. Anything that makes the output vary between runs
(unsorted sets, timestamps) is a bug - one already had to be fixed for exactly this reason.

## Where the data comes from

Recipes, pools, soils, sub-soils and light requirements are read out of the compiled mod with
`javap`, not copied from a wiki. `tools/README.md` describes the pipeline.

**Do not infer facts from field names.** Two claims on this page were wrong because of that: a soil
label invented from the identifier `netherMushroom` (it is really a union of four soil lists), and
"Barley has no recipe" (it has one, `Bamboo Shoot + Wheat`; it was merely unreachable from Tier 1 in
a test). Verify against the bytecode and cite the method. If something cannot be verified, say in
the text that it is practical advice rather than a fact from the code.

**A plausible-looking `cls` is not proof the right class was read.** All eight bonsai shipped with
`soil: farmland` when the mod says `dirtGrass`, because the loader constructs the crop first and its
arguments after it, so the last `new` before the field store was an `ItemStack`. Nothing failed - the
wrong class simply answered every question with a default. When crop data looks odd, check `cls`
first: it should always be a `com.gtnewhorizon.cropsnh` crop class. `extract.py` now warns when a
tier came from the fallback instead of the bytecode; treat that warning as work to do, not noise.

## Conventions

- The page and all repo files are **English**. The author is Polish; chat can be Polish, the product
  is not.
- **No em dashes.** Use a plain `-`. Same for en dashes and the U+2212 minus sign.
- Every crop name rendered anywhere goes through `cropLink()` / `parentLinks()` so it opens the
  detail panel and is coloured by whether the user holds it. Do not hand-roll a crop name.
- Colours: `--leaf` for owned and positive, `--ore` for missing and requirements, `--steel` for
  machine-only. Owned entries sort to the bottom of result lists.
- Tips in the Tips & tricks tab always pair a plain-language sentence with a `why` box naming the
  source in the mod. No tip without a source.

## Checking a change

There is no test runner. The page is verified by pulling the `<script>` out of `index.html` and
running it in Node against a stubbed DOM, then calling the render functions and checking the output.
Worth doing for anything touching odds, routing or the drawer.

Local notes that are not in git may exist in `CLAUDE.local.md` - read it if it is there.
