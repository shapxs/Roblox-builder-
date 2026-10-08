# Roblox Integration Plan

Spec step 2 (section 31). Maps `FORGE_ROBLOX_STUDIO_IMPLEMENTATION.md` onto existing Forge
components. Principle: Roblox is a domain pack for Forge, not a second orchestrator.

## Repository split

| Lives in | Contents |
|---|---|
| `~/Roblox Games` (this repo) | Every game (`games/<id>/`), the template, pinned toolchain (`rokit.toml`), vendored type defs, gate scripts, scenarios, research data, Roblox docs |
| `~/Voya/AutoDevFactory/repo`, branch `feature/roblox-studio-domain` | Forge code: Studio adapter, studio gate type, Telegram media + Roblox commands, release-bound approvals, worker-image tooling |

Forge treats each `games/<id>` as an imported project, the same way it treats the travel
platform today.

## Done (2026-10-07)

- Toolchain pinned via Rokit: Rojo 7.7.1, Wally 0.3.2, StyLua 2.5.2, Selene 0.32.0,
  Lune 0.10.5, luau-lsp 1.70.1. ffmpeg installed for capture.
- `games/_template`: Collect -> Sell -> Upgrade. Strict Luau, server-authoritative
  (ProximityPrompts only, no client remotes), rate-limited actions, DataStore abstraction
  with retry, an in-memory fallback, and save sanitizing.
- `tools/check.sh`: gates R03 format, R04 lint, R05 typecheck, R07 build, R10 unit
  (Lune, headless). All offline. Verified that each gate fails on an injected defect.
- `tools/new_game.sh`: creates an isolated game from the template.
- Roblox Studio 0.736 has the built-in `StudioMCP` proxy (`list_roblox_studios`,
  playtest start/stop, output logs, errors, runtime eval).

## Requirement -> component mapping

| Spec item | Plan |
|---|---|
| Static gates R01–R08 | Add Linux binaries plus `tools/types/*` to `factory-worker` image; gate commands call the `tools/check.sh` steps |
| Unit gates R10–R15 | Lune specs per game (pure modules); Jest-Lua later if needed |
| Studio gates R20–R29 | New `gate_type="studio"`, run by the controller on the host via `RobloxStudioAdapter` (MCP stdio client to `StudioMCP`), resource class `studio_playtest: 1` |
| Scenario DSL (s15) | `qa/scenarios/*.yaml`, executed by the adapter through runtime eval + ProximityPrompt triggering |
| Repair loop (s14) | Reuse `task_retry` / failure signatures; studio gate output becomes repair evidence |
| Visual gates R30–R35 | Fill the existing `models.visual` slot after qualifying a multimodal model; `VisualReviewAdapter` already exists |
| Capture (s16) | ffmpeg avfoundation window capture on the host; failures do not block the candidate |
| Telegram (s17) | Same bot. Add `sendPhoto`/`sendVideo`, `/roblox …` commands, candidate card |
| Immutable approval (s17, AT-005) | Extend `approvals.py` payload with release_id + commit + build hash |
| Publishing (s18) | Open Cloud Place Publishing; API key in Keychain via `keychain.py`; Phase 5 |
| Model stack (s5) | Use Forge's qualified roles, not the spec's list. `qwen3.5:122b` stays unqualified until it passes Forge's probe |
| Research, analytics, portfolio (s8, s19–21) | Phases 4–7, after the MVP loop is frozen with tests |

## Next steps (Phase 1, in order)

1. Create a Forge worktree + branch `feature/roblox-studio-domain` (live checkout untouched).
2. `RobloxStudioAdapter` + unit tests against a fake MCP server; real smoke test (AT-002)
   with Studio open.
3. Studio gate type in `qa/runner.py`, host-executed, with timeout and structured result.
4. Worker image: Roblox static tools, then run `games/_template` gates in the sandbox.
5. Import `games/_template` copy as a Forge project; run one Luau task end to end.
6. Telegram media + candidate card + release-bound approval (AT-004, AT-005).

## Known limits

- Studio must be open, signed in, and on an awake, logged-in Mac session for runtime gates.
- Open Cloud publishes new versions of an existing place. Creating each new experience is
  a one-time manual step in Studio (or keep a pool of pre-created private experiences).
- Game feel, art quality, and whether a game finds players can't be gated
  deterministically. Visual-model scores and your Telegram review cover them.

## Milestones reached (2026-10-08)

- **AT-002 (Studio control): PASS live.** Bridge finds Studio, inspects, starts a
  playtest, reads server state and logs, stops. Also passes through Forge's
  `roblox-studio` gate.
- **AT-003 (repair loop): PASS live.** `scripts/roblox_repair_e2e.py` on branch
  `feature/roblox-studio-domain`; evidence in `evidence/at003-repair-loop-2026-10-08.json`.
  A runtime-only defect (indexing a missing leaderstats child) passed all five static gates
  in the sandbox; the `roblox-studio core` gate failed with
  `ServerScriptService.Server:125: attempt to index nil with 'Value'`; the builder
  (qwen3.8-flash-next:125b-mlx) fixed it on attempt 2; the reviewer (qwen3.8:27b) rejected
  that fix as scope creep (it invented a new bonus rule); attempt 3 made the minimal fix,
  all gates passed, the reviewer accepted, and the controller merged. 21 minutes, audit
  chain intact.
