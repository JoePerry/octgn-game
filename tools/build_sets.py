#!/usr/bin/env python3
"""Generate Epic Battles OCTGN set XML from authoritative beta CSV files.

The CSV contains one gameplay row per card. Imagefile is used only as an
implementation key and is intentionally NOT emitted as an OCTGN property.
Missing artwork and incomplete beta metadata are valid during playtesting.

Artwork convention:
  <Imagefile>.jpg      base artwork
  <Imagefile>-ai.jpg   alternate artwork
  <Imagefile>-ai2.jpg  second alternate, etc.

Alternate identities may also be declared in config/alternate-art.json so the
OCTGN alternate card GUID remains stable before the binary art is published.

Important OCTGN compatibility note:
  OCTGN reserves the property name "Type", so CSV column "Type" is emitted
  as the visible OCTGN property "Card Type".
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
PROPERTY_MAP = [
    ("Number", "Number"),
    ("Rarity", "Rarity"),
    ("Card Type", "Type"),
    ("Attack", "Attack"),
    ("Attack Type", "Attack Type"),
    ("Cost", "Cost"),
    ("Damage", "Damage"),
    ("Link", "Link"),
    ("Text", "Text"),
]
ALT_RE = re.compile(r"^(?P<base>.+)-ai(?P<n>\d*)$", re.IGNORECASE)


def clean(value):
    return (value or "").strip()


def card_uuid(set_name, number):
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
    seen_numbers = set()
    seen_imagefiles = set()
    warnings = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Name", "Set", "Imagefile"}
        required.update(source for _, source in PROPERTY_MAP)
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
            if identity in seen_numbers:
                raise SystemExit("Duplicate Number {!r} in set {!r}".format(number, set_name))
            seen_numbers.add(identity)

            image_key = imagefile.casefold()
            if image_key in seen_imagefiles:
                raise SystemExit("Duplicate Imagefile {!r}".format(imagefile))
            seen_imagefiles.add(image_key)

            if not name:
                warnings.append("Row {} ({}/{}) has no card name yet".format(row_index, set_name, number))

            properties = {}
            for output_name, source_name in PROPERTY_MAP:
                properties[output_name] = clean(row[source_name])

            cards_by_set[set_name].append({
                "name": name,
                "set": set_name,
                "imagefile": imagefile,
                "guid": str(card_uuid(set_name, number)),
                "properties": properties,
            })

    return cards_by_set, warnings


def scan_art(images_root):
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


def load_declared_alternates(path):
    by_base = defaultdict(set)
    if path is None or not path.exists():
        return by_base
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data.get("alternates", []):
        base = clean(item.get("baseImagefile")).casefold()
        alt = clean(item.get("alternateImagefile"))
        if not base or not alt:
            raise SystemExit("Invalid alternate-art entry in {}".format(path))
        match = ALT_RE.match(alt)
        if not match or match.group("base").casefold() != base:
            raise SystemExit("Alternate {!r} does not match base {!r}".format(alt, item.get("baseImagefile")))
        by_base[base].add(alt)
    return by_base


def alternates_for_card(card, artwork, declared_alternates):
    base_key = card["imagefile"].casefold()
    stems = set(declared_alternates.get(base_key, set()))
    for stem in artwork:
        match = ALT_RE.match(stem)
        if match and match.group("base").casefold() == base_key:
            stems.add(stem)
    return sorted(stems, key=str.casefold)


def write_set_xml(output_root, set_name, set_guid, cards, artwork, declared_alternates):
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
        for prop_name, prop_value in card["properties"].items():
            ET.SubElement(base, "property", {"name": prop_name, "value": prop_value})

        for stem in alternates_for_card(card, artwork, declared_alternates):
            alt_guid = str(alternate_uuid(uuid.UUID(card["guid"]), stem))
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
    parser.add_argument("--alternate-art", type=Path, default=Path("config/alternate-art.json"))
    parser.add_argument("--images-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("dist/Sets"))
    args = parser.parse_args()

    set_ids = json.loads(args.set_ids.read_text(encoding="utf-8"))
    cards_by_set, warnings = read_cards(args.csv, set_ids)
    artwork = scan_art(args.images_root)
    declared_alternates = load_declared_alternates(args.alternate_art)

    for set_name, cards in cards_by_set.items():
        write_set_xml(
            args.output,
            set_name,
            set_ids[set_name],
            cards,
            artwork,
            declared_alternates,
        )

    total = sum(len(cards) for cards in cards_by_set.values())
    alternate_count = sum(
        len(alternates_for_card(card, artwork, declared_alternates))
        for cards in cards_by_set.values()
        for card in cards
    )
    print("Generated {} gameplay cards across {} sets.".format(total, len(cards_by_set)))
    print("Generated {} alternate card identities.".format(alternate_count))
    if artwork:
        print("Scanned {} artwork files for base/alternate image mapping.".format(len(artwork)))
    for warning in warnings:
        print("WARNING: {}".format(warning))


if __name__ == "__main__":
    main()
