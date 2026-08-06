/* Assertions about a built page, run against a stubbed DOM.

     node tools/checkpage.js index.html pl/index.html ja/index.html zh/index.html

   Exits non-zero on the first page that fails, so it can gate a commit. The
   point is the things build.py cannot see: it checks that every key resolves
   and that no string is orphaned, but it never runs the page, so a handler
   wired to a button that no longer exists would pass the build and break in
   the browser.

   Run it on every language, not just English. The markup is shared, but a
   catalogue can still break a page on its own - a translation that drops an
   interpolation only shows up once the template literal is evaluated.      */
const fs = require("fs");
const vm = require("vm");
const path = require("path");

const pages = process.argv.slice(2);
if (!pages.length) {
  console.error("usage: node tools/checkpage.js <page.html> [more.html ...]");
  process.exit(2);
}

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

/* Load one page and hand back its internals plus the stub nodes. */
function load(pagePath) {
  const html = fs.readFileSync(pagePath, "utf8");
  const code = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));
  const nodes = new Map();
  const byId = id => { if (!nodes.has(id)) nodes.set(id, el(id)); return nodes.get(id); };
  const hashes = [];

  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    document: {
      getElementById: byId, querySelector: () => el(), querySelectorAll: () => [],
      createElement: () => el(), addEventListener() {}, body: el("body"),
      documentElement: el("html"),
    },
    window: { addEventListener() {}, removeEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }) },
    location: { hash: "", href: "https://example.invalid/", search: "" },
    history: { replaceState(a, b, h) { hashes.push(h); }, pushState() {} },
    navigator: { clipboard: { writeText: () => Promise.resolve() }, userAgent: "node" },
    localStorage: null,
    setTimeout, clearTimeout, URLSearchParams, Intl, Date, Math, JSON,
    requestAnimationFrame: fn => fn(),
    alert() {}, Blob: class {}, FileReader: class {},
  };
  sandbox.globalThis = sandbox; sandbox.self = sandbox; sandbox.top = sandbox;

  /* Top-level let/const are not globals, so reach them explicitly. */
  const expose = `
  globalThis.__api = {
    getView: () => view, setView: v => { view = v; },
    getPair: () => [pairA, pairB], setPair: (a, b) => { pairA = a; pairB = b; },
    getRecent: () => recentPairs, getStack: () => drawerStack,
    setOwned: ids => { owned = new Set(ids); },
    render, oddsFor, showCrop, showPool, showTag, showBiome,
    C, MUT, POOLM, BIOMES,
  };`;

  vm.createContext(sandbox);
  vm.runInContext(code + expose, sandbox, { filename: pagePath });
  return { api: sandbox.__api, byId, nodes, hashes, html };
}

const VIEWS = ["ready", "near", "pool", "path", "biome", "tips", "about"];
let failed = 0;

