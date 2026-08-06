# GTNH Crop Breeding Planner

A single-page planner for crop breeding in **GregTech: New Horizons**.

Tick off the seeds you own and it tells you what you can breed next, the exact odds of each
outcome, which two blocks have to be under the crop stick for the result to be planted at all, and
which biome to build the farm in.

**Live version:**
[English](https://paner91-ux.github.io/gtnh-cropsnh-planner/)
&nbsp;·&nbsp; [日本語](https://paner91-ux.github.io/gtnh-cropsnh-planner/ja/)
&nbsp;·&nbsp; [Polski](https://paner91-ux.github.io/gtnh-cropsnh-planner/pl/)
&nbsp;·&nbsp; [简体中文](https://paner91-ux.github.io/gtnh-cropsnh-planner/zh/)

Same page in every language, and the picker at the top right keeps your place when you switch.

There is no Russian version and there will not be one. If you would like to help Ukraine instead,
[United24](https://u24.gov.ua/) is the Ukrainian government's fundraising platform.

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

**Biomes** - which biome to build in. A crop that matches two of a biome's tags gets +28 Nutrient
Score, more than half the ceiling. In game you can read a biome's tags with Nature's Compass and a
crop's tags in NEI, but nothing joins the two, so working out where a particular crop does best
means checking biomes one at a time. This does the join: from a crop's tags to the biomes that
carry them, and from a biome to the crops worth growing there.

**Tips & tricks** - a seven step walkthrough plus 43 mechanics in plain language, each with a `why`
box naming the method in the mod's code it was read from.

**About this page** - what the tool can do, where its numbers come from, and what it stores. Kept
separate from Tips & tricks on purpose: that tab promises a source in the mod for every line, and
notes about this page have none.

Every crop links to a panel with its tier, growth time, mutation pools, the recipes that produce
it, and everything it is a parent for.

The page is in English, Japanese, Polish and Simplified Chinese. The address bar follows what you
are looking at, so a link opens on the same tab, the same pair and the same open panel, and
switching language keeps your place.

Crop names follow the game rather than the page. GTNH translates through its own config directory
rather than through the mod jars, so the Chinese and Japanese versions print the names their
clients show in NEI, all 179 of them. Polish keeps English names because the pack has no Polish
ones for CropsNH, which is what a Polish client shows too.

Anything the pack leaves untranslated stays English here for the same reason, so the page keeps
matching the game rather than getting ahead of it. That covers the biome tags on the Japanese
version, and biome names everywhere: in Minecraft 1.7.10 a biome name is a plain string in code
with no translation key at all, so the game shows "Alps" and "Bayou" whatever language it is set
to, and so does this.

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
| `en_US.lang` | display names, exactly as they appear in NEI, and the biome tag names |
| the pack's `lang` configs | the same names in the other languages, read the same way |

Built against **CropsNH 2.0.101**, as shipped in the GTNH 2.9 daily builds (nightly 659).
In that version: 179 crops, 172 recipes, 66 pools.

The **Biomes** tab is the one exception. Biome tags are Forge's, and each biome is registered by
whichever mod added it, so `tools/biomes.py` reads them out of Minecraft, Biomes O' Plenty, Twilight
Forest, RWG and Thaumcraft - every mod in this pack that registers any. 159 biomes. Same method,
different jars: a mod that adds biomes without registering tags will not appear, and the script says
so rather than quietly dropping them.

Nothing else in the pack registers crops with CropsNH, so the list is complete rather than a
selection. When a new CropsNH version lands the data is regenerated from the new jar rather than
edited by hand - see [tools/](tools/) if you want to do that yourself.

Three things worth knowing about the data:

- **21 crops belong to no pool.** Those can only ever come from their exact recipe.
- **7 crops have no recipe at all**, among them Wheat, Potato and Carrot. Those are starting points: you find them in the world, you cannot breed your way to them.
- **17 crops cannot reach the full biome bonus anywhere in this pack.** No biome carries two of their tags, so +14 is the most a location is ever worth to them.

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
