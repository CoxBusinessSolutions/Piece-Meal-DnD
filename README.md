# Piece-Meal-DnD

A **piece-meal character economy** for D&D 5e. Instead of taking a whole class
level at once, every level is decomposed into its individual "pieces" (features,
proficiencies, hit die, ...) and each piece is priced. That turns character
building into an à-la-carte shop:

- **At creation**, spend a flat **100-experience budget** to assemble your
  level-1 character piece by piece.
- **In play**, spend earned XP to buy pieces from higher levels.

Everything is built on the **open** SRD 5.1 content (CC-BY-4.0): 12 base
classes, each with one subclass.

## Two ledgers

Level 1 and levels 2–20 are priced by two different rules, because they answer
two different questions.

### Level 1 — the character-creation budget (100 experience)

Every class gets the **same** 100-experience budget to build its 1st-level
character, so no class is strictly richer than another at the start. The trick
that keeps it fair is splitting each class's pieces into two kinds:

1. **Commodities** — the things *shared* across classes: saving throws, skill
   proficiencies, hit die (by size), armor, weapons, tools, and a starting-kit.
   These have **fixed prices** from a single shared table
   (`data/level1_catalog.yaml`), so a d8 hit die or heavy armor costs the *same
   experience no matter which class buys it*. That is what "equal weight for
   shared things" means, enforced by construction.

2. **Unique features** — the class's signature pieces (Spellcasting, Sneak
   Attack, Fighting Style, ...). After the commodities are paid for, **whatever
   is left of the 100 is split among these** in proportion to their power-points.

The consequence is exactly the intended one: a class that buys **fewer/cheaper
commodities has more of its 100 flowing into its signature features**, so those
features "carry more weight." All 12 classes, sorted by how much they spend on
commodities (durability + proficiencies) vs. how much is left for signature
features:

| Class | Hit die | Commodities | Features | Biggest single feature |
|---|:--:|---:|---:|---|
| Sorcerer | d6 | 28 | 72 | Spellcasting 33 |
| Wizard | d6 | 28 | 72 | Spellcasting 33 |
| Monk | d8 | 35 | 65 | Martial Arts 41 |
| Warlock | d8 | 35 | 65 | Pact Magic 29 |
| Druid | d8 | 43 | 57 | Spellcasting 36 |
| Cleric | d8 | 44 | 56 | Spellcasting 28 |
| Rogue | d8 | 46 | 54 | Sneak Attack 25 |
| Barbarian | d12 | 48 | 52 | Rage 33 |
| Bard | d8 | 49 | 51 | Spellcasting 21 |
| Ranger | d10 | 49 | 51 | Favored Enemy 26 |
| Fighter | d10 | 50 | 50 | Fighting Style 31 |
| Paladin | d10 | 50 | 50 | Lay on Hands 31 |

The glass cannons (d6, no armor) keep only 28 in commodities and pour 72 into
magic; the plate-and-shield martials (d10, all armor) spend a full half of their
budget just being durable. Same 100 for everyone — very different characters.

Because every commodity has a fixed price, the budget is a real constraint: a
100-XP character **can't** buy all-armor (12) + a d10 body (10) + all martial
weapons (8) **and** Spellcasting (33) — that's 63 before any other feature. You
have to sacrifice. That is the whole point.

The 100 is **build currency only**. When play begins your earned XP is 0 and the
official SRD thresholds apply from there (level 2 = 300, level 3 = 900, ...).

### Levels 2–20 — the in-play XP ledger

The anchor is the official SRD XP table. The cost to *earn* a level is the delta
between thresholds (earning level 5 costs 6,500 − 2,700 = 3,800 XP). Each piece
is tagged and weighted in **power points** (the `rubric` in each class file); a
level's XP cost is divided among its pieces in proportion to points, using
largest-remainder rounding so:

- every level's piece prices sum **exactly** to that level's XP cost, and
- cumulative totals reproduce the official SRD thresholds exactly.

Prices are **derived, never authored**. To tune the economy you edit `points`
(or the shared catalog) and re-run the pricer — you never hand-write an XP
number.

Scaling features (Sneak Attack dice, Proficiency Bonus bumps, a second
Expertise) are modeled as **buyable upgrade-pieces**: each tier is its own piece
that references the piece it builds on via `upgrades`, forming a purchase chain.

#### Spellcasting sub-scheme

Casters decompose their spell-slot progression into the same kind of
upgrade-pieces: `spell-tier-N` (unlock a new spell level, chained tier to tier),
`spell-slots-L` (incremental slot growth), and `cantrip-*` (cantrips known).
See `data/cleric.yaml` for the reference.

