# Piece-Meal-DnD

A **piece-meal character economy** for D&D 5e. Instead of taking a whole class
level at once, every level is decomposed into its individual "pieces" (features,
proficiencies, hit die, ...) and each piece is priced. That turns character
building into an à-la-carte shop:

- **At creation**, spend a flat **100-experience budget** to assemble your
  level-1 character piece by piece.
- **In play**, spend earned XP to buy pieces from higher levels.

The 12 base classes and their one **SRD reference subclass** are built on the
**open** SRD 5.1 content (CC-BY-4.0). The additional Player's Handbook subclasses
are **not** SRD — their data records only mechanical feature/level facts plus
original weights, with no rules prose (see [License & attribution](#license--attribution)).

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

**Level gate.** A piece also *unlocks* by level: your **XP level** is the SRD
level for your earned XP (6,500 XP = level 5), and a piece opens **one level
ahead** of it — at level 1 you can buy level-2 pieces, at level 6 level-7
pieces — however much XP you've banked. So you buy a level's abilities while
earning your way to it, and reaching a level means already owning them. Without
the gate, every level-2+ piece costs only a slice of its level's XP and could be
bought many levels early. At level 20 nothing is locked. Level-1 pieces stay
buyable after creation: once the 100 is spent, more level-1 pieces (a second
caster type, say) are paid from earned XP. Consumers can loosen the gate:
CharacterManager's `levelGate` setting supports `strict` (the default for
Piece-Meal), `selective` (only pieces flagged `gated`), `warn` (allowed but
marked) and `off`, all with the same one-level allowance. The classless
builder applies it to its "build as level" dial.

**Descriptions.** Every SRD piece has a short own-words `summary:` (one or two
sentences); repeated kinds (Hit Points, saves, spell tiers, +1 ability...) share
one in `data/summaries.yaml`. Non-SRD subclass fragments stay prose-free —
`tools/price.py --check` fails if one carries a summary. Save pieces name their
ability (`ability: dex`) so consumers can grant the real proficiency.

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
  (slot level 1st@1 … 5th@9) and grow in number as in the SRD table (a 2nd
  slot at 2, a 3rd at 11, a 4th at 17 — each its own `slots` piece), plus
  Mystic Arcanum pieces for 6th–9th and Eldritch Invocations as their own
  buyable scaling chain.

## Ancestry — a third, creation-only ledger

Race works the same way as classes, on its own budget. A character **declares**
one or more ancestries (the first is their *primary*, which sets size and base
speed), then buys racial pieces from just those ancestries with a separate
**20-point ancestry budget**. Racial pieces are creation-only: they are never
bought with earned XP.

- **Commodities** shared across ancestries have fixed prices
  (`ancestry_commodities` in `data/level1_catalog.yaml`): +1 to an ability 3,
  a language 2, and darkvision, skill, tool, weapon training, resistance and
  cantrip pieces at 1–2.
- **Unique traits** (Lucky, Breath Weapon, Fey Ancestry, ...) split whatever is
  left of the 20 by power points.
- Every ancestry, bought in full, costs **exactly 20**, so "all of Dwarf" is
  today's Dwarf and a mixed heritage trades breadth for depth.
- Human (+1 to all six plus a language, no unique traits) is pure commodity and
  pins the budget. If commodity prices change, move the budget only in steps of
  10 and re-price every ancestry.
- Subraces fold into their parent (Hill Dwarf's Dwarven Toughness is a Dwarf
  piece); pieces that came from a subrace are tagged `subrace: <id>`. Shared pieces carry a `shared` key (one Darkvision piece no matter
  how many ancestries offer it); the same unique trait in two ancestries carries
  a `feature` key so it can only be owned once.
- Mixed builds may raise any one ability by at most +2 from ancestry pieces.

Ancestries: the 9 SRD 5.1 races plus Goliath and Orc from SRD 5.2. Goliath's
and Orc's +2 STR / +1 CON are a **house rule** (2024 species carry no ability
increases). Goliath's Large Form is a free **primary trait**, not a piece: a
Goliath-primary character unlocks it at 6,500 earned XP (the SRD level-5
threshold, Piece-Meal's stand-in for character level 5).

```bash
python3 tools/price.py data/ancestries/dwarf.yaml            # breakdown
python3 tools/price.py data/ancestries/dwarf.yaml --check    # validate
```

## Layout

```
data/level1_catalog.yaml   Shared, fixed prices for level-1 commodities
data/summaries.yaml        Shared summaries for repeated piece kinds
data/<class>.yaml          Base chassis — one file per class (all 12)
data/subclasses/<class>/<name>.yaml  Subclass fragments merged onto a base
data/<class>.md            Generated breakdown tables (do not edit by hand)
data/ancestries/<id>.yaml  One file per ancestry (racial pieces; ancestry ledger)
data/ancestries/<id>.md    Generated ancestry breakdown tables
tools/price.py             Pricer / validator
tools/build_web.py         Bundles the data into both web builders
web/index.html             Per-class builder — open in any browser (generated)
web/app.html               Per-class builder source (body-only)
web/classless.html         Classless builder (classes + ancestries) — open in any browser (generated)
web/classless-app.html     Classless builder source (body-only)
web/classless-menu.json    Canonical classless menu export (generated)
.github/workflows/pages.yml  Deploys web/ to GitHub Pages on push to main
```

All 12 SRD classes are present: barbarian, bard, cleric, druid, fighter, monk,
paladin, ranger, rogue, sorcerer, warlock, wizard.

### Subclasses (fragments)

A base class file (`data/<class>.yaml`) carries the shared chassis only —
commodities, spellcasting/resource package, HP, ASI, proficiency bumps, and the
base-class capstones — and **no subclass features**. Each subclass lives in its
own fragment under `data/subclasses/<class>/<name>.yaml`, listing only the
archetype pieces keyed by the level they are gained. The pricer splices a
fragment onto its base:

```bash
python3 tools/price.py data/wizard.yaml \
    --subclass data/subclasses/wizard/necromancy.yaml --check
```

Because each level's XP cost is split across whatever pieces are present, any
fragment reconciles to the SRD thresholds automatically — you only choose the
`points` weights. `tools/build_web.py` merges each class's **default** fragment
(the one flagged `default: true`, or the first alphabetically) so the web build
stays whole.

**Licensing boundary.** The 12 base chassis and their one SRD subclass are open
**SRD 5.1 (CC-BY-4.0)**. Fragments for non-SRD subclasses (e.g. the extra Wizard
schools) record only **mechanical feature/level facts** (which feature unlocks,
and when) plus **original power-point weights** — no rules prose is reproduced.
Their `source:` line marks them as such rather than as SRD content. Keep it that
way when adding more: names and level-timing are facts; descriptions are not.

## Web builders

Two dependency-free builders, both self-contained (open in any browser, no
server) and theme-aware:

- **Per-class** (`web/index.html`) — pick a class, see where its 100-experience
  budget goes (commodities vs. signature features, as a two-tone meter you can
  toggle piece by piece), and browse its full levels 2–20 progression with the
  upgrade-chains marked.
- **Classless** (`web/classless.html`) — forget classes: spend one 100-XP budget
  on any mix of pieces (a d12 body with a wizard's spellcasting, heavy armor with
  sneak attack). One-of pickers for hit die, armor tier, weapon tier, starting
  kit and each level's Hit Points; individual saves, skills and tools; and the
  canonical feature menu, where every shared ability appears once (see below).

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
same feature has different prices in different classes (Fighting Style appears
in four classes at four prices). A classless menu needs **one canonical price
per piece**, or players would always buy the cheapest copy. `build_web.py`
builds that **canonical menu** from every class *and every subclass variant*,
and the classless builder, its presets and the exported menu all use it.

- **Shared abilities appear once.** Every "Unarmored Defense", "Extra Attack" or
  "Fighting Style" collapses to one piece, tagged with the classes that grant it
  in 5e. Its upgrades chain from that one piece.
- **Per-level repeats are separate pieces.** An ability a class gains more than
  once — Ability Score Improvement, Magical Secrets — is one piece per level at
  which it is gained (`asi-4`, `asi-8`, ...), each bought at most once.
- **Spellcasting is bought per caster type.** Bard, Cleric, Druid, Sorcerer,
  Wizard, Paladin, Ranger and Warlock's Pact Magic are each their own piece
  (`wizard-spellcasting`, `warlock-pact-magic`), with their own spell-level tiers
  and Cantrips Known chain, so each type keeps its own spell list. Buying Wizard
  and then Sorcerer spellcasting is two purchases.
- **Commodities** keep their fixed catalog prices, as individual pieces:
  - one **hit die** (d6/d8/d10/d12);
  - one **armor tier** (none, light, light + medium, all three), with **shield**
    as a separate piece on top of any tier;
  - one **weapon tier**;
  - each **saving throw** (`save-str` ... `save-cha`), **skill** and **tool**
    slot is its own piece;
  - one **Starting Equipment Package** per class (`starting-kit-barbarian`, ...),
    each listing that class's 5e starting weapons — buying the Barbarian kit
    gives a greataxe, handaxes and javelins.
- **Hit Points are per die, per level.** Each level 2–20 has a Hit Points piece
  for each die size (`hp-d10-5`), priced from what the classes with that die pay
  for it, so a cheap starting die doesn't make later HP cheap.
- **One-of groups.** You own at most one of each: hit die, Hit Points piece per
  level, starting kit, armor tier, weapon tier. Pieces carry the group in their
  `feature` key (`hit-die`, `hp-<level>`, `starting-kit`, `armor-tier`,
  `weapon-tier`); in the builder, picking another option in a group replaces the
  one you had.
- **Prices.** Level-1 features default to `rubric points × CLASSLESS_RATE` (6),
  but **standout pieces carry an explicit premium** in `CLASSLESS_FEATURE_PRICE`
  (each caster type's Spellcasting, Rage, Sneak Attack, Martial Arts...). The
  premium is what makes taking a big piece a real sacrifice. Higher-level pieces
  cost the **mean of their in-play XP at the earliest level** they appear,
  across every subclass that grants them.
- **Standard builds fit.** Premiums are tuned so every class's standard SRD
  level-1 build costs at most 100 (most land on exactly 100). The build enforces
  it: `tools/build_web.py` fails if any standard build goes over, if a shared
  ability appears twice, or if a group is malformed.

### Levels beyond 1 — the "build as level" dial

The classless builder isn't just level 1. A **level dial** sets the budget along
the SRD curve — 100 (creation) plus that level's cumulative earned XP: Lv 5 ≈
6,600, Lv 20 ≈ 355,100 — pooled into one budget. **Higher-level pieces** (Extra
Attack, higher spell tiers, subclass capstones) are priced at their **real
in-play XP** (the SRD threshold deltas) and open one level ahead of the dial
(the level gate above), so a level-1 build can already pick level-2 pieces.
"Hide unaffordable" (on by default) keeps the low-level view clean; the menu
grows as you level up, and a Hit Points picker appears for each level up to the
gate.

- **Prerequisites are enforced.** A piece needs the one it upgrades — "3rd-level
  spells" needs "2nd-level spells" needs that type's base "Spellcasting" — shown
  as a red "needs X" chip until satisfied. Removing a piece cascades: its
  dependents drop too.
- **Load a standard class.** A "Quick start" dropdown rebuilds a stock class and
  subclass at the current level from canonical pieces — hit die, Hit Points,
  saves, kit and every feature it gains up to that level — as a baseline you
  then tweak.

### Menu export

The build also writes the canonical menu to `web/classless-menu.json`:
`{budget, pieces, presets}`. Each piece carries its `id`, `name`, `level`, `xp`,
`tag`, granting classes (`sources`), an `srd` flag, a `summary`, the per-class
piece ids it `replaces` (`wizard:spellcasting`), and where relevant its group
(`feature`), `upgrades`, `casterType`, commodity fields (`ability`, `tiers`,
`tier`, `hp`/`con` on hit dice and Hit Points, `hitDieSize`, kit `weapons`).
Each preset lists its `grants` and `level1Total`. Prices span every subclass;
apps that ship only SRD content (CharacterManager's Piece-Meal 5e pack) take the
`srd: true` pieces at the same prices.

## Roadmap / next steps

- **Classless builder — done so far:** canonical per-piece prices across every
  subclass, per-caster-type spellcasting, per-level repeats, per-die Hit Points,
  one-of groups, the one-level-ahead gate, enforced prerequisite chains,
  standard builds fitting 100, and the menu export (see *Classless pricing*).
- **Load a standard class — done:** a "Quick start" dropdown fills the stock
  class at the chosen level from canonical pieces as a starting point to tweak.
- **Further polish.** The menu could group by level band for easier scanning.
- **Tune the economy.** Revisit any of the Design-notes choices above; re-run
  `tools/price.py --check` after each change.
- **Subclasses — in progress.** Base classes now carry no subclass features;
  each subclass is a fragment under `data/subclasses/<class>/` merged onto the
  base. Done: Wizard (8 schools); Fighter (Champion, Battle Master, Eldritch
  Knight); Barbarian (Berserker, Totem Warrior); Bard (Lore, Valor); Druid
  (Land, Moon); Ranger (Hunter, Beast Master); Rogue (Thief, Assassin, Arcane
  Trickster); Monk (Open Hand, Way of Shadow, Way of the Four Elements); Sorcerer
  (Draconic Bloodline, Wild Magic); Warlock
  (The Fiend, The Archfey, The Great Old One); Paladin (Oath of Devotion, Oath of
  the Ancients, Oath of Vengeance); Cleric (Life, Knowledge, Light, Nature,
  Tempest, Trickery, War). **All 12 classes now have every PHB subclass.**
  The per-class web builder (`web/index.html`) has a **subclass picker** — pick a
  class, then any of its subclasses from a dropdown, and the level-1 breakdown and
  the 2–20 progression re-render for that subclass. `build_web.py` emits every
  variant per class; the classless builder consumes all of them.
  - **Level-1 subclasses.** Sorcerer origins and Warlock patrons grant features
    at level 1, so `merge_subclass` inserts fragment pieces *after* the level-1
    commodities (keeping saves/armor/etc. first) and among the unique features.
  - **Ordering note.** When a subclass feature interleaves with base features at
    a level (e.g. Bard L3, Monk L6), the prepend-merge reorders those rows; that
    can flip a largest-remainder tiebreak by ±1 XP. Prices still reconcile and no
    pieces change — it is cosmetic. Wizard/Fighter, whose subclass pieces lead
    their level, stay byte-identical.
  - **Subclass proficiency changes.** A fragment can `override` a base commodity
    it can't express additively — Tempest/War Domain upgrade `weapons-1` from
    simple to simple_and_martial that way. Additive grants (heavy armor as an
    extra `[heavy]` armor piece, Knowledge's bonus skills as a skill commodity)
    are just extra pieces. Heavy-and-martial domains spend more of their 100 on
    durability, so less is left for their features — the intended trade-off.
  - **Classless builder covers every subclass.** The à-la-carte menu and the
    "load a standard class" quick-start now span all 40 subclass variants (menu
    grew from ~200 to ~330 pieces; quick-start lists each class+subclass). The
    classless builder consumes all variants; the per-class page uses the picker.
  - **Subclass commitment — resolved as "free".** Subclass features stay
    free-floating (no cross-feature `upgrades:` chains): the classless builder is
    explicitly "mix anything," so requiring the whole subclass would fight that
    ethos. Feature *timing* is still gated by XP, and *internal* chains that
    already exist (spell tiers, superiority dice, cantrips) keep their `upgrades`
    prerequisites — e.g. "Eldritch Knight: 2nd-level spells" needs its 1st-level
    Spellcasting. Only the "you took this subclass" gate is intentionally absent.
- **Ancestry ledger — done.** Eleven ancestries priced on their own 20-point,
  creation-only budget (see *Ancestry*). The classless builder has an Ancestry
  card (declare ancestries, primary first; shared traits listed once; +2 cap;
  Goliath's Large Form unlocks at Lv 5). The same data drives CharacterManager's
  Piece-Meal 5e pack. Not yet in the per-class builder (`web/index.html`).
- **Broaden content.** More subclasses per class, or non-SRD classes/options
  (mind the SRD 5.1 licensing boundary for anything beyond it).
- **Builder niceties.** Save/share a specific build (permalink), export to a
  printable character sheet, or a side-by-side class comparison view.

## License & attribution

**Code** — the tooling and page sources in this repo (`tools/`, `web/*-app.html`)
are licensed under the **GNU General Public License v2** (see `LICENSE`).

**SRD content** — this project includes material from the **System Reference
Document 5.1 ("SRD 5.1")** by Wizards of the Coast LLC, available at
<https://dnd.wizards.com/resources/systems-reference-document>, licensed under
the **Creative Commons Attribution 4.0 International License**
(<https://creativecommons.org/licenses/by/4.0/legalcode>). The 12 base classes
and their one SRD reference subclass come from the SRD 5.1, as do the nine 2014
races in `data/ancestries/`. The **Goliath** and **Orc** ancestries include
material from the **System Reference Document 5.2 ("SRD 5.2")**, also CC-BY-4.0;
their +2 STR / +1 CON ability increases are a **house rule**, not SRD 5.2.

**Non-SRD subclasses** — the additional Player's Handbook subclasses are **not**
covered by the SRD or CC-BY. Their data files record only **mechanical facts**
(each feature's name and the level it is gained) plus **original, project-authored
power-point weights**. No descriptive or rules prose from any non-SRD source is
reproduced; each such file's `source:` line marks it accordingly. If you reuse
this repo, do not relabel that data as SRD/CC-BY.

**Trademarks / affiliation** — Dungeons & Dragons, D&D, Player's Handbook, and
related marks are trademarks of Wizards of the Coast LLC. This is an
**unofficial, fan-made tool** and is **not affiliated with, sponsored, endorsed,
or approved by Wizards of the Coast**.

See `NOTICE` for the same summary in one place.
