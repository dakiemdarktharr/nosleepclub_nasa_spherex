"""Refresh the embedded catalogs in the offline sky atlas."""

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs" / "sky-atlas.html"
CATALOGS = {
    "project-data": "sky-project-fields.json",
    "archive-data": "sky-datasets.json",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the atlas has outdated catalogs")
    options = parser.parse_args()
    original = ATLAS.read_text(encoding="utf-8")
    updated = original
    for element_id, filename in CATALOGS.items():
        source = ROOT / "docs" / "data" / filename
        catalog = json.loads(source.read_text(encoding="utf-8"))
        payload = "\n" + json.dumps(catalog, ensure_ascii=False, indent=2).replace("<", "\\u003c") + "\n"
        pattern = rf'(<script type="application/json" id="{element_id}">).*?(</script>)'
        updated, matches = re.subn(pattern, lambda match: match[1] + payload + match[2], updated, flags=re.DOTALL)
        if matches != 1:
            raise SystemExit(f"Expected one catalog element {element_id}, found {matches}")

    if options.check and updated != original:
        raise SystemExit("Embedded catalogs are outdated. Run python scripts/embed_sky_atlas.py.")
    if updated != original:
        ATLAS.write_text(updated, encoding="utf-8", newline="\n")
    print("Sky atlas catalogs match docs/data.")


if __name__ == "__main__":
    main()
