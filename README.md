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
```

All 12 SRD classes are present: barbarian, bard, cleric, druid, fighter, monk,
paladin, ranger, rogue, sorcerer, warlock, wizard.

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

Possible next steps: tune the commodity/point values, add the non-SRD classes or
alternate subclasses, or build a front-end that reads these YAMLs as an
à-la-carte character-builder shop.
