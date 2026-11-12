#!/usr/bin/env python3
"""Build the web character-builders from the class YAMLs.

Reuses tools/price.py to compute every piece's price, then produces two pages:

  * The per-class builder: web/app.html (body-only source) -> web/index.html.
  * The classless builder: web/classless-app.html -> web/classless.html,
    including the ancestry ledger (data/ancestries/*.yaml, its own budget).

It also exports the canonical classless menu to web/classless-menu.json for
other tools (CharacterManager's Piece-Meal pack is generated from it).

Both pages get their data injected between /*DATA_START*/.../*DATA_END*/ markers
and are wrapped in a minimal HTML skeleton for standalone use. Run after editing
any data/*.yaml:

    python3 tools/build_web.py

Classless pricing: the per-class model prices each feature WITHIN its class,
so a shared menu needs one canonical price per piece. build_menu keys each
canonical piece explicitly (per caster type, per level, or by name) and prices
it: commodities at their catalog price, level-1 features at their premium in
CLASSLESS_FEATURE_PRICE (else points x CLASSLESS_RATE), later features at the
mean in-play XP across the variants that gain them, and Hit Points by the HP
each die gives. Every class's standard SRD level-1 build must fit the 100 budget.
"""
import collections
import glob
import importlib.util
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR = os.path.join(ROOT, "web")

# SRD piece ids deliberately retired from the canonical menu. Saved characters
# (e.g. CharacterManager's Piece-Meal 5e pack) reference these ids, so the build
# refuses to drop any SRD id already in the committed web/classless-menu.json
# unless it is listed here.
RETIRED_IDS = set()

# Flat XP-per-power-point rate for canonical feature prices in the classless
# builder — the fallback for any feature not given an explicit premium below.
CLASSLESS_RATE = 6

# Classless-only feature premiums (feature name -> XP). Standout pieces cost more
# than a flat points x rate, so taking one forces real sacrifices. Anything not
# listed falls back to points x CLASSLESS_RATE.
CLASSLESS_FEATURE_PRICE = {
    "Druid: Spellcasting (1st-level spells)": 39,
    "Wizard: Spellcasting (1st-level spells)": 36,
    "Sorcerer: Spellcasting (1st-level spells)": 36,
    "Warlock: Pact Magic (1st-level spell slots)": 29,
    "Cleric: Spellcasting (1st-level spells)": 26,
    "Bard: Spellcasting (1st-level spells)": 19,
    "Rage": 30,
    "Sneak Attack (1d6)": 28,
    "Martial Arts (d4)": 28,
    "Lay on Hands": 24,
    "Fighting Style": 24,
    "Bardic Inspiration (d6)": 20,
    "Expertise (first pair)": 20,
}

# SRD cumulative XP thresholds. The classless "build as level" budget presets are
# 100 (creation) + these, so higher-level pieces — priced at their real in-play
# XP — unlock only as you raise the dial. That is the "you'd need to be higher
# level to buy this" gating.
SRD_THRESHOLDS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500, 6: 14000, 7: 23000,
                  8: 34000, 9: 48000, 10: 64000, 11: 85000, 12: 100000,
                  13: 120000, 14: 140000, 15: 165000, 16: 195000, 17: 225000,
                  18: 265000, 19: 305000, 20: 355000}
BUDGET_LEVELS = [1, 2, 3, 5, 8, 11, 14, 17, 20]

# Load the pricer as a module so we reuse its exact pricing logic.
_spec = importlib.util.spec_from_file_location(
    "price", os.path.join(ROOT, "tools", "price.py"))
price = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(price)

ROLE = {"none": "Martial", "half": "Half-caster",
        "full": "Full caster", "pact": "Pact Magic"}


