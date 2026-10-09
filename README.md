# Roblox Games — Forge Roblox Studio

Workspace for Roblox game templates, controller-owned policy, the Studio bridge,
the dedicated QA place, and generated games. The live Forge checkout is
`~/Voya/AutoDevFactory/repo`; the isolated Roblox development worktree is
`~/Voya/AutoDevFactory-roblox`.

Current audit and prioritized handoff: [docs/roblox/PROJECT_AUDIT_2026-10-09.md](docs/roblox/PROJECT_AUDIT_2026-10-09.md).

## Layout

```text
rokit.toml          pinned toolchain (rojo, wally, stylua, selene, lune, luau-lsp)
games/_template/    Collect -> Sell -> Upgrade starter game
games/<id>/         one isolated project per game
forge-games/        generated game repositories and specs (ignored by this repo)
policy/             acceptance tests, scenarios, and publish destinations
qa-place/           source for the dedicated QA Studio place
ForgeQA.rbxl        local QA place file
artifacts/          local output and release scratch files
tools/check.sh      static gates for one game
tools/new_game.sh   create a game from the template
tools/types/        vendored Roblox type definitions (offline gates)
bridge/             host-side Studio MCP bridge (docs/roblox/HOST_BRIDGE.md)
docs/roblox/        operator notes, quality criteria, and current audit
legacy/             June 2026 night-agent prototype (reference only)
```

## Commands

```bash
rokit install                                  # once per machine
tools/new_game.sh my_game "My Game"            # new project
tools/check.sh games/my_game                   # static, unit, policy, build checks
rojo serve games/my_game/default.project.json  # live-sync into Studio (Rojo plugin)
```

Release cards and staging publish are driven by Forge's `scripts/roblox_release.py`
from the isolated worktree. See [PUBLISHING.md](docs/roblox/PUBLISHING.md) for the
publish record and [HOST_BRIDGE.md](docs/roblox/HOST_BRIDGE.md) for Studio control.
The original `FORGE_ROBLOX_STUDIO_IMPLEMENTATION.md` master spec is not in this workspace.
