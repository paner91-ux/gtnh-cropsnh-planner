/* Render every view of a built page against a stubbed DOM and write out what
   it says, so two runs can be diffed.

     node tools/dumpviews.js index.html before.txt

   This is the honest test for a text change: a diff of page.src.html shows
   every reworded template literal, while a diff of two dumps shows only what
   a reader would actually notice. Markup is stripped for the same reason -
   swapping a quote for a backtick changes the source and nothing else.

   Two things the stub has to get right, both learned the hard way: window
   needs addEventListener, because the page listens for hashchange, and the
   script's top-level let/const are not globals, so the only way to reach
   them is to append an assignment to globalThis (see `expose` below).      */
const fs = require("fs");
const vm = require("vm");

const [, , pagePath, outPath] = process.argv;
if (!pagePath || !outPath) {
  console.error("usage: node tools/dumpviews.js <page.html> <out.txt>");
  process.exit(2);
}
const html = fs.readFileSync(pagePath, "utf8");
const code = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));

/* An element that answers anything, so the page's own wiring does not throw. */
function el(id) {
  return {
    id, innerHTML: "", textContent: "", value: "", hidden: false, open: false,
    dataset: {}, style: {}, checked: false, files: [], hash: "",
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    addEventListener() {}, removeEventListener() {}, setAttribute() {},
    removeAttribute() {}, getAttribute: () => null, focus() {}, blur() {},
    click() {}, scrollIntoView() {}, appendChild() {}, remove() {},
    insertAdjacentHTML() {}, closest: () => null, querySelector: () => null,
    querySelectorAll: () => [], select() {}, setSelectionRange() {},
    getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 }),
  };
}

const nodes = new Map();
const byId = id => {
  if (!nodes.has(id)) nodes.set(id, el(id));
  return nodes.get(id);
};

const sandbox = {
  console,
  document: {
    getElementById: byId,
    querySelector: () => el(),
    querySelectorAll: () => [],
    createElement: () => el(),
    addEventListener() {},
    body: el("body"),
    documentElement: el("html"),
  },
  window: {
    addEventListener() {}, removeEventListener() {},
    matchMedia: () => ({ matches: false, addEventListener() {} }),
  },
  location: { hash: "", href: "https://example.invalid/", search: "" },
  history: { replaceState() {}, pushState() {} },
  navigator: { clipboard: { writeText: () => Promise.resolve() }, userAgent: "node" },
  localStorage: null,          // exercises the no-storage path
  setTimeout, clearTimeout, URLSearchParams, Intl, Date, Math, JSON,
  requestAnimationFrame: fn => fn(),
  alert() {}, Blob: class {}, FileReader: class {},
};
sandbox.globalThis = sandbox;
sandbox.self = sandbox;
sandbox.top = sandbox;

const expose = `
globalThis.__api = {
  setView: v => { view = v; },
  render, renderTips, renderAbout, renderBiomes, oddsFor, bestPairs, planFor,
  showCrop, showBiome, showTag, paintDrawer, drawerStack,
  setOwned: ids => { owned = new Set(ids); },
  setPair: (a, b) => { pairA = a; pairB = b; },
  setTarget: t => { target = t; },
  sortPool: typeof togglePoolSort === "function" ? togglePoolSort : null,
  C, MUT, POOLM, BIOMES,
};`;

vm.createContext(sandbox);
vm.runInContext(code + expose, sandbox, { filename: pagePath });

