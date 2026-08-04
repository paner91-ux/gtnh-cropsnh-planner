# CropsNH Breeding Planner

A single-page planner for crop breeding in **GregTech: New Horizons**.

Tick off the seeds you own and it tells you what you can breed next, the exact odds of each
outcome, and which two blocks have to be under the crop stick for the result to be planted at all.

**Live version:** https://paner91-ux.github.io/cropsnh-planner/

No install, no account, nothing sent anywhere. Your ticked seeds are stored in your own browser.

---

## This is for the new crop system in GTNH 2.9

**CropsNH replaced the old IC2 crops in 2.9.** If you are still on 2.8 or earlier, none of this
applies to you: different crops, different breeding rules, different everything. Check whether your
crop sticks come from CropsNH before you start planning against this.

Breeding works genuinely differently now, so old habits and old guides will mislead you. The two
that catch people out most:

- Crossing no longer needs two *different* plants to improve stats. Two of the same crop next to a
  double crop stick works, and it behaves differently from two different crops.
- Which blocks sit under the stick decides what is even allowed to appear there, not just whether
  the result grows afterwards.

Both are covered in the **Tips & tricks** tab, with the reasoning behind them.

If you are upgrading a world, the mod converts existing IC2, Crops++ and GT5u crops over
automatically, so you do not need to replant anything by hand.

---

## What it does

**Ready now** - recipes where you already hold every parent.

**One parent short** - recipes you are a single crop away from, so you know what to hunt for next.

**Pool roulette** - pick two parents and get the full probability breakdown: how often you get a
copy of a parent, how often a real mutation, and exactly which crops can come out with what chance.
Picking the same crop twice is supported, and it behaves differently from two different crops.
With nothing selected it ranks the best pairs from your own seeds by the chance of something new.

**Route to a goal** - the shortest chain of recipes from what you own to any crop you want.

**Tips & tricks** - 38 mechanics written in plain language, each with a `why` box explaining where
in the mod's code it comes from.

Every crop links to a panel with its tier, growth time, mutation pools, the recipes that produce
it, and everything it is a parent for.

---

## Where the data comes from

Nothing here was collected by playing or copied from a wiki. The recipes, mutation pools, soils,
sub-soils and light requirements are all read straight out of the compiled mod:

| Source class | What it gives |
| --- | --- |
| `MutationLoader` | every deterministic recipe and every crop's pool membership |
| `CropLoader` + the crop classes | tier, growth time, soil, sub-soil, light requirements |
| `SubSoilRequirementLoader` | which blocks and ore dictionary entries count as each sub-soil |
| `CropsNHSoilTypes` | how compound soil lists are built out of simpler ones |
| `en_US.lang` | display names, exactly as they appear in NEI |

Built against **CropsNH 2.0.101**, as shipped in the GTNH 2.9 daily builds (nightly 659).
In that version: 179 crops, 172 recipes, 66 pools.

Nothing else in the pack registers crops with CropsNH, so the list is complete rather than a
selection. If a future version adds or changes crops, regenerate the data with the steps below
instead of editing anything by hand.

Two things worth knowing about the data:

- **21 crops belong to no pool.** Those can only ever come from their exact recipe.
- **Some crops have no recipe.** Barley for one - you find those in the world, you cannot breed them.

---

## Regenerating for a newer CropsNH

You need Python 3 and a **JDK** (a JRE will not do, `javap` only ships with the JDK).

```
python tools/dump.py path/to/cropsnh-X.Y.Z.jar
python tools/extract.py
python tools/build.py
```

`dump.py` unpacks the jar and disassembles the classes the extractor needs. `extract.py` parses
that into `data/crops.json`. `build.py` inlines the JSON into `tools/page.src.html` and writes
`index.html`. The unpacked jar and the raw disassembly stay out of git.

`dump.py` looks for `javap` on `PATH`, then `JAVA_HOME`, then the usual JDK install locations
including the one Prism Launcher downloads.

To change the page itself, edit `tools/page.src.html` and re-run `build.py`. Do not edit
`index.html` directly, it is generated.

---

## Notes

The page is one self-contained HTML file with no external requests, so it works offline. Download
`index.html` and open it locally if you would rather not use the hosted copy - it behaves
identically, except that the hosted copy cannot save files because browsers block downloads from
embedded frames.

Ticked seeds live in `localStorage`, which is per-origin. The hosted page and a local copy keep
separate lists. Use **Backup** in the sidebar to move a list between them.

---

## Credits

CropsNH is part of [GregTech: New Horizons](https://github.com/GTNewHorizons). This is an
unofficial fan-made tool and is not affiliated with or endorsed by the GTNH team. Crop names and
game data belong to that project; the tool itself is MIT licensed, see [LICENSE](LICENSE).