def load_subclasses(class_key):
    """(stem, fragment) pairs for a base class, from data/subclasses/<key>/*.yaml."""
    d = os.path.join(DATA_DIR, "subclasses", class_key)
    if not os.path.isdir(d):
        return []
    out = []
    for p in sorted(glob.glob(os.path.join(d, "*.yaml"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        out.append((stem, yaml.safe_load(open(p, encoding="utf-8"))))
    return out


def build_class(path, catalog, subclass=None):
    doc = yaml.safe_load(open(path, encoding="utf-8"))
    base_srd = price.is_srd(doc.get("source"))
    frag_ids = {p["id"] for ps in ((subclass or {}).get("pieces") or {}).values()
                for p in ps}
    frag_srd = price.is_srd((subclass or {}).get("source"))
    if subclass:
        price.merge_subclass(doc, subclass)
    doc["_catalog"] = catalog

    # id -> the piece it upgrades, so the UI can show the chain.
    upgrades = {}
    for lvl in doc["levels"].values():
        for p in lvl["pieces"]:
            if "upgrades" in p:
                upgrades[p["id"]] = p["upgrades"]

    rows, problems = price.price_class(doc)
    if problems:
        raise SystemExit(f"{path}: reconciliation failed: {problems}")

    # Summaries (own words, SRD scope only; non-SRD subclass pieces have none).
    shared = price.load_summaries(DATA_DIR)
    piece_by_id = {p["id"]: p for lvl in doc["levels"].values() for p in lvl["pieces"]}
    def _summary(pid):
        return price.summary_for(piece_by_id.get(pid, {"id": pid}), shared) or ""

    caster = doc.get("caster", "none")
    level1 = [{"id": r["id"], "name": r["name"], "detail": r["tag"],
               "type": r["type"], "xp": r["xp"], "points": r["points"],
               "summary": _summary(r["id"])}
              for r in rows if r["ledger"] == "creation"]
    levels = [{"lvl": r["level"], "id": r["id"], "name": r["name"],
               "tag": r["tag"], "xp": r["xp"], "cum": r["cumulative"],
               "upgrades": upgrades.get(r["id"]), "summary": _summary(r["id"])}
              for r in rows if r["ledger"] == "xp"]

    menu_rows = [dict(r, piece=piece_by_id[r["id"]], summary=_summary(r["id"]),
                      srd=frag_srd if r["id"] in frag_ids else base_srd,
                      fromSubclass=r["id"] in frag_ids)
                 for r in rows]

    return doc["class"].lower(), {
        "name": doc["class"], "subclass": doc.get("subclass", ""),
        "menuRows": menu_rows,
        "hitDie": doc["hit_die"], "caster": caster,
        "role": ROLE.get(caster, "Martial"),
        "budget": catalog["creation_budget"],
        "level1": level1, "levels": levels,
    }


# Skill and tool proficiency slots a classless build may buy.
SKILL_SLOTS = 8
TOOL_SLOTS = 4

# Base-class pieces whose names start with these belong to that class's own
# spellcasting (a caster type): they stay separate per class instead of merging
# by name, so each type keeps its own spell list, tiers and cantrip chain.
CASTER_PREFIXES = ("Spellcasting", "Cantrips Known", "Pact Magic")

WEAPON_NAMES = {
    "none": "Weapons: none",
    "limited": "Weapons: daggers, darts, slings, quarterstaffs, light crossbows",
    "simple": "Weapons: simple",
    "simple_plus_few_martial":
        "Weapons: simple + hand crossbows, longswords, rapiers, shortswords",
    "simple_and_martial": "Weapons: simple + martial",
}
ARMOR_TIERS = {"none": [], "light": ["light"], "medium": ["light", "medium"],
               "heavy": ["light", "medium", "heavy"]}


def _armor_tier(tiers):
    return ("heavy" if "heavy" in tiers else "medium" if "medium" in tiers
            else "light" if "light" in tiers else "none")


def _die_size(die):
    return int(die.lstrip("d"))


def _is_feature_row(r):
    return not ("commodity" in r["piece"] or r["tag"] == "hp")


def _grant_list(grants):
    return [{"id": g, "level": lvl} for g, lvl in grants.items()]


def _mean(xs):
    return round(sum(xs) / len(xs))


def build_menu(catalog, classes):
    """The canonical classless menu: every piece of every class and subclass,
    each shared ability once at one price, as a flat list of pieces.

    * Commodities become generic pieces at their catalog price: one per save,
      skill and tool slot, hit die, armor tier (+ shield) and weapon tier, plus
      one Starting Equipment Package per class carrying its starting weapons.
    * Hit Points are one piece per die per level, priced by the HP it gives:
      the level's mean class-row price, scaled by die HP / mean die HP.
    * Skill and tool slots are padded to SKILL_SLOTS / TOOL_SLOTS pieces.
    * Base-class spellcasting, Pact Magic and Cantrips Known stay per class
      (`<class>-<id>`), chained within the class.
    * A name one class gains at several levels (Ability Score Improvement,
      Magical Secrets...) is one piece per level; any other name is one piece,
      at the earliest level any class gains it.
    * Level-1 features cost their premium or points x rate; later pieces the
      mean price at their level across every subclass variant.

    Returns (menu, grants): grants map each variant key to the pieces that
    rebuild it, {piece id: level gained} in the variant's own order.
    """
    c = catalog["commodities"]
    summaries = price.load_summaries(DATA_DIR)
    classless_summary = summaries.get("classless") or {}

    def shared_summary(piece):
        return price.summary_for(piece, summaries) or ""

    pieces = {}
    occ = {}

    def add(pid, piece, variant, row):
        if pid not in pieces:
            piece.setdefault("sources", [])
            piece.setdefault("srd", False)
            piece["replaces"] = []
            pieces[pid] = piece
            occ[pid] = []
        p = pieces[pid]
        cls = classes[variant]
        if cls["name"] not in p["sources"]:
            p["sources"].append(cls["name"])
        p["srd"] = p["srd"] or row["srd"]
        occ[pid].append((variant, row))
        if cls.get("default"):
            old = f"{cls['name'].lower()}:{row['id']}"
            if old not in p["replaces"]:
                p["replaces"].append(old)
        return pid

    # A name that recurs within one variant is gained per level.
    per_level = set()
    for cls in classes.values():
        seen = set()
        for r in cls["menuRows"]:
            if not _is_feature_row(r):
                continue
            if r["name"] in seen:
                per_level.add(r["name"])
            seen.add(r["name"])

    def feature_key(cls, r):
        name = r["name"]
        if (not r["fromSubclass"] and cls["caster"] not in (None, "none")
                and name.startswith(CASTER_PREFIXES)):
            k = cls["name"].lower()
            return ("type", k, r["id"]), f"{k}-{r['id']}", f"{cls['name']}: {name}"
        if name in per_level:
            return ("level", name, r["level"]), r["id"], name
        return ("name", name), r["id"], name

    keys = {}
    for cls in classes.values():
        for r in cls["menuRows"]:
            if not _is_feature_row(r):
                continue
            key, pid, name = feature_key(cls, r)
            k = keys.setdefault(key, {"id": pid, "name": name,
                                      "subclassOnly": True, "classes": set()})
            k["subclassOnly"] = k["subclassOnly"] and r["fromSubclass"]
            k["classes"].add(cls["name"].lower())
    # Two different pieces with the same YAML id: a subclass piece gives way
    # by taking its class as a prefix; base-class ids never change.
    by_id = {}
    for key, k in keys.items():
        by_id.setdefault(k["id"], []).append(k)
    for pid, ks in by_id.items():
        if len(ks) < 2:
            continue
        for k in ks:
            if k["subclassOnly"]:
                if len(k["classes"]) != 1:
                    sys.exit(f"menu: cannot disambiguate id '{pid}'")
                k["id"] = f"{next(iter(k['classes']))}-{pid}"
    counts = collections.Counter(k["id"] for k in keys.values())
    dupes = {i for i, n in counts.items() if n > 1}
    if dupes:
        sys.exit(f"menu: duplicate piece ids {sorted(dupes)}")

    def commodity(pid, name, tag, xp, **extra):
        p = {"id": pid, "name": name, "level": 1, "xp": xp, "tag": tag}
        p.update(extra)
        return p

    hp_xp = {}
    grants = {v: {} for v in classes}
    row_ids = {}

    for variant, cls in classes.items():
        k = cls["name"].lower()
        rows = cls["menuRows"]
        armor_tiers = [t for r in rows if r["piece"].get("commodity") == "armor"
                       for t in r["piece"].get("tiers", [])]
        n_skill = n_tool = 0
        for r in rows:
            d = r["piece"]
            kind = d.get("commodity")
            out = []
            if kind == "save":
                ab = d["ability"]
                out.append(add(f"save-{ab}", commodity(
                    f"save-{ab}", r["name"], "save", c["save"], commodity="save",
                    ability=ab, summary=shared_summary(d)), variant, r))
            elif kind in ("skill", "tool"):
                for _ in range(d.get("qty", 1)):
                    if kind == "skill":
                        n_skill += 1
                        n = n_skill
                    else:
                        n_tool += 1
                        n = n_tool
                    pid = f"{kind}-{n}"
                    out.append(add(pid, commodity(
                        pid, f"{kind.title()} Proficiency ({n})", kind, c[kind],
                        commodity=kind, summary=classless_summary.get(kind, "")),
                        variant, r))
            elif kind == "hit_die":
                die = d["variant"]
                size = _die_size(die)
                out.append(add(f"hit-die-{die}", commodity(
                    f"hit-die-{die}", f"Hit Die ({die})", "hit_die",
                    c["hit_die"][die], feature="hit-die", commodity="hit_die",
                    hp=size, con=1, hitDieSize=size, summary=shared_summary(d)),
                    variant, r))
            elif kind == "armor":
                tier = _armor_tier(armor_tiers)
                tiers = ARMOR_TIERS[tier]
                label = ", ".join(tiers) or "none"
                out.append(add(f"armor-{tier}", commodity(
                    f"armor-{tier}", f"Armor Proficiency: {label}", "armor",
                    sum(c["armor"][t] for t in tiers), feature="armor-tier",
                    commodity="armor", tiers=tiers,
                    summary=shared_summary(d)), variant, r))
                if "shield" in armor_tiers:
                    out.append(add("shield", commodity(
                        "shield", "Shield Proficiency", "armor", c["armor"]["shield"],
                        commodity="armor", tiers=["shield"],
                        summary=classless_summary.get("shield", "")), variant, r))
            elif kind == "weapon":
                tier = d["tier"]
                pid = "weapon-" + tier.replace("_", "-")
                out.append(add(pid, commodity(
                    pid, WEAPON_NAMES[tier], "weapon", c["weapon"][tier],
                    feature="weapon-tier", commodity="weapon", tier=tier,
                    summary=shared_summary(d)), variant, r))
            elif kind == "starting_kit":
                pid = f"starting-kit-{k}"
                weapons = (catalog.get("starting_kit_weapons") or {}).get(k) or []
                out.append(add(pid, commodity(
                    pid, f"Starting Equipment Package ({cls['name']})",
                    "starting_kit", c["starting_kit"], feature="starting-kit",
                    commodity="starting_kit", weapons=weapons,
                    summary=classless_summary.get("starting_kit", "")), variant, r))
            elif kind:
                sys.exit(f"menu: unhandled commodity '{kind}' in {variant}")
            elif r["tag"] == "hp":
                die = cls["hitDie"]
                lvl = r["level"]
                pid = f"hp-{die}-{lvl}"
                out.append(add(pid, {
                    "id": pid, "name": r["name"], "level": lvl, "xp": None,
                    "tag": "hp", "feature": f"hp-{lvl}",
                    "hp": _die_size(die) // 2 + 1, "con": 1,
                    "hitDieSize": _die_size(die),
                    "summary": r["summary"]}, variant, r))
                hp_xp.setdefault(pid, []).append(r["xp"])
            else:
                key, _, name = feature_key(cls, r)
                kd = keys[key]
                piece = {"id": kd["id"], "name": name, "level": None, "xp": None,
                         "tag": r["tag"], "summary": r["summary"]}
                if key[0] == "type":
                    piece["casterType"] = key[1]
                out.append(add(kd["id"], piece, variant, r))
                if r["summary"] and not pieces[kd["id"]]["summary"]:
                    pieces[kd["id"]]["summary"] = r["summary"]
            row_ids[(variant, r["id"])] = out
            for pid in out:
                grants[variant].setdefault(pid, r["level"])

    # Skill/tool slots: as many as a classless build may buy, not just the most
    # any one variant gains.
    for kind, cap in (("skill", SKILL_SLOTS), ("tool", TOOL_SLOTS)):
        for n in range(1, cap + 1):
            pid = f"{kind}-{n}"
            if pid not in pieces:
                pieces[pid] = commodity(
                    pid, f"{kind.title()} Proficiency ({n})", kind, c[kind],
                    commodity=kind, summary=classless_summary.get(kind, ""),
                    sources=[], srd=True, replaces=[])
                occ[pid] = []

    # Hit Points: price by HP given, so a bigger die always costs more. Each
    # level's base is the mean of its dice's class-row prices.
    hp_levels = {}
    for pid in hp_xp:
        hp_levels.setdefault(pieces[pid]["level"], []).append(pieces[pid])
    for lvl_pieces in hp_levels.values():
        base = sum(_mean(hp_xp[p["id"]]) for p in lvl_pieces) / len(lvl_pieces)
        mean_hp = sum(p["hp"] for p in lvl_pieces) / len(lvl_pieces)
        for p in lvl_pieces:
            p["xp"] = round(base * p["hp"] / mean_hp)

    for pid, rows in occ.items():
        p = pieces[pid]
        if p["tag"] == "hp":
            continue
        if "commodity" in p:
            continue
        lvl = min(r["level"] for _, r in rows)
        p["level"] = lvl
        if lvl == 1:
            pts = _mean([r["points"] or 0 for _, r in rows if r["level"] == 1])
            p["xp"] = CLASSLESS_FEATURE_PRICE.get(p["name"], pts * CLASSLESS_RATE)
        else:
            p["xp"] = _mean([r["xp"] for _, r in rows if r["level"] == lvl])
        ups = set()
        for variant, r in rows:
            up = r["piece"].get("upgrades")
            if up:
                ups.update(row_ids[(variant, up)])
        if len(ups) > 1:
            sys.exit(f"menu: {pid} upgrades several pieces {sorted(ups)}")
        if ups:
            p["upgrades"] = ups.pop()

    # A piece several classes grant gets one description covering them all:
    # when their own summaries differ, data/summaries.yaml `merged:` supplies
    # it, and the build fails rather than keep whichever class came first.
    merged = summaries.get("merged") or {}
    for pid, rows in occ.items():
        texts = {r["summary"] for _, r in rows if r.get("summary")}
        if pid in merged:
            pieces[pid]["summary"] = merged[pid]
        elif len(texts) > 1 and pieces[pid].get("srd"):
            sys.exit(f"menu: {pid} merges classes with different summaries; "
                     f"add one covering them under `merged:` in summaries.yaml")

    order = ["id", "name", "level", "xp", "tag", "sources", "srd", "feature",
             "upgrades", "casterType", "commodity", "ability", "tiers", "tier",
             "hp", "con", "hitDieSize", "weapons", "summary", "replaces"]
    menu = [{f: p[f] for f in order if f in p}
            for p in sorted(pieces.values(),
                            key=lambda p: (p["level"], -p["xp"], p["name"]))]
    return menu, grants


def level1_total(menu, grants):
    xp = {p["id"]: p["xp"] for p in menu}
    return sum(xp[g] for g, lvl in grants.items() if lvl == 1)


def check_menu(menu, grants, classes):
    problems = []
    by_id = {p["id"]: p for p in menu}

    for variant, cls in classes.items():
        total = level1_total(menu, grants[variant])
        if cls.get("default") and total > cls["budget"]:
            problems.append(f"{variant}: standard level-1 build costs "
                            f"{total} > {cls['budget']}")

    covered = {old for p in menu if p["srd"] for old in p["replaces"]}
    for cls in classes.values():
        if cls.get("default"):
            for r in cls["menuRows"]:
                old = f"{cls['name'].lower()}:{r['id']}"
                if old not in covered:
                    problems.append(f"{old}: no canonical SRD piece")

    groups = {}
    for p in menu:
        if p.get("feature"):
            groups.setdefault(p["feature"], []).append(p)
    if len(groups.get("hit-die", [])) != 4:
        problems.append("hit-die group must hold the four hit dice")
    for lvl in range(2, 21):
        hp = sorted(groups.get(f"hp-{lvl}", []), key=lambda p: p["hitDieSize"])
        if len(hp) != 4:
            problems.append(f"hp-{lvl} must hold one Hit Points piece per die")
        if any(a["xp"] >= b["xp"] for a, b in zip(hp, hp[1:])):
            problems.append(f"hp-{lvl}: price must rise with die size "
                            f"{[(p['id'], p['xp']) for p in hp]}")
    kits = [p for p in menu if p.get("commodity") == "starting_kit"]
    if len(kits) != len({c["name"] for c in classes.values()}):
        problems.append("one Starting Equipment Package per class")
    for p in kits:
        if not p["weapons"] or p.get("feature") != "starting-kit":
            problems.append(f"{p['id']}: kit needs weapons and the starting-kit group")
    if len(groups.get("starting-kit", [])) != len(kits):
        problems.append("starting-kit group holds only kits")

    for lvl in (4, 8, 12, 16, 19):
        if f"asi-{lvl}" not in by_id:
            problems.append(f"asi-{lvl} missing")
    names_per_level = {}
    for p in menu:
        names_per_level.setdefault((p["name"], p["level"]), []).append(p["id"])
    for (name, lvl), ps in names_per_level.items():
        if len(ps) > 1 and not name.startswith("Hit Points"):
            problems.append(f"{name} at level {lvl} appears {len(ps)} times: {ps}")

    # One SRD ability, one piece: a subclass-prefixed name ("Circle of the
    # Land: Land's Stride") must not duplicate another piece's plain name.
    subclasses = {cls["subclass"] for cls in classes.values() if cls["subclass"]}
    plain = {}
    for p in menu:
        if p["srd"]:
            pre, sep, rest = p["name"].partition(": ")
            plain.setdefault(rest if sep and pre in subclasses else p["name"],
                             set()).add(p["name"])
    for name, full in plain.items():
        if len(full) > 1:
            problems.append(f"{name} ships as several SRD pieces: {sorted(full)}")

    for lvl in (9, 13, 17):
        p = by_id.get(f"proficiency-bonus-{lvl}")
        if not p or not p.get("upgrades"):
            problems.append(f"proficiency-bonus-{lvl} must upgrade the previous bump")

    bases = [p for p in menu if p.get("casterType") and p["srd"]
             and not p.get("upgrades")
             and not p["name"].split(": ", 1)[1].startswith("Cantrips Known")]
    if len(bases) != 8:
        problems.append(f"expected 8 SRD spellcasting bases, got "
                        f"{[p['id'] for p in bases]}")
    ud = [p for p in menu if p["name"] == "Unarmored Defense"]
    if len(ud) != 1 or sorted(ud[0]["sources"]) != ["Barbarian", "Monk"]:
        problems.append("Unarmored Defense must be one piece from Barbarian and Monk")

    if problems:
        sys.exit("classless menu check failed:\n  - " + "\n  - ".join(problems))


def build_classless(catalog, classes, menu, grants):
    """The classless builder's data: every canonical menu piece (commodities,
    Hit Points and features alike), the "build as level" budgets and the
    "load a standard class" presets, which grant canonical pieces."""
    keep = ("id", "name", "level", "xp", "tag", "sources", "feature", "upgrades",
            "casterType", "commodity", "ability", "tiers", "tier", "hitDieSize",
            "weapons", "summary")
    pieces = [{f: p[f] for f in keep if f in p} for p in menu]
    budgets = [{"level": L, "budget": catalog["creation_budget"] + SRD_THRESHOLDS[L]}
               for L in BUDGET_LEVELS]
    presets = {
        key: {"name": cls["name"], "subclass": cls.get("subclass", ""),
              "grants": _grant_list(grants[key])}
        for key, cls in classes.items()}
    return {"budget": catalog["creation_budget"], "budgets": budgets,
            "order": list(classes.keys()), "presets": presets, "pieces": pieces}


ANCESTRY_ORDER = [
    "human", "elf", "dwarf", "halfling", "dragonborn", "gnome",
    "half_elf", "half_orc", "tiefling", "goliath", "orc",
]


def build_ancestries(catalog):
    """The ancestry ledger for the classless builder: every ancestry priced by
    tools/price.py against `ancestry_budget`, with shared commodities merged
    into one piece listing every ancestry that offers it (offered/owned once).
    Mirrors what CharacterManager's Piece-Meal 5e pack does with the same data.
    """
    anc_dir = os.path.join(DATA_DIR, "ancestries")
    if not os.path.isdir(anc_dir):
        return None
    races, pieces, shared = {}, [], {}
    anc_shared = price.load_summaries(DATA_DIR)
    for key in ANCESTRY_ORDER:
        doc = yaml.safe_load(open(os.path.join(anc_dir, f"{key}.yaml"), encoding="utf-8"))
        rows, problems = price.price_ancestry(doc, catalog)
        if problems:
            sys.exit(f"{key}: " + "; ".join(problems))
        races[key] = {
            "name": doc["ancestry"], "speed": doc["speed"],
            "size": doc.get("size", "Medium"),
            "traits": [{"name": t["name"], "minXp": t.get("min_experience", 0),
                        "text": t.get("description", "")}
                       for t in doc.get("primary_traits") or []],
        }
        detail = {p["id"]: p for p in doc["pieces"]}
        for r in rows:
            d = detail[r["id"]]
            pid = (f"{d['shared']}" if d.get("shared") else f"{key}:{r['id']}")
            if pid in shared:
                shared[pid]["anc"].append(key)
                continue
            piece = {"id": pid, "name": r["name"], "anc": [key], "xp": r["xp"],
                     "tag": r["tag"] or "",
                     "summary": price.summary_for(d, anc_shared, "ancestry") or ""}
            if d.get("commodity") == "ability" and d.get("ability") != "choice":
                piece["abil"] = {d["ability"]: d.get("amount", 1)}
            if d.get("feature"):
                piece["feature"] = d["feature"]
            if d.get("upgrades"):
                piece["req"] = f"{key}:{d['upgrades']}"
            if d.get("shared"):
                shared[pid] = piece
            pieces.append(piece)
    return {"budget": catalog["ancestry_budget"], "cap": 2,
            "order": ANCESTRY_ORDER, "races": races, "pieces": pieces}


def inject(src_path, payload):
    """Replace the DATA marker block in a body-only source and return it."""
    src = open(src_path, encoding="utf-8").read()
    new = re.sub(r"/\*DATA_START\*/.*?/\*DATA_END\*/",
                 lambda m: "/*DATA_START*/" + payload + "/*DATA_END*/",
                 src, flags=re.S)
    open(src_path, "w", encoding="utf-8").write(new)
    return new


def wrap(body, title):
    return ('<!doctype html>\n<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{title}</title>\n'
            '</head>\n<body>\n' + body + '\n</body>\n</html>\n')


def check_stable_ids(menu):
    """Fail if an SRD piece id in the committed export vanished from the new menu.

    Canonical ids are what saved characters store; a renamed id (e.g. a
    subclass-only piece gaining a class prefix after a new collision) would
    silently orphan them.
    """
    path = os.path.join(WEB_DIR, "classless-menu.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        old = json.load(f)
    new_ids = {p["id"] for p in menu}
    missing = sorted(p["id"] for p in old.get("pieces", [])
                     if p.get("srd") and p["id"] not in new_ids
                     and p["id"] not in RETIRED_IDS)
    if missing:
        sys.exit("SRD piece ids in the committed web/classless-menu.json are missing "
                 "from the new menu (saved characters reference them): "
                 + ", ".join(missing)
                 + ". Keep the ids stable, or add them to RETIRED_IDS in "
                 "tools/build_web.py if the removal is intended.")


def main():
    catalog = yaml.safe_load(open(os.path.join(DATA_DIR, "level1_catalog.yaml"), encoding="utf-8"))
    classes, order = {}, []
    # Every subclass variant, keyed "<class>:<stem>", so the classless builder's
    # à-la-carte menu and quick-start presets cover all subclasses, not just the
    # defaults. Ordered class-major so the preset dropdown groups by class.
    all_variants = {}
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.yaml"))):
        if os.path.basename(path) in ("level1_catalog.yaml", "summaries.yaml"):
            continue
        # Build EVERY subclass variant so the per-class page can offer a picker.
        file_key = os.path.splitext(os.path.basename(path))[0]
        frags = load_subclasses(file_key)
        if not frags:
            frags = [(file_key, {})]  # bare class with no subclass dir (fallback)
        subs, sub_order, default_stem = {}, [], None
        for stem, frag in frags:
            key, payload = build_class(path, catalog, subclass=(frag or None))
            subs[stem] = {k: payload[k]
                          for k in ("subclass", "caster", "role", "level1", "levels")}
            sub_order.append(stem)
            all_variants[f"{key}:{stem}"] = payload
            payload["srd"] = all(r["srd"] for r in payload["menuRows"])
            payload["default"] = False
            if frag.get("default"):
                default_stem = stem
        if default_stem is None:
            default_stem = sub_order[0]
        all_variants[f"{key}:{default_stem}"]["default"] = True
        classes[key] = {
            "name": payload["name"], "hitDie": payload["hitDie"],
            "budget": payload["budget"], "defaultSub": default_stem,
            "subOrder": sub_order, "subs": subs,
        }
        order.append(key)

    # Per-class builder.
    per_class = json.dumps({"order": order, "classes": classes},
                           separators=(",", ":"))
    body = inject(os.path.join(WEB_DIR, "app.html"), per_class)
    open(os.path.join(WEB_DIR, "index.html"), "w", encoding="utf-8").write(
        wrap(body, "Piece-Meal D&amp;D — Character Builder"))

    # Canonical classless menu, spanning every subclass variant.
    menu, grants = build_menu(catalog, all_variants)
    check_menu(menu, grants, all_variants)
    check_stable_ids(menu)
    export = {
        "budget": catalog["creation_budget"],
        "pieces": menu,
        "presets": {key: {"name": cls["name"], "subclass": cls["subclass"],
                          "srd": cls["srd"], "standard": cls["default"],
                          "level1Total": level1_total(menu, grants[key]),
                          "grants": _grant_list(grants[key])}
                    for key, cls in all_variants.items()},
    }
    with open(os.path.join(WEB_DIR, "classless-menu.json"), "w", encoding="utf-8") as f:
        json.dump(export, f, indent=1, ensure_ascii=False)
        f.write("\n")

    # Classless builder: menu + presets span every subclass variant.
    classless_data = build_classless(catalog, all_variants, menu, grants)
    classless_data["ancestry"] = build_ancestries(catalog)
    classless = json.dumps(classless_data, separators=(",", ":"))
    cbody = inject(os.path.join(WEB_DIR, "classless-app.html"), classless)
    open(os.path.join(WEB_DIR, "classless.html"), "w", encoding="utf-8").write(
        wrap(cbody, "Piece-Meal D&amp;D — Classless Builder"))

    print(f"Built {len(order)} classes -> web/index.html; "
          f"classless builder -> web/classless.html; "
          f"{len(menu)} pieces ({sum(p['srd'] for p in menu)} SRD) "
          f"-> web/classless-menu.json")


if __name__ == "__main__":
    main()
