# Forge Roblox workspace audit — 2026-10-09

## Purpose and scope

Forge is an owner-operated Roblox game studio. The controller plans and reviews work,
builders change isolated game repositories, deterministic gates run before merge, Studio
checks gameplay, and a person approves frozen releases through Telegram. The objective is
small, reliable games that people enjoy and return to, with human approval for publishing.

This audit covers this Git repository (`~/Roblox Games`), its bridge, template, policy,
scripts, documents, and the current ignored `forge-games/` output. It also traces the
connected implementation in `~/Voya/AutoDevFactory-roblox` **read-only**. The running
Forge checkout, Studio, Telegram, and Open Cloud were not exercised. The master file
`FORGE_ROBLOX_STUDIO_IMPLEMENTATION.md` is absent, so this is an implementation audit,
not a compliance audit against that original spec. The June `legacy/` prototype is
reference material; it is not the runtime path.

Current state: the bridge has a fixed MCP operation list, a dedicated local QA place,
strict health checks, controller-owned policy tests/scenarios, release evidence binding,
and staging publishing. `capture_demo` was published to private staging on 2026-10-09
([publishing record](PUBLISHING.md)). Batch A–C work is present. The
[builder comparison](evidence/builder-comparison-2026-10-08.md) is one task per model;
1.9 minutes is an encouraging smoke result, not a qualified fleet-wide speed claim.

## Changes made during this audit

| Change | Why | Verification |
|---|---|---|
| `tools/new_game.sh` now substitutes placeholders as data and quotes the YAML display name | `sed` treated `&`, `/`, quotes, and backslashes in game names as replacement syntax; an unquoted name with `:` can break YAML | Temporary fixture with `A&B / "Studio": Game`; malformed multiline name rejected before copying |
| `tools/check.sh` requires a policy test file before starting gates | A missing policy test was silently skipped | Temporary fixture with no policy exits nonzero before any gate |
| `policy/_baseline/tests/run.luau` fails when `Economy.luau` is absent | Previously a builder could remove the module and make this baseline test exit successfully | Template baseline passes; missing module fixture exits nonzero |

These are local fixes. They do not replace the Forge production gates or the live Studio
checks. No files in the Forge checkout were changed.

## Remaining work, ranked

**P0 — before a public game or broad unattended building**

1. **Test the exact candidate place, not a script projection (L).**
   `bridge/src/roblox_bridge/sync.py:13-20,141-185` accepts only scripts/folders,
   rejects some unsupported features, and produces a source hash. Forge compares that
   hash with archived source (`src/factory/roblox_release.py:178-208`). That proves script
   identity, but not full place identity, lighting, assets, terrain, configuration,
   or properties. The local QA place may supply extra objects. Build the frozen place
   once, load those exact bytes into a disposable QA session, test it, and publish those
   bytes. Keep fast sync as an iterative repair check. Acceptance: a property-only or
   asset-only change is either tested faithfully or rejected; a stale QA-place object
   cannot make a broken candidate pass. Roblox's [Rojo sync details](https://rojo.space/docs/v7/sync-details/)
   explain how much more Rojo can represent than this bridge's subset.

2. **Prevent overlapping saves from writing older snapshots (M).**
   `games/_template/src/server/init.server.luau:156-174` spawns autosaves independently;
   `PlayerRemoving` and `BindToClose` can save the same player concurrently.
   `src/server/SessionStore.luau:62-75` checks the session ID, but has no revision
   attached to an in-flight snapshot. An older autosave that commits after a newer one
   can roll back progress while the same server owns the lock. This is a code-path risk,
   not a reproduced live loss. Serialize per-player saves or assign increasing snapshot
   revisions and refuse older writes inside `UpdateAsync`. Add a test that controls
   completion order: autosave A starts, gameplay changes, save B commits, A finishes;
   stored data must equal B. Cover leave and shutdown races too.

