// Browser check for the classless builder (web/classless.html).
//
// Loads the generated page in headless Chromium and exercises the logic that
// lives only in web/classless-app.html: the one-level-ahead gate, one-of groups
// (hit die, per-level Hit Points, starting kit) and the quick-start presets.
// Exits non-zero if any assertion fails.
//
//   npm i --no-save playwright && npx playwright install chromium
//   node tools/check_builder.mjs
//
// (A globally installed Playwright also works: NODE_PATH=$(npm root -g).)

import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const pageUrl = new URL("../web/classless.html", import.meta.url).href;
const menu = JSON.parse(
  readFileSync(fileURLToPath(new URL("../web/classless-menu.json", import.meta.url)), "utf8"));

const failures = [];
let passed = 0;
function check(name, ok, detail) {
  if (ok) { passed++; console.log(`ok   ${name}`); }
  else { failures.push(name); console.log(`FAIL ${name}${detail ? ` — ${detail}` : ""}`); }
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(pageUrl);

  const spent = async () =>
    parseInt((await page.$eval(".meter__spent", (e) => e.textContent)).replace(/,/g, ""), 10);
  const pressed = async (sel) => (await page.getAttribute(sel, "aria-pressed")) === "true";
  const owned = (sel) => page.$$eval(sel, (es) => es.map((e) => e.dataset.id));
  // Pick the "build as level" dial by its label ("Lv 1", not "Lv 10").
  const setLevel = (n) => page.$$eval("#budget button", (bs, n) => {
    const b = bs.find((b) => b.firstChild.textContent.trim() === `Lv ${n}`);
    if (!b) throw new Error(`no Lv ${n} button`);
    b.click();
  }, n);
  const reset = async () => { await page.click("#reset"); await setLevel(1); };

  // One-level-ahead gate: at level 1, a level-2 piece is open, a level-3 one is not.
  await page.uncheck("#hide-locked");
  await setLevel(1);
  const [lvl2, lvl3] = await page.evaluate(() => {
    const ps = window.__PIECEMEAL_CLASSLESS__.pieces;
    const plain = (p) => !p.commodity && p.tag !== "hp" && !p.upgrades;
    return [ps.find((p) => p.level === 2 && plain(p) && p.xp <= 100).id,
            ps.find((p) => p.level === 3 && plain(p)).id];
  });
  const btn2 = `#features button[data-id="${lvl2}"]`;
  const btn3 = `#features button[data-id="${lvl3}"]`;
  await page.click(btn2, { force: true });
  check(`level-2 piece ${lvl2} selectable at level 1`, await pressed(btn2));
  const title3 = await page.getAttribute(btn3, "title");
  check(`level-3 piece ${lvl3} shows "Unlocks at level 2"`, title3 === "Unlocks at level 2", `title=${title3}`);
  await page.click(btn3, { force: true });
  check(`level-3 piece ${lvl3} not selectable at level 1`, !(await pressed(btn3)));

  // Hit die is one-of: a second pick replaces the first.
  await reset();
  await page.click('#commodities button[data-id="hit-die-d10"]');
  await page.click('#commodities button[data-id="hit-die-d12"]');
  const dice = await owned('#commodities button[data-id^="hit-die-"][aria-pressed="true"]');
  check("second hit die replaces the first", same(dice, ["hit-die-d12"]), `owned=${dice}`);

  // Hit Points at one level are one-of: two picks keep only the last.
  await page.click('#commodities button[data-id="hp-d10-2"]');
  await page.click('#commodities button[data-id="hp-d6-2"]');
  const hp2 = await owned('#commodities .field[data-level="2"] button[aria-pressed="true"]');
  check("two level-2 Hit Points dice keep only the last", same(hp2, ["hp-d6-2"]), `owned=${hp2}`);

  // Starting kit lists its weapons.
  await page.selectOption("#kit", "starting-kit-barbarian");
  const weapons = await page.$eval("#kit-weapons", (e) => e.textContent);
  check("Barbarian kit lists Greataxe, Handaxe, Javelin",
    weapons === "Weapons: Greataxe, Handaxe, Javelin", `got "${weapons}"`);

  // Every SRD standard quick-start preset totals its exported level1Total.
  const presets = Object.entries(menu.presets).filter(([, p]) => p.srd && p.standard);
  check("export has SRD standard presets", presets.length > 0);
  for (const [key, p] of presets) {
    await reset();
    await page.selectOption("#preset", key);
    const total = await spent();
    check(`preset ${key} level-1 total ${total} = export ${p.level1Total}`, total === p.level1Total);
  }

  check("no page errors", errors.length === 0, errors.join(" | "));
} catch (e) {
  // A step that could not run (e.g. a missing control) is a failure too.
  failures.push("aborted");
  console.log(`FAIL aborted — ${String(e.message).split("\n")[0]}`);
} finally {
  await browser.close();
}

console.log(`\n${passed} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