for (const pagePath of pages) {
  const label = path.relative(process.cwd(), pagePath).replace(/\\/g, "/");
  const bad = [];
  const ok = (cond, msg) => { if (!cond) bad.push(msg); };

  const { api, byId, nodes, hashes, html } = load(pagePath);
  const view = byId("view"), drawer = byId("drawer");

  /* An untranslated key reaching the page is the one failure that looks fine
     in a screenshot until someone reads it. */
  ok(!html.includes("{{"), "the built file still contains a {{key}} placeholder");

  /* Every view renders, with a set that gives each of them something to say. */
  const seed = ["Wheat", "Potato", "Carrot", "Dandelion", "Poppy", "BrownMushroom",
                "RedMushroom", "Barley", "Cactus", "SugarCane"].filter(id => api.C[id]);
  api.setOwned(seed);
  for (const v of VIEWS) {
    api.setView(v);
    api.render();
    ok(view.innerHTML.length > 0, `view ${v} rendered nothing`);
    ok(!view.innerHTML.includes("{{"), `view ${v} left a {{key}} unreplaced`);
  }

  /* Each drawer kind has its own strings, so each gets opened. */
  const crop = Object.keys(api.C).sort()[0];
  api.showCrop(crop);
  ok(drawer.innerHTML.length > 0, "crop drawer rendered nothing");
  ok(!drawer.innerHTML.includes("{{"), "crop drawer left a {{key}} unreplaced");

  const pool = Object.keys(api.POOLM).sort()[0];
  if (pool) { api.showPool(pool); ok(!drawer.innerHTML.includes("{{"), "pool drawer left a {{key}} unreplaced"); }
  const biome = Object.keys(api.BIOMES).sort()[0];
  if (biome) { api.showBiome(biome); ok(!drawer.innerHTML.includes("{{"), "biome drawer left a {{key}} unreplaced"); }

  /* The odds have to add up. Half of every draw is a clone of a parent, so
     whatever the other half is made of - one recipe, a tie between several,
     or a spread over pools - it sums to the same 0.5.                      */
  const inPool = Object.values(api.C).find(c => c.pools.length);
  if (inPool) {
    const o = api.oddsFor(inPool.id, inPool.id);
    ok(o.same === true, "oddsFor did not flag two identical parents as the same crop");
    ok(o.det.length === 0, "a recipe fired on two identical parents, which .distinct() rules out");
    ok(o.pools.length === inPool.pools.length, "not every pool of the crop applied to itself");
    const sum = o.rows.reduce((s, r) => s + r.p, 0);
    ok(Math.abs(sum - 0.5) < 1e-9, `same-crop odds sum to ${sum}, expected 0.5`);
  }
  const recipe = api.MUT.find(m => m.parents.length === 2 && m.parents[0] !== m.parents[1]);
  if (recipe) {
    const o = api.oddsFor(recipe.parents[0], recipe.parents[1]);
    const sum = o.rows.reduce((s, r) => s + r.p, 0);
    ok(Math.abs(sum - 0.5) < 1e-9, `recipe odds sum to ${sum}, expected 0.5`);
  }

  /* The crop drawer's shortcut into the roulette: it has to set the pair,
     switch the view, close itself and leave a hash that can be shared. */
  const target = inPool ? inPool.id : crop;
  api.showCrop(target);
  /* Both halves are checked on purpose. The stub hands out a node for any id
     asked for, so a handler bound to a button that is no longer in the markup
     still looks alive here - in a browser it would be a null dereference. */
  ok(/id="pairSelf"/.test(drawer.innerHTML), "the crop drawer markup has no pairSelf button");
  const btn = nodes.get("pairSelf");
  ok(btn && typeof btn.onclick === "function", "nothing is bound to the pairSelf button");
  if (btn && btn.onclick) {
    btn.onclick();
    const [a, b] = api.getPair();
    ok(a === target && b === target, `pairSelf set ${a} + ${b} instead of the crop twice`);
    ok(api.getView() === "pool", `pairSelf left the view on ${api.getView()}`);
    ok(api.getStack().length === 0, "pairSelf did not close the drawer");
    ok(api.getRecent()[0] === `${target}|${target}`, "pairSelf did not record the pair as recent");
    const h = hashes[hashes.length - 1] || "";
    ok(/v=pool/.test(h) && h.includes(`a=${target}`) && h.includes(`b=${target}`),
       `pairSelf wrote the hash ${h}`);
    ok(!/crop=/.test(h), "the hash still points at a drawer that was closed");
  }

  /* The two rail markers make a claim the rail has no other way to show: that
     a crop stick will never hand you this crop. The expected counts are worked
     out from the data here rather than written down, so the check survives a
     mod update but still fails if the template stops emitting a marker - and
     the stub would otherwise hide that, since it answers for any id.        */
  api.render();
  const rail = byId("seedlist").innerHTML;
  const outs = new Set(api.MUT.map(m => m.out));
  const wantBreeder = Object.values(api.C).filter(c => !c.pools.length && outs.has(c.id)
    && api.MUT.filter(m => m.out === c.id).every(m => m.machineOnly)).length;
  const wantNone = Object.values(api.C).filter(c => !c.pools.length && !outs.has(c.id)).length;
  const seen = cls => (rail.match(new RegExp(`class="mark ${cls}"`, "g")) || []).length;
  ok(wantBreeder > 0 && wantNone > 0, "no crop matches either route marker, so this check proves nothing");
  ok(seen("mach") === wantBreeder,
     `rail draws ${seen("mach")} Crop Breeder marks, the data says ${wantBreeder}`);
  ok(seen("none") === wantNone,
     `rail draws ${seen("none")} no-route marks, the data says ${wantNone}`);

  if (bad.length) {
    failed++;
    console.log(`FAIL  ${label}`);
    for (const m of bad) console.log(`      - ${m}`);
  } else {
    console.log(`ok    ${label}`);
  }
}

process.exit(failed ? 1 : 0);
