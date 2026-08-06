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
    .replace(/&#9670;/g, "*").replace(/&#8203;/g, "").replace(/&nbsp;/g, " ")
    .replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim());
};

/* A set with enough in it that every view has something to say. */
const seed = ["Wheat", "Potato", "Carrot", "Dandelion", "Poppy", "BrownMushroom",
              "RedMushroom", "Barley", "Cactus", "SugarCane"].filter(id => api.C[id]);
api.setOwned(seed);

for (const v of ["ready", "near", "pool", "path", "biome", "tips", "about"]) {
  api.setView(v);
  api.render();
  dump(`view: ${v}`, view.innerHTML);
}

/* The pool view again with a pair loaded, which is the odds table itself. */
const pair = api.bestPairs(1)[0];
if (pair) {
  api.setPair(pair.a, pair.b);
  api.setView("pool");
  api.render();
  dump(`view: pool (${pair.a} + ${pair.b})`, view.innerHTML);
}

/* Every drawer kind, since each has its own strings. */
const someCrop = Object.keys(api.C).sort()[0];
api.showCrop(someCrop);
dump(`drawer: crop ${someCrop}`, drawer.innerHTML);

const someBiome = Object.keys(api.BIOMES).sort()[0];
if (someBiome) { api.showBiome(someBiome); dump(`drawer: biome ${someBiome}`, drawer.innerHTML); }

fs.writeFileSync(outPath, out.join("\n") + "\n", "utf8");
console.log(`${pagePath} -> ${outPath}  (${out.join("").length} chars)`);
