# Forge Roblox workspace audit — 2026-10-09

## Purpose and scope

Forge is an owner-operated Roblox game studio. The controller plans and reviews work,
builders change isolated game repositories, deterministic gates run before merge, Studio
checks gameplay, and a person approves frozen releases through Telegram. The objective is
small, reliable games that people enjoy and return to, with human approval for publishing.

This audit covers this Git repository (`~/Roblox Games`), its bridge, template, policy,
scripts, documents, and the current ignored `forge-games/` output. It also traces the
connected implementation in `~/Voya/AutoDevFactory-roblox` and the live Forge checkout.
This re-audit did not exercise Studio, Telegram, or Open Cloud. The master file
`FORGE_ROBLOX_STUDIO_IMPLEMENTATION.md` is absent, so this is an implementation audit,
not a compliance audit against that original spec. The June `legacy/` prototype is
reference material; it is not the runtime path.

Current state: the bridge has a fixed MCP operation list, a dedicated local QA place,
strict health checks, controller-owned policy tests/scenarios, release evidence binding,
staging publishing, and four reusable system kits. `capture_demo` was published to private staging on 2026-10-09
([publishing record](PUBLISHING.md)). Batch A–C work is present. The
[builder comparison](evidence/builder-comparison-2026-10-08.md) is one task per model;
1.9 minutes is an encouraging smoke result, not a qualified fleet-wide speed claim.

## Changes made during the initial audit

| Change | Why | Verification |
|---|---|---|
| `tools/new_game.sh` now substitutes placeholders as data and quotes the YAML display name | `sed` treated `&`, `/`, quotes, and backslashes in game names as replacement syntax; an unquoted name with `:` can break YAML | Temporary fixture with `A&B / "Studio": Game`; malformed multiline name rejected before copying |
| `tools/check.sh` requires a policy test file before starting gates | A missing policy test was silently skipped | Temporary fixture with no policy exits nonzero before any gate |
| `policy/_baseline/tests/run.luau` fails when `Economy.luau` is absent | Previously a builder could remove the module and make this baseline test exit successfully | Template baseline passes; missing module fixture exits nonzero |
| `tools/check.sh` now falls back to baseline policy for a publish-only game folder | A publish destination previously hid the required baseline tests in the shell check, disagreeing with Forge's policy resolver | `capture_demo` static/policy/build checks pass |
| Template and both current games reject stale saves | Overlapping autosave, leave, and shutdown requests could finish out of order | Reordered-save and later-lease unit tests; local checks for all three games |

These initial local fixes did not replace the Forge production gates or the live Studio
checks. The subsequent release-path changes are recorded below.

## Deep audit addendum — release-path blockers

This second pass traced the shared `roblox_ship` CLI through Studio execution, candidate
assessment, and approval. It changes the priority of the earlier list: address the
following release-path defects before treating a green card as proof of a fresh run.
No production code was changed in this pass.

1. **P0: a failed bridge command can reuse an earlier PASS report.**
   `src/factory/roblox_ship.py:45-53` discards `subprocess.run`'s return code and reads
   the report path even if this invocation wrote nothing. `:67-87` reuses source,
   capture, and edge-report paths for the same game and 12-character commit prefix.
   In an isolated repro, a bridge return code of 1 with an existing PASS JSON was
   accepted as PASS. With unchanged source, that stale report can retain a matching
   source hash. Use a unique run directory and run ID, require exit code 0, write
   reports atomically, and require the report to name the expected run, operation,
   source hash, and candidate. A failed command must produce a failed diagnostic card
   without reading an earlier report. Add a regression test for a stale PASS after a
   command failure.

2. **P0: the edge-case gate trusts a status string without its scenario evidence.**
   `src/factory/roblox_ship.py:84-95` reduces the edge run to `{name,status}`;
   `src/factory/roblox_release.py:178-208,277-290` binds the capture's source identity
   but fingerprints only the gate status for edges. An isolated call to `assess` with
   a valid capture and `studio-edges: PASS`, but no edge report, produced no rejection
   reason. The shared CLI supplies all required gate names, so this is specifically an
   evidence-verification gap, amplified by the stale-report path above. Archive and
   verify the complete edge report: expected scenario IDs, assertions, source hash,
   run ID, and artifact digest. Make absence or mismatch block approval. Test forged
   PASS, missing scenario, wrong source, and swapped reports.

