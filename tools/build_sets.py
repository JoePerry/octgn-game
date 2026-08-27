#!/usr/bin/env python3
"""Generate Epic Battles OCTGN set XML from the authoritative CSV.

The CSV contains one gameplay row per card. Imagefile is used only as an
implementation key and is intentionally NOT emitted as an OCTGN property.
Missing artwork is valid during beta.

Artwork convention:
  <Imagefile>.jpg      base artwork
  <Imagefile>-ai.jpg   alternate artwork
  <Imagefile>-ai2.jpg  second alternate, etc.
"""

import argparse
import csv
import json
import re
import uuid
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

GAME_ID = uuid.UUID("336cc7ef-c808-5f75-a22e-0171564da1e3")
GAME_VERSION = "0.1.0.0"
VISIBLE_PROPERTIES = [
    "Number", "Rarity", "Type", "Attack", "Attack Type",
    "Cost", "Damage", "Link", "Text",
]
ALT_RE = re.compile(r"^(?P<base>.+)-ai(?P<n>\d*)$", re.IGNORECASE)


def clean(value):
    return (value or "").strip()


def card_uuid(set_name, number):
    # Number is the stable gameplay identifier within a set.
    return uuid.uuid5(GAME_ID, "card:{}:{}".format(set_name, number))


def alternate_uuid(base_uuid, image_stem):
    return uuid.uuid5(base_uuid, "alternate:{}".format(image_stem.casefold()))


def indent(elem, level=0):
    pad = "\n" + "  " * level
    child_pad = "\n" + "  " * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_pad
        for child in elem:
            indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = child_pad
        elem[-1].tail = pad
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = pad


def read_cards(csv_path, set_ids):
    cards_by_set = defaultdict(list)
    seen = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Name", "Set", "Imagefile", *VISIBLE_PROPERTIES}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise SystemExit("CSV missing columns: {}".format(", ".join(sorted(missing))))

        for row_index, row in enumerate(reader, start=2):
            set_name = clean(row["Set"])
            number = clean(row["Number"])
            imagefile = clean(row["Imagefile"])
            name = clean(row["Name"])

            if not set_name:
                raise SystemExit("Row {} has no Set".format(row_index))
            if set_name not in set_ids:
                raise SystemExit("Row {} uses unknown set {!r}".format(row_index, set_name))
            if not number:
                raise SystemExit("Row {} has no Number".format(row_index))
            if not imagefile:
                raise SystemExit("Row {} has no Imagefile".format(row_index))

            identity = (set_name.casefold(), number.casefold())
            if identity in seen:
                raise SystemExit("Duplicate Number {!r} in set {!r}".format(number, set_name))
            seen.add(identity)

            cards_by_set[set_name].append({
                "name": name,
                "set": set_name,
                "imagefile": imagefile,
                "guid": str(card_uuid(set_name, number)),
                **{prop: clean(row[prop]) for prop in VISIBLE_PROPERTIES},
            })
    return cards_by_set


def scan_art(images_root):
    """Return case-insensitive stem -> source path for jpg/jpeg/png artwork."""
    artwork = {}
    if images_root is None or not images_root.exists():
        return artwork
    for path in images_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        key = path.stem.casefold()
        if key in artwork:
            raise SystemExit("Duplicate artwork stem: {}".format(path.stem))
        artwork[key] = path
    return artwork


def write_set_xml(output_root, set_name, set_guid, cards, artwork):
    set_dir = output_root / set_guid
    set_dir.mkdir(parents=True, exist_ok=True)
    root = ET.Element("set", {
        "name": set_name,
        "id": set_guid,
        "gameId": str(GAME_ID),
        "gameVersion": GAME_VERSION,
        "version": "1.0",
    })
    cards_node = ET.SubElement(root, "cards")

    for card in cards:
        base = ET.SubElement(cards_node, "card", {"id": card["guid"], "name": card["name"]})
        for prop in VISIBLE_PROPERTIES:
            ET.SubElement(base, "property", {"name": prop, "value": card[prop]})

        base_key = card["imagefile"].casefold()
        alternates = []
        for stem in artwork:
            match = ALT_RE.match(stem)
            if match and match.group("base").casefold() == base_key:
                alternates.append(stem)
        for stem in sorted(alternates):
            alt_guid = str(alternate_uuid(uuid.UUID(card["guid"]), stem))
            # OCTGN alternate card: separate image/card GUID linked to the base card.
            ET.SubElement(cards_node, "card", {
                "id": alt_guid,
                "name": card["name"],
                "alternate": card["guid"],
            })

    indent(root)
    ET.ElementTree(root).write(set_dir / "set.xml", encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--set-ids", type=Path, default=Path("config/set-ids.json"))
    parser.add_argument("--images-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("dist/Sets"))
    args = parser.parse_args()

    set_ids = json.loads(args.set_ids.read_text(encoding="utf-8"))
    cards_by_set = read_cards(args.csv, set_ids)
    artwork = scan_art(args.images_root)

    for set_name, cards in cards_by_set.items():
        write_set_xml(args.output, set_name, set_ids[set_name], cards, artwork)

    total = sum(len(cards) for cards in cards_by_set.values())
    print("Generated {} gameplay cards across {} sets.".format(total, len(cards_by_set)))


if __name__ == "__main__":
    main()
