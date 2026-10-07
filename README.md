# Roblox Games — Forge Roblox Studio

Workspace for every Roblox game Forge builds. Forge itself lives in
`~/Voya/AutoDevFactory/repo`; see [docs/roblox/ROBLOX_INTEGRATION_PLAN.md](docs/roblox/ROBLOX_INTEGRATION_PLAN.md).

## Layout

```text
FORGE_ROBLOX_STUDIO_IMPLEMENTATION.md  master spec (add here)
rokit.toml          pinned toolchain (rojo, wally, stylua, selene, lune, luau-lsp)
games/_template/    Collect -> Sell -> Upgrade starter game
games/<id>/         one isolated project per game
tools/check.sh      static gates for one game
tools/new_game.sh   create a game from the template
tools/types/        vendored Roblox type definitions (offline gates)
docs/roblox/        integration map and plan
legacy/             June 2026 night-agent prototype (reference only)
```

## Commands

```bash
rokit install                                  # once per machine
tools/new_game.sh my_game "My Game"            # new project
tools/check.sh games/my_game                   # format, lint, typecheck, unit, build
rojo serve games/my_game/default.project.json  # live-sync into Studio (Rojo plugin)
```