3. **P0: shared shipping bypasses the Studio lock and recovery protocol.**
   `src/factory/roblox_ship.py:56-97` invokes the bridge directly; the task gates use
   the `GpuSlot` lock and Studio recovery in `src/factory/qa/studio.py:180-249`.
   Concurrent task and shipping runs can therefore operate on the same QA Studio and
   contaminate one another's evidence. The 900-second subprocess timeout also lacks
   local cleanup/recovery handling. Route shipping through the same exclusive Studio
   runner, or acquire the same lock for the whole sync/play/capture sequence. Add a
   concurrency test and a timeout-recovery test.

4. **P1: reused paths are destructively replaced and CLI game names are not
   constrained.** `src/factory/roblox_ship.py:67-73` removes the existing source tree
   for a game/commit before rebuilding it. A concurrent invocation can erase files
   another is using. `scripts/roblox_release.py` accepts `--game` from the CLI, while
   `ship()` does not validate it before composing paths. The Telegram selection path
   limits names to known games, but direct CLI callers need the same constraint and a
   resolved-path containment check. Replace shared scratch directories with unique
   run directories, validate game names, and test concurrent same-commit invocations
   plus traversal-shaped names without touching external paths.

5. **P1: static failure still spends Studio time.** `src/factory/roblox_ship.py:79-96`
   runs both Studio checks after static gates fail, then attempts candidate creation.
   This wastes the scarce Studio slot and can turn a predictable static failure into
   an exception during Rojo build instead of a clear diagnostic card. Stop before
   Studio when required static gates fail, and produce a non-releasable card listing
   those failures. Verify that no Studio command runs in this case.

6. **P2: make the release API safe for callers other than the shared CLI.**
   `src/factory/roblox_release.py:244-245` defaults `required_gates` to whatever
   gate names a caller supplied. The shared `ship()` passes the full required list,
   but a new direct caller can accidentally omit a required gate and receive an
   eligible candidate. Require the policy's full gate set by default, with any
   exception explicit and reviewed. Test an omitted capture/edge gate through the
   public candidate API.

These findings concern evidence freshness and provenance, not a demonstrated malicious
publication. The two false-pass behaviors were reproduced with mocked bridge results
and temporary reports; a live publish was neither attempted nor needed to establish
the code-path defects.

### Fix status after this audit

The six release-path items above are implemented in the isolated
`~/Voya/AutoDevFactory-roblox` worktree and fast-forwarded into the live Forge checkout.
Shipping now uses the task gate's Studio
lock, validation, timeout recovery, and quarantine; each run has unique scratch paths;
unsafe CLI game names fail before file operations; static failures skip Studio and
produce a diagnostic even when Rojo cannot build. Candidate assessment requires the
full edge report, scenario identity and policy-file hash, and the frozen source hash.
The edge report is archived and bound into approval evidence. The default candidate
API requires all seven release gates, simultaneous candidates claim separate release
IDs, and manifest eligibility, gate results, and destinations are checked against
approved evidence. Focused regression tests cover stale PASS, absent edge evidence,
edge-report tampering, unsafe names, failed static builds, and manifest edits.

The game template and both existing game copies now assign an ordered save revision to
each snapshot and a generation to each loaded session. A delayed older save is refused,
and a retry keeps its original revision and generation. Headless tests cover reversed
completion and a later load in the same server. The code changes are merged into the
live Forge checkout but have **not** been validated in live Studio; rerun shipping on
a disposable QA game before relying on
new approval cards. Candidates created under the earlier release evidence policy
should be regenerated under `roblox-release/3`.

## Re-audit of the current build — 2026-10-09

This pass includes the newer system-kit work (`Roblox Games` commit `3dccb72`),
the Forge planner/builder commits through `87b3f08`, and the save/release fixes above.
The three uncommitted atmosphere-kit files were inspected but left untouched. The
following are **new or still-live findings**; they supersede the older ranking where
there is a conflict.

