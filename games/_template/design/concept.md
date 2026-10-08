# __GAME_NAME__ — Design Contract

Every Forge game fills in every section before building. Short answers are fine; blank
ones are not. Forge's planner turns this file into tasks, and the Acceptance section
into scenarios and checks. See docs/roblox/GAME_QUALITY.md.

(Answers below are for the starter template: Collect → Sell → Upgrade.)

## Player promise
What enjoyable experience does the player get, in one sentence?
> Watch a small effort snowball: every trip earns more than the last.

## Core loop
Action → feedback → reward → meaningful choice.
> Collect at the yellow pad (bag fills, HUD counts up) → sell at the green pad (cash jumps)
> → choose: upgrade the bag now, or save for a bigger upgrade.

## Session loop
First success → first upgrade → new challenge → satisfying stopping point.
> First collect within 15 s; first sale within 60 s; first upgrade within 2 min;
> stopping point: the next upgrade is visibly close.

## Progression
What changes besides bigger numbers?
> Template: only capacity grows. A real game must add at least one qualitative change
> (new area, new tool behaviour, new resource) by level 5.

## Social hook
One useful shared activity or comparison.
> Template: leaderboard cash only. A real game needs one reason to play near others.

## Return reason
A saved goal, mastery challenge, or new variation.
> Progress is saved (session-locked); the next upgrade cost is shown on the HUD.

## Pacing targets
| Moment | Target | Enforced by |
|---|---|---|
| First successful action | ≤ 15 s | policy scenario checkpoint `first_action` |
| First currency reward | ≤ 60 s | checkpoint `first_reward` |
| First meaningful upgrade | ≤ 2 min | checkpoint `first_upgrade` |
| Any later level | ≤ 15 full-bag trips (game), ≤ 25 (policy) | unit + policy invariant tests |

## Scope
- Allowed: one place, one core mechanic, one progression axis, one social hook, three
  stations, up to five meaningful upgrades, primitive parts + a fixed art kit.
- Excluded: trading, procedural worlds, custom inventory frameworks, cross-place travel,
  monetization (until a game has players), combat.
- Time box: playable slice 60–90 min, release candidate ≤ 4 h, repairs ≤ 3 attempts per gate.

## Acceptance
- Static gates: format, lint, typecheck, unit, policy invariants, build.
- Studio: `core` (boots clean), `capture` (core_loop scenario + pacing), `edges` (empty
  sell, unaffordable upgrade, full bag, respawn keeps progress); zero runtime errors.
- Human review questions (Telegram card): Is the goal obvious without help? Would you keep
  playing after five minutes? Can you say why you'd come back?

## Known risks / kill criteria
> Template: no qualitative progression yet, so it will feel repetitive past level 3.
