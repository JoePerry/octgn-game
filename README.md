# Epic Battles CCG for OCTGN

Independent OCTGN implementation of Epic Battles CCG.

## Beta status
This branch is being built for playtesting. Cards may exist before their artwork is complete. Missing artwork is expected and should use the proxy/card-back fallback rather than blocking the card database.

## Source data
The project owner's current Epic Battles CSV is authoritative. Gameplay-facing OCTGN properties are:

- Number
- Rarity
- Type
- Attack
- Attack Type
- Cost
- Damage
- Link
- Text

`Imagefile` is implementation-only and is not exposed in the Deck Editor.

## Artwork naming
- `<Imagefile>.jpg` = base artwork
- `<Imagefile>-ai.jpg` = alternate artwork
- `<Imagefile>-ai2.jpg`, `<Imagefile>-ai3.jpg`, etc. = additional alternate artwork

The generator maps alternate artwork to an OCTGN alternate-card entry linked to the base gameplay card.

## Generate set XML

```bash
python tools/build_sets.py path/to/EpicBattlesCards.csv --images-root path/to/images
```

Generated sets are written under `dist/Sets/<set-guid>/set.xml` using stable UUIDs from `config/set-ids.json`.

## Repository boundary
`JoePerry/Ranma` is read-only reference material only. This project uses its own game ID, set IDs, card IDs, manifests, release files, and branches.
