#!/usr/bin/env python3
"""Piece-Meal-DnD pricer / validator.

Reads a class YAML (see data/rogue.yaml) and turns each piece's power-points
into an XP price by dividing every level's XP cost among its pieces in
proportion to points. Integer prices are allocated with the largest-remainder
method so each level's prices sum EXACTLY to that level's XP cost, and the
cumulative totals reproduce the official SRD thresholds.

Usage:
    python3 tools/price.py data/rogue.yaml            # report to stdout
    python3 tools/price.py data/rogue.yaml --markdown # emit a Markdown table
    python3 tools/price.py data/rogue.yaml --check     # exit 1 if anything is off

Prices are derived, never authored. Edit `points` in the YAML to tune, then
re-run. Exit code is non-zero if reconciliation fails or the data is malformed.
"""
import argparse
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


def price_class(doc):
    """Return (rows, problems). rows: list of dicts with computed prices."""
    thresholds = doc["xp_thresholds"]
    levels = doc["levels"]
    problems = []
    rows = []
    ids_seen = set()
    cumulative = 0

    for lvl in range(1, 21):
        if lvl not in levels:
            continue
        prev = thresholds.get(lvl - 1, 0) if lvl > 1 else 0
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
                "level": lvl,
                "id": pid,
                "name": p["name"],
                "tag": p.get("tag", ""),
                "points": p.get("points", 0),
                "xp": price,
                "cumulative": cumulative,
            })

        if cumulative != thresholds[lvl]:
            problems.append(
                f"L{lvl}: cumulative {cumulative} != threshold {thresholds[lvl]}")

    return rows, problems


def render_text(doc, rows):
    out = [f"{doc['class']} — piece-meal XP breakdown  (source: {doc['source']})", ""]
    cur = None
    for r in rows:
        if r["level"] != cur:
            cur = r["level"]
            out.append(f"Level {cur}")
        out.append(
            f"  {r['xp']:>7,} XP  [{r['tag']:<11}] {r['name']}  (cum {r['cumulative']:,})")
    return "\n".join(out)


def render_markdown(doc, rows):
    out = [f"# {doc['class']} — Piece-Meal XP Breakdown",
           "",
           f"_Source: {doc['source']}. Prices derived from power-points; "
           f"they reconcile to the official SRD XP thresholds._",
           "",
           "| Lvl | Piece | Tag | Pts | XP | Cumulative |",
           "|----:|-------|-----|----:|---:|-----------:|"]
    for r in rows:
        out.append(f"| {r['level']} | {r['name']} | {r['tag']} | {r['points']} "
                   f"| {r['xp']:,} | {r['cumulative']:,} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Price and validate a class YAML.")
    ap.add_argument("path")
    ap.add_argument("--markdown", action="store_true", help="emit a Markdown table")
    ap.add_argument("--check", action="store_true",
                    help="only validate; print nothing on success")
    args = ap.parse_args()

    with open(args.path) as f:
        doc = yaml.safe_load(f)

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