#### Caster shapes

Three spell mechanics are modeled, all with the same upgrade-chain style:

- **Full caster** (Wizard, Cleric) — spells from level 1, a new tier every odd
  level up to 9th.
- **Half caster** (Paladin, Ranger) — no spells at level 1; spellcasting is
  bought at level 2 and a new tier unlocks every four levels (2/5/9/13/17),
  capping at 5th.
- **Pact Magic** (Warlock) — a few short-rest slots that all rise together
  (1st@1 … 5th@9, then only the count grows), plus Mystic Arcanum pieces for
  6th–9th and Eldritch Invocations as their own buyable scaling chain.

## Layout

```
data/level1_catalog.yaml   Shared, fixed prices for level-1 commodities
data/<class>.yaml          Source of truth — one file per class (all 12)
data/<class>.md            Generated breakdown tables (do not edit by hand)
tools/price.py             Pricer / validator
tools/build_web.py         Bundles the data into both web builders
web/index.html             Per-class builder — open in any browser (generated)
web/app.html               Per-class builder source (body-only)
web/classless.html         Classless builder — open in any browser (generated)
web/classless-app.html     Classless builder source (body-only)
```

All 12 SRD classes are present: barbarian, bard, cleric, druid, fighter, monk,
paladin, ranger, rogue, sorcerer, warlock, wizard.

## Web builders

Two dependency-free builders, both self-contained (open in any browser, no
server) and theme-aware:

- **Per-class** (`web/index.html`) — pick a class, see where its 100-experience
  budget goes (commodities vs. signature features, as a two-tone meter you can
  toggle piece by piece), and browse its full levels 2–20 progression with the
  upgrade-chains marked.
- **Classless** (`web/classless.html`) — forget classes: spend one 100-XP budget
  on any mix of pieces (a d12 body with a wizard's spellcasting, heavy armor with
  sneak attack). Commodity pickers plus the deduplicated feature menu, priced
  canonically (see below).

```bash
python3 tools/build_web.py     # regenerate both after any data change
```

The `*-app.html` files are the editable sources; the build injects the data
between their `DATA_START/DATA_END` markers and wraps each into a standalone
page.

### Hosting on GitHub Pages

**Live:** https://coxbusinesssolutions.github.io/Piece-Meal-DnD/

`.github/workflows/pages.yml` publishes the `web/` folder to GitHub Pages on
every push to `main` that touches `web/**` (and via manual dispatch from the
Actions tab). It is already enabled for this repo.

To set it up on a fresh fork:

1. Settings → Pages → **Source: GitHub Actions**.
2. Make sure this workflow is on `main`, then push (or run it manually).

Pages on a **private** repo requires GitHub Pro; on the Free plan the repo must
be **public**. The site is fully self-contained, so it works at the project URL
`https://<owner>.github.io/Piece-Meal-DnD/` with no extra configuration.

## Usage

```bash
python3 tools/price.py data/rogue.yaml             # human-readable report
python3 tools/price.py data/rogue.yaml --markdown  # Markdown tables
python3 tools/price.py data/rogue.yaml --check      # validate; exit 1 if off
```

Requires Python 3 and PyYAML (`pip install pyyaml`).

Validate every class at once (the catalog is data, not a class — skip it):

```bash
for f in data/*.yaml; do
  [ "$(basename "$f")" = "level1_catalog.yaml" ] && continue
  python3 tools/price.py "$f" --check && echo "OK $f"
done
```

## Status

**All 12 SRD classes are complete** — both the level-1 creation budget (each
summing to exactly 100) and the levels 2–20 in-play ledger (each reconciling to
the SRD thresholds through 355,000). Every class shape is represented:

- **Pure martial** — Barbarian, Fighter
- **Martial + resource** — Monk (Ki)
- **Skirmisher** — Rogue
- **Half-caster** — Paladin, Ranger
- **Full caster** — Bard, Cleric, Druid, Sorcerer, Wizard
- **Pact Magic** — Warlock

The web builder (`web/`) is built and deployed — see **Hosting on GitHub Pages**
above.

## Design notes — tunable choices

These are deliberate first-pass calls, not fixed truths. Every one is a single
edit to `data/level1_catalog.yaml` (a price) or a class file's `points` (a
weight) followed by re-running the pricer, so the whole economy re-balances.

- **Commodity prices** (`save=4`, `skill=3`, hit die = die-size, `starting_kit=6`
  flat, armor/weapon tiers) are a starting calibration, not sacred.
