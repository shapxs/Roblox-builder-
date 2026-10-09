# System kits

Pre-built, tested Luau systems that Forge installs into every new game, so builders
adapt and connect them instead of writing common systems from scratch (the idea behind
SuperBullet's template library, kept in-house so every file has a known source).

Each kit: `src/` module (installed to `src/shared/Kits/`), `tests/` Lune specs (installed
to `tests/unit/Kit_*.spec.luau`), `kit.json` (install map + API summary), `README.md`.
`catalog.json` lists every kit for the planner.

Install into a game: `tools/add_kit.sh games/<id> <kit> [<kit> ...]` or `--all`.

Rules for kits: strict Luau; pure logic separated from Roblox calls so it is tested
headless; Roblox services touched only inside functions; no assets without provenance;
a kit change must keep every game that uses it passing its gates.
