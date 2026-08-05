# GTNH Crop Breeding Planner

A single-page planner for crop breeding in **GregTech: New Horizons**.

Tick off the seeds you own and it tells you what you can breed next, the exact odds of each
outcome, and which two blocks have to be under the crop stick for the result to be planted at all.

**Live version:** https://paner91-ux.github.io/gtnh-cropsnh-planner/
&nbsp;·&nbsp; **Po polsku:** https://paner91-ux.github.io/gtnh-cropsnh-planner/pl/

No install, no account, nothing sent anywhere. Your ticked seeds are stored in your own browser.

Every feature is explained on the page itself, in
[**About this page**](https://paner91-ux.github.io/gtnh-cropsnh-planner/#v=about).

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

**Tips & tricks** - a seven step walkthrough plus 41 mechanics in plain language, each with a `why`
box naming the method in the mod's code it was read from.

**About this page** - what the tool can do, where its numbers come from, and what it stores. Kept
separate from Tips & tricks on purpose: that tab promises a source in the mod for every line, and
notes about this page have none.

Every crop links to a panel with its tier, growth time, mutation pools, the recipes that produce
it, and everything it is a parent for.

The page is in English and Polish. The address bar follows what you are looking at, so a link opens
on the same tab, the same pair and the same open panel, and switching language keeps your place.

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
selection. When a new CropsNH version lands the data is regenerated from the new jar rather than
edited by hand - see [tools/](tools/) if you want to do that yourself.

Two things worth knowing about the data:

- **21 crops belong to no pool.** Those can only ever come from their exact recipe.
- **7 crops have no recipe at all**, among them Wheat, Potato and Carrot. Those are starting points: you find them in the world, you cannot breed your way to them.

---

## Notes

The page is one self-contained HTML file with no external requests, so it works offline. Download
`index.html` and open it locally if you would rather not use the hosted copy - it behaves
identically, except that the hosted copy cannot save files because browsers block downloads from
embedded frames.

Ticked seeds live in `localStorage`, which is per-origin. The hosted page and a local copy keep
separate lists. Open **Manage list** in the sidebar to move a list between them.

---

## Credits

[CropsNH](https://github.com/GTNewHorizons/CropsNH) is by C0bra5 and the GTNH Team, built on
AgriCraft. GTNH modifications are LGPL-3.0-or-later, the original AgriCraft code is MIT.

This is an unofficial fan-made tool, not affiliated with or endorsed by the GTNH team.

**It contains no CropsNH code.** No Java sources, no class files, no jar, no textures. What it does
carry from the mod is game data read out of the compiled classes - recipes, pool memberships, tiers,
soils, light levels - plus the English display names, sub-soil descriptions, pool names and a
handful of flavour texts, taken from the mod's language file so the tool matches what you see in
NEI. All of that belongs to the CropsNH authors.

The tool itself, meaning the page and the extraction scripts, is MIT licensed. See [LICENSE](LICENSE).

If anything here oversteps, open an issue and it will be changed or removed.