3. **Split universal acceptance from the template economy policy (M).**
   `policy/_baseline/tests/run.luau:9-15` loads one `Economy.luau` API and the baseline
   scenarios require `Collect`, `Sell`, `Upgrade`, and `MainHUD`. The generated
   [Glowcap Grove spec](../../forge-games/specs/collect_glowing_mushrooms.md) inherits
   that shape. This makes every idea a reskinned collect/sell/upgrade game and limits
   the quality goal. Keep universal gates for load, errors, save safety, input abuse,
   release integrity, and video. Add declared mechanic-specific packs (for example
   collection, obstacle course, puzzle) plus game-specific assertions generated from a
   reviewed design. The controller must reject a missing pack; never silently skip it.
   Acceptance: a non-economy game can pass on its own invariant/scenario pack, while
   removing the chosen pack blocks release.

4. **Make the design contract an enforced input (M).**
   `games/_template/design/concept.md:1-59` has sensible sections, but a new game
   inherits template answers, including its explicit lack of qualitative progression.
   `games/_template/forge_game.yaml:1` says the manifest is not wired. Forge's
   `scripts/roblox_jobs.py:225-280` drafts a new concept, but there is no demonstrated
   check that each promised progression/social/return feature appears in gameplay.
   Add a schema for core loop, first-session milestones, qualitative change, social
   behavior, return reason, exclusions, and matching acceptance scenarios. Reject blank
   or template-copy fields, and require owner review for subjective claims. Acceptance:
   a design promising a level-5 mechanic cannot be called complete based only on the
   template's economy and HUD.

**P1 — reliability and efficiency**

5. **Harden bridge queue semantics if `serve` is used (M).**
   `bridge/src/roblox_bridge/jobs.py:225-253` reads files in place and writes results
   named by the input stem. It has no exclusive claim before execution, no uniqueness
   guarantee for `job_id`, and only catches a narrow set of exceptions. Two workers or
   a crash between running a job and moving it to `done/` can repeat a Studio action or
   overwrite evidence. Verify whether any production caller uses `serve`; the Forge
   Studio gate currently invokes the CLI directly. If queue mode is retained, atomically
   claim jobs, keep a durable state/attempt record, reject duplicate IDs, recover stale
   claims, and add crash/parallel-worker tests. Otherwise remove or mark `serve` as a
   development-only interface.

