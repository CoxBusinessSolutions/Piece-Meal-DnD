#!/usr/bin/env python3
"""Build the web character-builders from the class YAMLs.

Reuses tools/price.py to compute every piece's price, then produces two pages:

  * The per-class builder: web/app.html (body-only source) -> web/index.html.
  * The classless builder: web/classless-app.html -> web/classless.html.

Both pages get their data injected between /*DATA_START*/.../*DATA_END*/ markers
and are wrapped in a minimal HTML skeleton for standalone use. Run after editing
any data/*.yaml:

    python3 tools/build_web.py

Classless pricing: the per-class model normalizes each feature's price WITHIN
its class, so the same feature has different prices in different classes. A
single shared menu needs one canonical price per piece, so the classless builder
prices every feature at `rubric points x CLASSLESS_RATE` (commodities keep their
fixed catalog prices). That makes de-duplication automatic and the rubric the
single source of truth. Consequence: rebuilding a standard class costs ~95-100,
not exactly 100.
"""
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

# Flat XP-per-power-point rate for canonical feature prices in the classless
# builder — the fallback for any feature not given an explicit premium below.
CLASSLESS_RATE = 6

# Classless-only feature premiums (feature name -> XP). Standout pieces cost more
# than a flat points x rate, so taking one forces real sacrifices — you can't
# pair full spellcasting with a plate-and-martial kit. Anything not listed falls
# back to points x CLASSLESS_RATE. Tune freely; the per-class model is untouched.
CLASSLESS_FEATURE_PRICE = {
    "Spellcasting (1st-level spells)": 45,
    "Pact Magic (1st-level spell slots)": 38,
    "Rage": 30,
    "Sneak Attack (1d6)": 28,
    "Martial Arts (d4)": 28,
    "Bardic Inspiration (d6)": 26,
    "Lay on Hands": 24,
    "Fighting Style": 24,
    "Expertise (first pair)": 22,
}

# Load the pricer as a module so we reuse its exact pricing logic.
_spec = importlib.util.spec_from_file_location(
    "price", os.path.join(ROOT, "tools", "price.py"))
price = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(price)

ROLE = {"none": "Martial", "half": "Half-caster",
        "full": "Full caster", "pact": "Pact Magic"}


def build_class(path, catalog):
    doc = yaml.safe_load(open(path))
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

    caster = doc.get("caster", "none")
    level1 = [{"id": r["id"], "name": r["name"], "detail": r["tag"],
               "type": r["type"], "xp": r["xp"], "points": r["points"]}
              for r in rows if r["ledger"] == "creation"]
    levels = [{"lvl": r["level"], "id": r["id"], "name": r["name"],
               "tag": r["tag"], "xp": r["xp"], "cum": r["cumulative"],
               "upgrades": upgrades.get(r["id"])}
              for r in rows if r["ledger"] == "xp"]

    return doc["class"].lower(), {
        "name": doc["class"], "subclass": doc.get("subclass", ""),
        "hitDie": doc["hit_die"], "caster": caster,
        "role": ROLE.get(caster, "Martial"),
        "budget": catalog["creation_budget"],
        "level1": level1, "levels": levels,
    }


def build_classless(catalog, classes):
    """One shared, deduplicated level-1 menu with canonical prices."""
    c = catalog["commodities"]
    armor = c["armor"]
    armor_opts = [
        {"id": "none", "label": "None", "xp": 0},
        {"id": "light", "label": "Light", "xp": armor["light"]},
        {"id": "medium", "label": "Light + Medium",
         "xp": armor["light"] + armor["medium"]},
        {"id": "heavy", "label": "Light + Medium + Heavy",
         "xp": armor["light"] + armor["medium"] + armor["heavy"]},
    ]
    weapon_labels = {
        "none": "None", "limited": "Limited list", "simple": "All simple",
        "simple_plus_few_martial": "Simple + a few martial",
        "simple_and_martial": "Simple + Martial",
    }
    weapon_opts = [{"id": k, "label": weapon_labels.get(k, k), "xp": v}
                   for k, v in c["weapon"].items()]
    hitdie_opts = [{"id": k, "label": k, "xp": v}
                   for k, v in sorted(c["hit_die"].items(), key=lambda kv: kv[1])]

    # Features: union of every class's level-1 unique features, de-duplicated by
    # name, priced at points x rate, tagged with the classes that grant them.
    feats = {}
    for cls in classes.values():
        for p in cls["level1"]:
            if p["type"] != "feature":
                continue
            pts = p["points"] or 0
            # Collapse the near-duplicate "Cantrips Known (2/3/4)" rows into one.
            if p["name"].startswith("Cantrips Known"):
                fid, name = "cantrips-known", "Cantrips Known"
            else:
                fid, name = p["id"], p["name"]
            xp = CLASSLESS_FEATURE_PRICE.get(name, pts * CLASSLESS_RATE)
            f = feats.setdefault(name, {
                "id": fid, "name": name, "tag": p["detail"],
                "points": pts, "xp": xp, "sources": []})
            if cls["name"] not in f["sources"]:
                f["sources"].append(cls["name"])
    features = sorted(feats.values(), key=lambda f: (-f["xp"], f["name"]))

    return {
        "budget": catalog["creation_budget"], "rate": CLASSLESS_RATE,
        "commodities": {
            "save": c["save"], "skill": c["skill"], "tool": c["tool"],
            "starting_kit": c["starting_kit"], "shield": armor["shield"],
            "hitDie": hitdie_opts, "armor": armor_opts, "weapon": weapon_opts,
        },
        "features": features,
    }


def inject(src_path, payload):
    """Replace the DATA marker block in a body-only source and return it."""
    src = open(src_path).read()
    new = re.sub(r"/\*DATA_START\*/.*?/\*DATA_END\*/",
                 lambda m: "/*DATA_START*/" + payload + "/*DATA_END*/",
                 src, flags=re.S)
    open(src_path, "w").write(new)
    return new


def wrap(body, title):
    return ('<!doctype html>\n<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{title}</title>\n'
            '</head>\n<body>\n' + body + '\n</body>\n</html>\n')


def main():
    catalog = yaml.safe_load(open(os.path.join(DATA_DIR, "level1_catalog.yaml")))
    classes, order = {}, []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.yaml"))):
        if os.path.basename(path) == "level1_catalog.yaml":
            continue
        key, payload = build_class(path, catalog)
        classes[key] = payload
        order.append(key)

    # Per-class builder.
    per_class = json.dumps({"order": order, "classes": classes},
                           separators=(",", ":"))
    body = inject(os.path.join(WEB_DIR, "app.html"), per_class)
    open(os.path.join(WEB_DIR, "index.html"), "w").write(
        wrap(body, "Piece-Meal D&amp;D — Character Builder"))

    # Classless builder.
    classless = json.dumps(build_classless(catalog, classes),
                           separators=(",", ":"))
    cbody = inject(os.path.join(WEB_DIR, "classless-app.html"), classless)
    open(os.path.join(WEB_DIR, "classless.html"), "w").write(
        wrap(cbody, "Piece-Meal D&amp;D — Classless Builder"))

    n_feat = len(json.loads(classless)["features"])
    print(f"Built {len(order)} classes -> web/index.html; "
          f"classless menu with {n_feat} features -> web/classless.html")


if __name__ == "__main__":
    main()
