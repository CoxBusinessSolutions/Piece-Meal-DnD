#!/usr/bin/env python3
"""Build the web character-builder from the class YAMLs.

Reuses tools/price.py to compute every piece's price, serializes all 12 classes
to JSON, and injects that JSON into web/app.html (between the DATA markers). Also
wraps app.html in a minimal HTML skeleton to produce web/index.html, a
standalone page you can open directly in a browser.

app.html is body-only so it can double as a hosted artifact; index.html is the
full document for local use. Run this after editing any data/*.yaml:

    python3 tools/build_web.py
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
               "type": r["type"], "xp": r["xp"]}
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


def main():
    catalog = yaml.safe_load(open(os.path.join(DATA_DIR, "level1_catalog.yaml")))
    classes, order = {}, []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.yaml"))):
        if os.path.basename(path) == "level1_catalog.yaml":
            continue
        key, payload = build_class(path, catalog)
        classes[key] = payload
        order.append(key)

    data = {"order": order, "classes": classes}
    payload = json.dumps(data, separators=(",", ":"))

    app_path = os.path.join(WEB_DIR, "app.html")
    app = open(app_path).read()
    new_app = re.sub(r"/\*DATA_START\*/.*?/\*DATA_END\*/",
                     lambda m: "/*DATA_START*/" + payload + "/*DATA_END*/",
                     app, flags=re.S)
    open(app_path, "w").write(new_app)

    skeleton = (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Piece-Meal D&amp;D — Character Builder</title>\n'
        '</head>\n<body>\n' + new_app + '\n</body>\n</html>\n')
    open(os.path.join(WEB_DIR, "index.html"), "w").write(skeleton)

    print(f"Built {len(order)} classes ({len(payload):,} bytes of data) "
          f"-> web/app.html, web/index.html")


if __name__ == "__main__":
    main()
