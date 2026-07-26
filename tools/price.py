#!/usr/bin/env python3
"""Piece-Meal-DnD pricer / validator.

Two ledgers, priced separately:

  * LEVEL 1 — character creation. Every class spends the same flat CREATION
    BUDGET (see data/level1_catalog.yaml, default 100 experience). "Commodity"
    pieces — the things shared across classes (saves, skills, hit die, armor,
    weapons, tools, starting kit) — cost their fixed catalog price, so they are
    identical in every class. Whatever budget is left over is divided among the
    class's UNIQUE features in proportion to their power-points. Every class
    therefore totals exactly the budget, and a class that buys fewer commodities
    pours more of its 100 into its signature features.

  * LEVELS 2-20 — in-play XP. Each level's XP cost (the delta between official
    SRD thresholds) is divided among that level's pieces in proportion to
    points, using the largest-remainder method so the cumulative totals
    reproduce the SRD thresholds exactly. Level 1 contributes 0 here: the
    creation budget is spent before play and earned XP starts at 0.

Usage:
    python3 tools/price.py data/rogue.yaml            # report to stdout
    python3 tools/price.py data/rogue.yaml --markdown # emit Markdown tables
    python3 tools/price.py data/rogue.yaml --check    # exit 1 if anything is off

Commodity prices come from the catalog; unique/in-play prices are derived from
points. Neither is hand-authored. Edit points (or the catalog) to tune, then
re-run. Exit code is non-zero if reconciliation fails or the data is malformed.
"""
import argparse
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


