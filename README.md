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

## Layout

```
data/rogue.yaml   Source of truth for the Rogue (the reference prototype)
data/rogue.md     Generated breakdown table (do not edit by hand)
tools/price.py    Pricer / validator
```

## Usage

```bash
python3 tools/price.py data/rogue.yaml             # human-readable report
python3 tools/price.py data/rogue.yaml --markdown  # Markdown table
python3 tools/price.py data/rogue.yaml --check      # validate; exit 1 if off
```

Requires Python 3 and PyYAML (`pip install pyyaml`).

## Status

Rogue is complete as the reference implementation. The remaining 11 SRD classes
follow the same schema; spellcasting (slots + spells known + cantrips) will need
its own pricing sub-scheme layered onto this model.