1. **P0: a quick rejoin to the same server can lose the departing player's last
   progress.** `SessionStore.load` accepts a record owned by the same server and
   increments its generation (`games/_template/src/server/SessionStore.luau:42-68`).
   `PlayerRemoving` may still be inside a yielding save while `PlayerAdded` loads the
   same key. The new load returns the older stored snapshot and changes generation;
   the pending release save then gets `lost_session` (`:94-105`). An isolated Lune
   interleaving produced `rejoin_cash=90`, `pending_release=lost_session`, and
   `persisted_cash=90` after the departing state reached 100. The previous fix
   correctly rejects out-of-order writes, but this lifecycle gap remains in the
   template, `capture_demo`, and the generated mushroom game. Serialize loads and
   saves **per player key**, or keep the pending departure snapshot and make a same-
   server rejoin await/consume it before opening a new lease. Test rapid leave/rejoin,
   save retry with unknown outcome, and shutdown interleavings. Roblox's
   [data-store best practices](https://create.roblox.com/docs/cloud-services/data-stores/best-practices)
   explicitly call for ordered per-key retries and caution that a failed response may
   follow a completed write. Do this before treating the save system as release-ready.

2. **P1: reinstalling a kit into a game can write outside that game.**
   `tools/add_kit.sh:30-45` trusts the game-owned `kits.lock.json` and follows a
   destination symlink. In a temporary fixture, a symlink under the game pointed at
   a file outside it; a matching lock digest let `shutil.copy2` overwrite that outside
   file. Forge's automatic new-game path installs before a builder edits the repo,
   which limits the current path. Manual upgrades or reuse on builder-edited repos
   expose the host write. Refuse symlinks in every destination component, validate
   resolved sources and destinations against their roots, and never use a game-owned
   lock as authority to cross the game boundary. Add a symlink and forged-lock test.

3. **P1: a kit conflict leaves a partial installation.** The installer copies files
   one at a time and writes `kits.lock.json` only after every kit (`add_kit.sh:32-45`).
   A temporary fixture with a conflicting second file exited 1 after installing the
   first module, with no lock written. Preflight *all* files for *all* requested kits,
   then stage and atomically replace files and the lock, or roll back on failure.
   Test a conflict late in `--all` and confirm the game tree is unchanged.

4. **P1 before using per-player unlocks: the world helper changes shared state.**
   `kits/unlocks/src/Unlocks.luau:80-101` changes `Transparency` and `CanCollide` on
   Workspace parts based on one `level`. If a server calls it for different players,
   the last call controls the world seen by everyone; if called on one client, the
   server's collision authority can disagree with what that client sees. It also
   restores unannotated parts to transparency 0 and collision true, losing their
   original properties, and rewalks descendants for each tagged ancestor. State the
   kit's intended shared-world or per-player contract, separate visual access from
   server-authoritative interaction, preserve original properties, and test two
   players plus nested tagged models. Roblox's
   [client-server replication guide](https://create.roblox.com/docs/projects/client-server)
   explains why server changes to Workspace affect connected clients.

5. **P1: kit integrity is a prompt rule, not an acceptance gate.**
   Forge's game spec says builders must not edit `src/shared/Kits/*` or
   `tests/unit/Kit_*` (`scripts/roblox_jobs.py:133-140`), but both and the game-owned
   `kits.lock.json` are in the builder-editable repository. The test runner discovers
   whatever `*.spec.luau` files remain; neither `tools/check.sh` nor the controller's
   release policy compares installed files with an owner-controlled kit manifest.
   A builder can change a kit and its test, or remove a kit test, without a deterministic
   kit-integrity failure. In a temporary copy, removing the leaderboard spec still
   produced a green `50 passed, 0 failed` run instead of the original 53 tests.
   Keep a controller-owned expected file map per game/kit version,
   check presence and hashes before merge and release, and make upgrades an explicit
   owner-controlled operation. Test deletion, modification, and a forged game lock.

6. **P2: leaderboard ranks use a non-unique identity.**
   `kits/leaderboard/src/Leaderboard.luau:55-96` records `DisplayName` and
   `rankOf` selects the last matching name. Two players can share a display name,
   so one player's rank can be reported as the other's. Include `UserId` in entries,
   rank by that ID, and use display names only for presentation. Roblox's
   [Player reference](https://create.roblox.com/docs/reference/engine/classes/Player)
   explicitly says display names are not unique.

7. **P2: capture and shipping scratch need a retention rule.** At this pass,
   `artifacts/captures/` contained 52 directories using about 521 MB, all recent;
   shared shipping also keeps a unique frozen source directory for each attempt.
   Keep the copied, hashed release artifacts and gate logs required for review, but
   give unreferenced raw captures and reconstructible source copies a bounded
   age/size policy. Avoid deleting material still referenced by pending approvals.

The kit's six headless suites passed (53 tests), but these do not exercise Roblox
Instance replication or the installer. The symlink, partial-install, kit-test deletion, and rejoin
findings were reproduced only in isolated temporary fixtures; no live player data,
real game files, or outside-home files were changed by those probes.
The current Forge suite passed 880 tests with 71 skips when the 12 localhost-server
Ollama integration tests were excluded; this sandbox cannot bind their test socket.
This re-audit did not run live Studio, Telegram, or Roblox publishing.

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

2. **Test the save-ordering fix live (M).**
   `games/_template/src/server/init.server.luau:156-174` spawns autosaves independently;
   `PlayerRemoving` and `BindToClose` can save the same player concurrently.
   The template and both current games now have ordered revisions and a reversed-
   completion test. Resolve the same-server rejoin race in the re-audit above, then
   exercise leave/rejoin and shutdown in a private staging experience. The new race
   was reproduced headlessly, not as a live player-data loss.

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
    The root README and `HOST_BRIDGE.md` now cover the current layout and bridge
    operations. `docs/roblox/ROBLOX_INTEGRATION_PLAN.md:46-85` still mixes old plans
    with reached milestones, and its final note says the proof uses a custom runner
    despite the newer production-path proof. Archive historical milestones as dated
    history and keep one operator map current. Acceptance: a new maintainer can
    identify the live controller, game repository, policy, QA place, release path,
    and recovery command without reading contradictory instructions.

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

1. Close the same-server save/rejoin race; harden kit installation and enforce kit
   integrity before any kit upgrade on a builder-edited game. Add regressions.
2. Live-test the merged release-path fixes and persistence on a disposable QA game.
3. Define safe per-player unlock and leaderboard identity behavior; test two players.
4. Build and test the exact frozen place in disposable QA; prove staging still uploads
   the identical hash. This is the main release-integrity milestone.
5. Separate universal and mechanic-specific policy, then validate design promises.
6. Add phone/two-player checks and one private DataStore smoke test.
7. Benchmark capture and builders; adopt faster options only with measured quality.
8. Add analytics and calibrated visual review after at least one player-tested game.

## Verification and limits

During this audit: the template's local static checks passed, the baseline invariant
test passed, the deliberately missing-policy/module probes failed as intended, and
scaffolding handled punctuation in a temporary fixture. The bridge tests run only
against a fake MCP server; no live Studio, Telegram, or publishing test was run.
The ignored `forge-games/collect_glowing_mushrooms` is a separate Git repository and
was inspected without changes. Forge implementation findings cite its worktree paths;
changes there require their own review and test pass before entering the live checkout.

The deeper pass also ran 49 bridge tests and 86 focused Forge release, publishing,
Telegram, and Studio-gate tests; all passed. Those suites do not cover the stale-report
and missing-edge-evidence repros above. The Forge worktree and live checkout point at
the same commit at audit time, but the live checkout has local changes, so this audit
did not modify or reconcile it. No live Studio or Open Cloud action was performed.

After the fixes, complete local checks passed for the template and both game copies
(format, lint, sourcemap, typecheck, unit, policy, build). Forge's broad pytest run
passed 868 tests and skipped 71 when the localhost-only Ollama integration module was
excluded; its 12 tests could not set up because this sandbox denies binding a localhost
test server. The focused release suite passed 72 tests. The fixes are recorded as
commits `9b412b8` and `97ed264` (isolated Forge branch), `1616f82` (this workspace),
and `2c8770a` (generated mushroom game). The live Forge checkout was fast-forwarded to `97ed264`;
its unrelated local edits were preserved. No Forge process was restarted.
An AppleScript normal quit was attempted for the earlier Studio restart request, but
Studio returned `User canceled` and remained open. It was not force-quit; live capture,
edge-case, exact-place, phone, and two-player checks remain unverified.
The focused release suite also passed 72 tests from the live checkout after the merge;
Ruff passed on the changed Forge files.
