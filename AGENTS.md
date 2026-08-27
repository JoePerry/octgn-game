# Epic Battles OCTGN repository instructions

This repository is the independent Epic Battles CCG OCTGN implementation.

## Hard safety boundary
- NEVER modify the JoePerry/Ranma repository.
- Ranma may be inspected only as a read-only structural reference for proven OCTGN conventions.
- Never reuse Ranma game IDs, set IDs, card IDs, release metadata, manifests, branches, or project-specific card data.

## Authoritative data
- The current Epic Battles card CSV supplied by the project owner is authoritative for card data.
- Do not invent missing card names, rules text, rarities, stats, or other gameplay values.
- `Number` is a gameplay/search property and belongs in OCTGN card properties.
- `Imagefile` is implementation-only metadata for artwork lookup and MUST NOT be exposed as a gameplay property or Deck Editor column.

## Beta artwork rules
- Missing artwork is allowed during beta/playtesting and must not prevent a card from existing in the OCTGN database.
- Base art naming: `<Imagefile>.jpg` (case-insensitive matching during import).
- Alternate art naming: `<Imagefile>-ai.jpg`.
- Additional alternates may use `<Imagefile>-ai2.jpg`, `<Imagefile>-ai3.jpg`, etc.
- Alternate artwork must map to the same gameplay card identity using OCTGN alternate-card support; do not create duplicate gameplay records in the source CSV.

## Stability
- Generate stable deterministic UUIDs for the game, sets, cards, and alternate-art entries.
- Do not change an existing card UUID merely because artwork or beta card text is updated.
- Keep all property definitions synchronized with generated set XML to avoid OCTGN Deck Editor serialization failures.
