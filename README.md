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
features "carry more weight." Compare the two extremes:

| | Commodity load | Left for signature features |
|---|---:|---:|
| **Fighter** (all armor, all weapons, d10) | 50 | 50 → Fighting Style 31, Second Wind 19 |
| **Rogue** (4 skills, light armor, tools, d8) | 46 | 54 → Sneak Attack 25, Expertise 24, Cant 5 |
| **Cleric** (all armor, simple weapons, d8) | 44 | 56 → Spellcasting 28, Disciple 17, Cantrips 11 |
| **Wizard** (no armor, 5 weapons, d6) | 28 | 72 → Spellcasting 33, Arcane Recovery 20, Cantrips 13, Spellbook 6 |

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

## Layout

```
data/level1_catalog.yaml   Shared, fixed prices for level-1 commodities
data/fighter.yaml          Source of truth — Fighter (reference pure martial)
data/wizard.yaml           Source of truth — Wizard  (reference pure caster)
data/rogue.yaml            Source of truth — Rogue   (skirmisher; full 1–20)
data/cleric.yaml           Source of truth — Cleric  (hybrid; full 1–20)
data/*.md                  Generated breakdown tables (do not edit by hand)
tools/price.py             Pricer / validator
```

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

Level-1 character-creation breakdown (100-experience budget):

- **Fighter** — level 1 complete (reference pure martial).
- **Wizard** — level 1 complete (reference pure caster).
- **Rogue** — level 1 complete; **levels 2–20 complete**.
- **Cleric** — level 1 complete; **levels 2–20 complete** (spellcasting scheme).

Next: extend levels 2–20 for Fighter and Wizard, then bring the remaining 8 SRD
classes onto the same two templates (martials follow the Fighter/Rogue, casters
follow the Wizard/Cleric; half-casters and the Warlock need a small slot-table
adjustment).