- **Starting kit** is a flat 6 for every class — the game roughly balances
  starting gear, so it is not priced per-item.
- **Druid weapons** (a specific 10-weapon list) are priced at the `simple` tier;
  **Monk** ("simple + shortswords") likewise — the extra martial weapons are
  treated as negligible.
- **Bard's three instruments** cost `3 × tool = 9`, correct by the equal-weight
  rule even though flavor instruments arguably matter less than thieves' tools.
- **Champion's Improved Critical** (L3) is tagged `marquee`, so it dominates its
  small level band; drop it to `scaling` if you want it to read as incremental.
- **Life Domain's heavy armor** is folded into the armor commodity, so it costs
  the same heavy-armor price any class pays rather than being a floating feature.

## Classless pricing

The per-class model normalizes each feature's price *within* its class, so the
same feature has different prices in different classes (Spellcasting is 33 in
Wizard, 28 in Cleric; Fighting Style appears in four classes). A single shared
menu needs **one canonical price per piece**. Two knobs in `tools/build_web.py`:

- **Commodities** keep their fixed catalog prices.
- **Features** default to `rubric points × CLASSLESS_RATE` (6), but **standout
  pieces carry an explicit premium** in `CLASSLESS_FEATURE_PRICE` — Spellcasting
  is 45, Pact Magic 38, Rage 30, Sneak Attack 28, down to ribbons at 6. The
  premium is what makes taking a big piece a real sacrifice: with Spellcasting
  at 45, a caster can't also afford a plate-and-martial kit, and the builder
  greys out anything you can't afford.

De-duplication falls out for free (all "Unarmored Defense" / "Spellcasting"
entries collapse to one, tagged with the classes that grant them; the three
"Cantrips Known (2/3/4)" rows collapse to one). The builder enforces the budget:
it locks any feature you can't afford and shows an over-budget banner.

The trade-off: with premiums, rebuilding a *standard* class runs a little over
100 (a full caster is ~110), so even a "pure" build trims a ribbon or two —
on-theme for "you can't have it all." Deviating is the play.

### Levels beyond 1 — the "build as level" dial

The classless builder isn't just level 1. A **level dial** sets the budget along
the SRD curve — 100 (creation) plus that level's cumulative earned XP: Lv 5 ≈
6,600, Lv 20 ≈ 355,100. **Higher-level pieces** (Extra Attack, higher spell
tiers, subclass capstones) join the menu priced at their **real in-play XP**
(the SRD threshold deltas), so at level 1 they're unaffordable — you literally
have to raise your level to buy them. "Hide unaffordable" (on by default) keeps
the low-level view clean; the menu grows as you level up.

- **Canonical price** for a shared higher-level piece is the **mean of its cost
  at the earliest level** it appears (firmer than "cheapest wins").
- **Prerequisites are enforced.** A piece needs the one it upgrades — "3rd-level
  spells" needs "2nd-level spells" needs base "Spellcasting" — shown as a red
  "needs X" chip until satisfied. Removing a piece cascades: its dependents drop
  too.
- **Repeatable picks.** Ability Score Improvements and extra spell slots use a
  stepper so you can buy them more than once. HP and proficiency-bonus bumps are
  still left out (commodity-ish).
- **Load a standard class.** A "Quick start" dropdown reconstructs a stock class
  at the current level — its commodity kit plus every feature it gains up to
  that level — as a baseline you then tweak.

## Roadmap / next steps

- **Classless builder — done so far:** premium pricing for standout pieces, the
  Cantrips-Known collapse, budget enforcement, the level dial with higher-level
  pieces gated by their real in-play XP, **enforced prerequisite chains**,
  **repeatable ASIs / extra slots**, and mean-at-earliest-level canonical prices
  (see *Levels beyond 1*).
- **Load a standard class — done:** a "Quick start" dropdown fills the stock
  class at the chosen level (its commodity kit + its features) as a starting
  point to tweak. Because HP/proficiency bumps aren't in the menu, a loaded
  class sits comfortably under budget, leaving room to deviate.
- **Further polish.** Repeatable-pick cost could escalate (a 5th ASI costing
  more than the 1st); repeatable slots could cap at their real per-class limits;
  and the menu could group by level band for easier scanning.
- **Tune the economy.** Revisit any of the Design-notes choices above; re-run
  `tools/price.py --check` after each change.
- **Broaden content.** More subclasses per class, or non-SRD classes/options
  (mind the SRD 5.1 licensing boundary for anything beyond it).
- **Builder niceties.** Save/share a specific build (permalink), export to a
  printable character sheet, or a side-by-side class comparison view.
