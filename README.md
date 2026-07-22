# Piece-Meal-DnD

A **piece-meal leveling economy** for D&D 5e. Instead of gaining a whole level
at once, each class level is decomposed into its individual "pieces" (features),
and every piece is priced as a fraction of the XP that level costs to earn. That
turns character progression into an à-la-carte shop: spend XP on the exact
pieces you want.

Everything is built on the **open** SRD 5.1 content (CC-BY-4.0): 12 base classes,
each with one subclass.

## How the pricing works

The anchor is the official SRD XP table. The cost to *earn* a level is the delta
between thresholds (e.g. earning level 5 costs 6,500 − 2,700 = 3,800 XP).

Each piece is tagged and given a weight in **power points** (see the `rubric` in
each class file). A level's XP cost is divided among its pieces in proportion to
their points, using largest-remainder rounding so:

- every level's piece prices sum **exactly** to that level's XP cost, and
- cumulative totals reproduce the official SRD thresholds exactly.

Prices are **derived, never authored**. To tune the economy you edit `points` in
the YAML and re-run the pricer — you never hand-write an XP number.

Scaling features (Sneak Attack dice, Proficiency Bonus bumps, a second
Expertise) are modeled as **buyable upgrade-pieces**: each tier is its own piece
that references the piece it builds on via `upgrades`, forming a purchase chain.

### Spellcasting sub-scheme

Casters decompose their spell-slot progression into the same kind of
upgrade-pieces:

- `spell-tier-N` — unlocking a whole new spell level (marquee), chained tier to
  tier.
- `spell-slots-L` — incremental slot growth at a level that adds slots without a
  new tier (scaling).
- `cantrip-*` — cantrips-known increases.

Levels whose only spell change is repeated slots (12, 14, 16 for a full caster)
get no spellcasting piece. See `data/cleric.yaml` for the reference.

## Layout

```
data/rogue.yaml    Source of truth — Rogue (reference martial)
data/cleric.yaml   Source of truth — Cleric (reference full caster)
data/*.md          Generated breakdown tables (do not edit by hand)
tools/price.py     Pricer / validator
```

## Usage

```bash
python3 tools/price.py data/rogue.yaml             # human-readable report
python3 tools/price.py data/rogue.yaml --markdown  # Markdown table
python3 tools/price.py data/rogue.yaml --check      # validate; exit 1 if off
```

Requires Python 3 and PyYAML (`pip install pyyaml`).

## Status

- **Rogue** — complete (reference martial).
- **Cleric** — complete (reference full caster; establishes the spellcasting
  sub-scheme).

The remaining 10 SRD classes follow these two templates: martials copy the
Rogue, casters copy the Cleric. Half-casters (Paladin, Ranger) and the
pact-magic Warlock will each need a small slot-table adjustment.

To validate every class at once:

```bash
for f in data/*.yaml; do python3 tools/price.py "$f" --check && echo "OK $f"; done
```