6. **Bound capture work and decouple video from scenario timing (M).**
   `bridge/src/roblox_bridge/scenario.py:152-199,281-354` captures over a second MCP
   connection while interactions run. It handles a wedged screenshot tool, but footage
   is sparse and a capture timeout can consume 15 seconds. Benchmark Studio MCP
   screenshots against macOS [ScreenCaptureKit](https://developer.apple.com/documentation/screencapturekit)
   on the M3 Ultra. Record real frame timestamps, frame drops, CPU/GPU cost, and whether
   recording changes checkpoint times. Retain deterministic named screenshots even if
   continuous recording wins. Acceptance: release footage is real-time, legible, and
   represents the same run; gameplay timing is measured without recorder contention.

7. **Run mobile and multiplayer acceptance (M/L).**
   `bridge/src/roblox_bridge/scenario.py:203-260` drives one keyboard client and reads
   the first player. That cannot establish touch controls, HUD fit, player isolation,
   social behavior, or join/leave effects. Add a phone portrait/landscape UI pass and
   two-client scenario using Roblox's documented `StudioDeviceSimulatorService`,
   `StudioTestService`, and `VirtualInput` where the current MCP supports them. Check
   whether the published experience also needs a private-device smoke test.
   [Studio testing modes](https://create.roblox.com/docs/studio/testing-modes) describe
   these services. Acceptance: player A's earnings never alter B's, both see expected
   visuals, and the goal/UI is usable on a small phone.

8. **Add a staged persistence exercise and migration policy (M).**
   `games/_template/src/server/PlayerData.luau:16-40` uses `PlayerData_v2`; Studio uses
   memory storage. The seven fault-injected tests cover logic but cannot certify Roblox
   DataStore budgets, shutdown timing, or old `v1` profiles. Before moving an existing
   game to this template, decide whether data migration is needed. Use a private staging
   experience and test join/save/rejoin, contested sessions, throttling, and shutdown.
   Acceptance: old players retain progress or a documented reset is approved; errors
   are observable without risking production data.

9. **Qualify model changes with a representative benchmark (M).**
   The one-run [comparison](evidence/builder-comparison-2026-10-08.md) shows the coder
   model fixed the nil bug cleanly in 1.9 minutes; the 125B builder exhausted repairs.
   Use 20–30 varied tasks at minimum (30–50 preferred), including UI, save behavior,
   Luau types, mechanic work, and adverse prompts. Hold gates/reviewer constant, record
   model digest and quantization, time to accepted fix, pass rate, reviewer reversals,
   and p50/p95 duration. Only then select a live builder. Do not infer a general speed
   ratio from one run.

10. **Add player analytics once a game has players (M).**
    `docs/roblox/GAME_QUALITY.md:27-32` correctly leaves fun to people, but the
    production measurement loop is still a plan. Instrument join → first action →
    first reward → first upgrade → return, then compare cohorts with enough sample
    size. Roblox's [funnel events](https://create.roblox.com/docs/production/analytics/funnel-events)
    require server-side events in published games and do not work in Studio. Use
    [retention analytics](https://create.roblox.com/docs/production/analytics/retention)
    for day-1/day-7 return. Acceptance: the owner sees where players leave and can
    identify whether a change improved the next cohort; do not turn tiny samples into
    automated release decisions.

**P2 — clarity and extension**

11. **Refresh the operator documentation (S).**
    `README.md:1-28` still says to add the missing master spec and omits `policy/`,
    `qa-place/`, `forge-games/`, and publishing. `docs/roblox/HOST_BRIDGE.md:15-54`
    still lists only the original bridge ops and says screenshot/navigation tools are
    unused. `docs/roblox/ROBLOX_INTEGRATION_PLAN.md:46-85` mixes old plans with reached
    milestones, and its final note says the proof uses a custom runner despite the
    newer production-path proof. Write one current operator map; archive historical
    milestones as dated history. Acceptance: a new maintainer can identify the live
    controller, game repository, policy, QA place, release path, and recovery command
    without reading contradictory instructions.

12. **Avoid treating a readable screenshot as a vision verdict (M).**
    The planned local vision review should compare full screen and HUD crops across
    device sizes. Return frame/time, specific defect, severity, and confidence; keep
    human review decisive. Benchmark against a labelled set of actual Roblox captures
    before making it a gate. Candidate defects: clipped UI, low contrast, unreadable
    text, hidden objectives, missing reward feedback, and obstructed interaction.

13. **Use engine tests where pure Lune tests cannot reach (M).**
    Lune is effective for `Economy` and `SessionStore`, but it does not cover replicated
    attributes, UI lifecycle, or actual DataStore behavior. Pilot
    [Jest Roblox](https://github.com/Roblox/jest-roblox) on a small engine-dependent
    module. Roblox also maintains [rocale-cli](https://github.com/Roblox/rocale-cli)
    for Open Cloud Luau execution; assess its permission and latency costs before
    relying on it. Preserve local Studio gameplay as the final client evidence.

## Suggested implementation order

1. Fix save ordering and add the adversarial save test.
2. Build and test the exact frozen place in disposable QA; prove staging still uploads
   the identical hash. This is the main release-integrity milestone.
3. Separate universal and mechanic-specific policy, then validate design promises.
4. Add phone/two-player checks and one private DataStore smoke test.
5. Benchmark capture and builders; adopt faster options only with measured quality.
6. Add analytics and calibrated visual review after at least one player-tested game.

## Verification and limits

During this audit: the template's local static checks passed, the baseline invariant
test passed, the deliberately missing-policy/module probes failed as intended, and
scaffolding handled punctuation in a temporary fixture. The bridge tests run only
against a fake MCP server; no live Studio, Telegram, or publishing test was run.
The ignored `forge-games/collect_glowing_mushrooms` is a separate Git repository and
was inspected without changes. Forge implementation findings cite its worktree paths;
changes there require their own review and test pass before entering the live checkout.