const api = sandbox.__api;
const view = byId("view");
const drawer = byId("drawer");
const out = [];
const dump = (label, text) => {
  out.push(`\n${"=".repeat(72)}\n== ${label}\n${"=".repeat(72)}\n`);
  // tags out, entities in, so the diff is what a reader sees rather than markup
  out.push(String(text)
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&#9670;/g, "*").replace(/&#9679;/g, "o").replace(/&#10005;/g, "x")
    .replace(/&#8203;/g, "").replace(/&nbsp;/g, " ")
    .replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim());
};

/* A set with enough in it that every view has something to say. */
const seed = ["Wheat", "Potato", "Carrot", "Dandelion", "Poppy", "BrownMushroom",
              "RedMushroom", "Barley", "Cactus", "SugarCane"].filter(id => api.C[id]);
api.setOwned(seed);

for (const v of ["ready", "near", "pool", "path", "biome", "guide", "tips", "about"]) {
  api.setView(v);
  api.render();
  dump(`view: ${v}`, view.innerHTML);
}

/* The pool view with a pair loaded. This used to claim it was "the odds table
   itself" and it was not: bestPairs()[0] is a pair with a deterministic recipe,
   which renders cards instead. The table went untested for as long as that
   comment was there, and a diff of two runs came back empty either way, which
   reads exactly like proof that nothing changed.                             */
const pair = api.bestPairs(1)[0];
if (pair) {
  api.setPair(pair.a, pair.b);
  api.setView("pool");
  api.render();
  dump(`view: pool, recipe pair (${pair.a} + ${pair.b})`, view.innerHTML);
}

/* So find a pair by its data rather than its markup - testing the rendered
   html for class="odds" passes on a pair whose table has no rows at all.
   First pair wins ties, so the choice is stable between two runs.            */
let odds = null, oddsRows = 0;
for (const a of seed) {
  for (const b of Object.keys(api.C)) {
    let o; try { o = api.oddsFor(a, b); } catch (e) { continue; }
    const n = o && o.rows ? o.rows.length : 0;
    if (n > oddsRows) { oddsRows = n; odds = [a, b]; }
  }
}
if (odds) {
  api.setPair(odds[0], odds[1]);
  api.setView("pool");
  api.render();
  dump(`view: pool, odds table (${odds[0]} + ${odds[1]}, ${oddsRows} rows)`, view.innerHTML);

  /* Column sorting is what a reader sees, so it belongs here rather than in
     checkpage. Only the order of the result column is dumped: sorting cannot
     change anything else, and twelve copies of a 76 row table would bury every
     other section in the diff. Two clicks per key, the second reverses it.   */
  if (api.sortPool) {
    /* The view holds two tables with this class - the parent copies first, the
       pool draw after it - so take whichever has the most crops in it rather
       than the first one, which quietly yields a single name.                */
    const order = h => (h.match(/<table class="odds">[\s\S]*?<\/table>/g) || [])
      .map(t => (t.match(/data-crop="([^"]+)"/g) || []).map(s => s.slice(11, -1)))
      .reduce((best, ids) => ids.length > best.length ? ids : best, [])
      .join(" ");
    const orders = [];
    for (const key of ["result", "chance", "pool", "topBlock", "underBlock", "light"]) {
      for (const dir of ["ascending", "descending"]) {
        api.sortPool(key);
        api.render();
        orders.push(`${key} ${dir}:\n${order(view.innerHTML)}`);
      }
    }
    dump("view: pool, result order per sort column", orders.join("\n\n"));
    api.sortPool("chance");   // back to the default so later dumps are unaffected
    api.sortPool("chance");
  }
  api.setPair("", "");
}

/* The route view above ran with no goal set, so it only ever showed the goal
   picker. These two are the branches that actually say something: a goal that
   no recipe chain reaches, and a goal with no recipe at all.                 */
const sorted = Object.keys(api.C).sort();
const blocked = sorted.find(id =>
  !seed.includes(id) && !api.planFor(id) && api.MUT.some(m => m.out === id));
if (blocked) {
  api.setTarget(blocked);
  api.setView("path");
  api.render();
  dump(`view: path, goal out of reach (${blocked})`, view.innerHTML);
}
const wild = sorted.find(id => !seed.includes(id) && !api.MUT.some(m => m.out === id));
if (wild) {
  api.setTarget(wild);
  api.setView("path");
  api.render();
  dump(`view: path, goal with no recipe (${wild})`, view.innerHTML);
}

/* Same branch once more for a crop that has no recipe but does sit in a pool,
   which is the only case that renders the pool hint under the goal. Every such
   crop is one of the five vanilla starters and so is in the seed set, and an
   owned goal short-circuits to "you already have it" - hand one back first.  */
const wildPooled = sorted.find(id =>
  !api.MUT.some(m => m.out === id) && (api.C[id].pools || []).length);
if (wildPooled) {
  api.setOwned(seed.filter(id => id !== wildPooled));
  api.setTarget(wildPooled);
  api.setView("path");
  api.render();
  dump(`view: path, goal with no recipe but in pools (${wildPooled})`, view.innerHTML);
  api.setOwned(seed);
}
api.setTarget("");

/* Every drawer kind, since each has its own strings. */
const someCrop = Object.keys(api.C).sort()[0];
api.showCrop(someCrop);
dump(`drawer: crop ${someCrop}`, drawer.innerHTML);

const someBiome = Object.keys(api.BIOMES).sort()[0];
if (someBiome) { api.showBiome(someBiome); dump(`drawer: biome ${someBiome}`, drawer.innerHTML); }

/* The rail is not one of the views, so nothing above would show a change to it.
   Its legend sits in the static markup rather than in a node, and only the rows
   carrying a marker are dumped - the other 150-odd rows are crop names, which a
   diff of data/crops.json already covers far better than this would.        */
dump("rail: legend", (html.match(/<p class="raillegend">[\s\S]*?<\/p>/g) || []).join("\n"));
const marked = (byId("seedlist").innerHTML.match(/<div class="seed">[\s\S]*?<\/div>/g) || [])
  .filter(row => /class="mark (mach|none)"/.test(row));
dump(`rail: rows marked as no stick route (${marked.length})`, marked.join("\n"));

fs.writeFileSync(outPath, out.join("\n") + "\n", "utf8");
console.log(`${pagePath} -> ${outPath}  (${out.join("").length} chars)`);