def largest_remainder(total, weights):
    """Split integer `total` across `weights` proportionally, summing exactly.

    Returns a list of ints the same length as `weights`. If every weight is 0
    the total is spread as evenly as possible so nothing is silently dropped.
    """
    n = len(weights)
    if n == 0:
        return []
    wsum = sum(weights)
    if wsum == 0:
        base, rem = divmod(total, n)
        return [base + (1 if i < rem else 0) for i in range(n)]
    raw = [total * w / wsum for w in weights]
    floors = [int(r) for r in raw]
    remainder = total - sum(floors)
    # Hand out the leftover to the largest fractional parts first.
    order = sorted(range(n), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in order[:remainder]:
        floors[i] += 1
    return floors


def merge_subclass(doc, frag):
    """Splice a subclass fragment onto a base-class doc, in place.

    A fragment (data/subclasses/<class>/<name>.yaml) carries only its
    arcane-tradition / archetype pieces keyed by the level they are gained.
    Those pieces are inserted after any leading run of COMMODITY pieces and
    before the level's other pieces. For levels 2-20 there are no commodities,
    so this is a plain front-insert (subclass feature, then HP), matching the
    original woven files. For level 1 it keeps the commodities first and slots
    the subclass features in among the unique features, where they belong. The
    base class's XP thresholds are untouched, so every level still reconciles.
    """
    doc["subclass"] = frag.get("subclass", doc.get("subclass", ""))
    fsrc = frag.get("source")
    if fsrc and fsrc != doc.get("source"):
        base = doc.get("source", "")
        doc["source"] = f"{base}; subclass — {fsrc}" if base else fsrc
    for lvl, pieces in (frag.get("pieces") or {}).items():
        lvl = int(lvl)
        doc["levels"].setdefault(lvl, {"pieces": []})
        existing = doc["levels"][lvl]["pieces"]
        i = 0
        while i < len(existing) and "commodity" in existing[i]:
            i += 1
        doc["levels"][lvl]["pieces"] = existing[:i] + list(pieces) + existing[i:]
    # Optional `overrides`: patch an existing base piece in place (matched by id
    # across any level). Used when a subclass changes a shared commodity it can't
    # express additively -- e.g. War Domain upgrading base `weapons-1` from simple
    # to simple_and_martial. Additive grants (heavy armor, bonus skills) are just
    # extra commodity pieces in `pieces` instead.
    for ov in frag.get("overrides") or []:
        matched = False
        for lvl in doc["levels"].values():
            for p in lvl["pieces"]:
                if p.get("id") == ov["id"]:
                    p.update(ov.get("set", {}))
                    matched = True
        if not matched:
            raise SystemExit(f"override targets unknown piece id '{ov['id']}'")
    return doc


def load_catalog(class_path):
    """Load the shared level-1 commodity catalog next to the class file."""
    cat_path = os.path.join(os.path.dirname(class_path), "level1_catalog.yaml")
    if not os.path.exists(cat_path):
        return None
    with open(cat_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def commodity_xp(piece, catalog, problems):
    """Fixed creation-XP price of a commodity piece, resolved from the catalog."""
    table = catalog["commodities"]
    kind = piece["commodity"]
    try:
        if kind == "hit_die":
            return table["hit_die"][piece["variant"]]
        if kind == "armor":
            return sum(table["armor"][t] for t in piece["tiers"])
        if kind == "weapon":
            return table["weapon"][piece["tier"]]
        if kind in ("skill", "tool"):
            return table[kind] * piece.get("qty", 1)
        return table[kind]  # save, starting_kit, or any flat scalar
    except KeyError as e:
        problems.append(f"{piece.get('id', '?')}: unknown commodity spec {e}")
        return 0


def price_level_1(doc, catalog, ids_seen, problems):
    """Price the creation budget: fixed commodities + unique features fill up."""
    rows = []
    pieces = doc["levels"][1]["pieces"]
    budget = doc["levels"][1].get("budget", catalog["creation_budget"])

    commodities = [p for p in pieces if "commodity" in p]
    uniques = [p for p in pieces if "commodity" not in p]

    commodity_prices = [commodity_xp(p, catalog, problems) for p in commodities]
    spent = sum(commodity_prices)
    remainder = budget - spent
    if remainder < 0:
        problems.append(
            f"L1: commodities cost {spent} > creation budget {budget}")
        remainder = 0
    unique_prices = largest_remainder(remainder, [p.get("points", 0) for p in uniques])

    running = 0
    for group, prices, ptype in ((commodities, commodity_prices, "commodity"),
                                 (uniques, unique_prices, "feature")):
        for p, price in zip(group, prices):
            pid = p["id"]
            if pid in ids_seen:
                problems.append(f"Duplicate piece id: {pid}")
            ids_seen.add(pid)
            running += price
            rows.append({
                "level": 1, "ledger": "creation", "id": pid, "name": p["name"],
                "type": ptype, "tag": p.get("tag", p.get("commodity", "")),
                "points": p.get("points", ""), "xp": price, "cumulative": running,
            })

    total = spent + sum(unique_prices)
    if total != budget:
        problems.append(f"L1: creation total {total} != budget {budget}")
    return rows


def price_class(doc):
    """Return (rows, problems). rows carry computed prices for both ledgers."""
    thresholds = doc["xp_thresholds"]
    levels = doc["levels"]
    problems = []
    rows = []
    ids_seen = set()
    catalog = doc.get("_catalog")

    # Level 1 — creation budget (only if it uses the commodity model).
    if 1 in levels and any("commodity" in p for p in levels[1]["pieces"]):
        if catalog is None:
            problems.append("Level 1 uses commodities but no catalog was found.")
        else:
            rows += price_level_1(doc, catalog, ids_seen, problems)

    # Levels 2-20 — in-play XP, reconciling to the SRD thresholds. Level 1
    # contributes 0 to this ledger (earned XP starts at 0 when play begins).
    cumulative = 0
    for lvl in range(2, 21):
        if lvl not in levels:
            continue
        prev = thresholds.get(lvl - 1, 0)
        cost = thresholds[lvl] - prev
        pieces = levels[lvl]["pieces"]
        prices = largest_remainder(cost, [p.get("points", 0) for p in pieces])
        if sum(prices) != cost:
            problems.append(f"L{lvl}: prices sum to {sum(prices)}, expected {cost}")
        for p, price in zip(pieces, prices):
            pid = p["id"]
            if pid in ids_seen:
                problems.append(f"Duplicate piece id: {pid}")
            ids_seen.add(pid)
            up = p.get("upgrades")
            if up and up not in ids_seen:
                problems.append(f"{pid}: upgrades unknown/earlier-missing id '{up}'")
            cumulative += price
            rows.append({
                "level": lvl, "ledger": "xp", "id": pid, "name": p["name"],
                "type": "feature", "tag": p.get("tag", ""),
                "points": p.get("points", 0), "xp": price, "cumulative": cumulative,
            })
        if cumulative != thresholds[lvl]:
            problems.append(
                f"L{lvl}: cumulative {cumulative} != threshold {thresholds[lvl]}")

    return rows, problems


def render_text(doc, rows):
    out = [f"{doc['class']} — piece-meal breakdown  (source: {doc['source']})", ""]
    cur = None
    for r in rows:
        if r["level"] != cur:
            cur = r["level"]
            tag = "  (creation budget)" if r["ledger"] == "creation" else ""
            out.append(f"Level {cur}{tag}")
        out.append(
            f"  {r['xp']:>7,} XP  [{str(r['tag']):<12}] {r['name']}  (cum {r['cumulative']:,})")
    return "\n".join(out)


def render_markdown(doc, rows):
    creation = [r for r in rows if r["ledger"] == "creation"]
    inplay = [r for r in rows if r["ledger"] == "xp"]
    out = [f"# {doc['class']} — Piece-Meal Breakdown",
           "",
           f"_Source: {doc['source']}. Prices are derived, not hand-authored._",
           ""]
    if creation:
        budget = creation[-1]["cumulative"]
        out += [f"## Level 1 — Character Creation ({budget} experience budget)",
                "",
                "_Commodity pieces cost their fixed catalog price (identical in "
                "every class); the class's unique features split whatever budget "
                "is left. Spent at creation — earned XP starts at 0 in play._",
                "",
                "| Piece | Type | Detail | XP | Spent |",
                "|-------|------|--------|---:|------:|"]
        for r in creation:
            out.append(f"| {r['name']} | {r['type']} | {r['tag']} | "
                       f"{r['xp']} | {r['cumulative']} |")
        out.append("")
    if inplay:
        out += ["## Levels 2-20 — In-Play XP",
                "",
                "_Each level's XP cost (SRD threshold delta) split among its "
                "pieces by power-points; cumulative reproduces the SRD table._",
                "",
                "| Lvl | Piece | Tag | Pts | XP | Cumulative |",
                "|----:|-------|-----|----:|---:|-----------:|"]
        for r in inplay:
            out.append(f"| {r['level']} | {r['name']} | {r['tag']} | {r['points']} "
                       f"| {r['xp']:,} | {r['cumulative']:,} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Price and validate a class YAML.")
    ap.add_argument("path")
    ap.add_argument("--subclass", metavar="FRAGMENT",
                    help="merge a subclass fragment "
                         "(data/subclasses/<class>/<name>.yaml) onto the base")
    ap.add_argument("--markdown", action="store_true", help="emit Markdown tables")
    ap.add_argument("--check", action="store_true",
                    help="only validate; print nothing on success")
    args = ap.parse_args()

    with open(args.path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if args.subclass:
        with open(args.subclass, encoding="utf-8") as f:
            merge_subclass(doc, yaml.safe_load(f))
    doc["_catalog"] = load_catalog(args.path)

    rows, problems = price_class(doc)

    if problems:
        print("RECONCILIATION FAILED:", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        sys.exit(1)

    if args.check:
        return
    if args.markdown:
        print(render_markdown(doc, rows))
    else:
        print(render_text(doc, rows))


if __name__ == "__main__":
    main()
