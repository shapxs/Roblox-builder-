# Existing Forge Integration Map

Read-only audit of the live Forge system, 2026-10-07. Spec step 1 (section 31).

## Where Forge lives

| What | Path |
|---|---|
| Source (git, branch main, live) | `~/Voya/AutoDevFactory/repo` (`src/factory/`, ~15k lines Python 3.12) |
| Runtime config | `~/Library/Application Support/AutonomousLocalDevFactory/config.yaml` |
| Authoritative state | same folder, `factory.db` (SQLite) |
| Service | launchd `com.local.autonomousdevfactory.controller` (`python -m factory controller-run`) |
| Imported projects | `~/Voya/AutoDevFactory/projects/` (currently `travel-platform`, `travel-platform-v1-1`) |

Forge is running right now. Do not modify the live checkout; build Roblox support in a
separate git worktree on `feature/roblox-studio-domain`.

Other folders named forge (`~/forge`, `~/FORGE 1.0`, `~/AutoDevFactory ` with a trailing
space, and the old June prototype now in `legacy/forge-night-agent-2026-06`) are not the
live system.

## Component map

| Spec concept | Existing Forge component | Notes |
|---|---|---|
| Orchestration entry | `controller.py`, `dispatcher.py`, `cli.py controller-run` | Single controller lease |
| Task model | `schemas/task.py` TaskPacket | allowed/forbidden paths, `required_gates`, risk, stop conditions |
| Task DAG | `task_graph.py`, `decomposition.py`, `spec_planner.py` | Spec -> phases -> tasks |
| State machine | `state_machine.py` | Crash-safe reconciliation |
| Build harness | `harnesses/native.py` (Ollama), `executor.py` | One git worktree per task |
| Sandbox | `connectors/container.py`, Docker `factory-worker:1.0` | `--network none`, read-only, 8 CPU, 16 GB |
| Gates | `qa/runner.py` GateSpec/GateRunner | A gate is a single shell-free command run **inside the sandbox** |
| Repair loop | `task_retry.py`, `plan_repair.py`, `task_doctor.py`, `diagnostics.py` | Failure signatures, retry ceilings |
| Review | `adapters.py` ReviewerAdapter, VisualReviewAdapter | Visual model currently `null` |
| Escalation | `adapters.py` EscalationAdapter, `claude_escalation.py` | Claude Code escalation, Telegram-approved, $10/day cap |
| Model routing | `config.py` models section | builder `qwen3.8-flash-next:125b-mlx`, architect `qwen3.8:27b`, escalation Qwen3.8-27B Q8; `qwen3.5:122b` marked UNQUALIFIED_TIMEOUT |
| Resource classes | `config.py` scheduler, `resources.py`, `gpu_lock.py` | heavy inference 1, implementation 1, tests 2, visual 1 |
| Telegram | `connectors/telegram.py`, `telegram_assistant.py`, `pairing.py`, `notifications.py`, `digest.py` | Bot `@Forgevoyabot`, paired to one owner, one shared update cursor |
| Approvals | `approvals.py`, `approval_inbox.py`, `scope_approval.py` | Integrity-protected, expiring, replay-safe |
| Secrets | `connectors/keychain.py` | Named Keychain entries only |
| Audit / telemetry | `audit.py` (hash chain), `logging_setup.py`, `live.py` | |
| Backups | `backup.py` | hourly/daily/weekly |
| Tests | `tests/{unit,integration,resilience,security}` | pytest + hypothesis |

## Constraints that shape the Roblox design

1. **Gates run in a no-network Linux container.** Static Roblox gates (StyLua, Selene,
   luau-lsp, Lune, Rojo) can run there once their Linux binaries and the vendored type
   definitions are in the worker image. **Roblox Studio cannot run there.** Studio
   playtests need a new controller-owned, host-side gate type.
2. **One implementation task at a time.** Roblox tasks share the single builder slot with
   whatever else Forge is building (currently the travel platform).
3. **Telegram uses one update cursor.** A second bot polling separately would be a second
   control plane. Roblox should use the same bot and inbox.
4. **Telegram connector sends text only.** Sending preview videos and screenshots needs
   `sendVideo` / `sendPhoto` added to `connectors/telegram.py`.
5. **Frontier API endpoints are rejected by config.** Model calls stay local, except the
   existing approval-gated Claude escalation.
