# Game Quality: What Forge Checks and What Only People Can Judge

Goal: small games that are quick to build, work reliably, and give players a reason to
come back. Profit is not the target; quality is.

## 1. Works (fully automated, blocks release)

| Check | Where | Catches |
|---|---|---|
| format, lint, typecheck, build | `roblox-gate` in the sandbox | broken or sloppy code |
| unit | game's own Lune tests | wrong game rules |
| policy invariants | `policy/<game or _baseline>/tests` (builder cannot edit) | negative cash, overfilled bags, unconserved money, absurd grind, unsafe save sanitizing |
| studio-core | Studio playtest, HEALTH | boot errors, players never loading |
| studio-capture | `policy/.../scenarios/core_loop.json` | core loop broken, pacing checkpoints missed, errors during play |
| studio-edges | `policy/.../scenarios/edge_cases.json` | empty sell, unaffordable upgrade, full bag, respawn losing progress |
| release evidence | `factory/roblox_release.py` | untested commits, footage from another build, tampering |

## 2. Feels right (automated signals, advisory)

- **Pacing checkpoints** (bot timings are a lower bound for real players): first action
  ≤ 15 s, first reward ≤ 60 s, first upgrade ≤ 2 min. Shown on the Telegram card.
- **Economy curve**: every level within a bounded number of full-bag trips.
- Next (not built): a local vision model reviewing screenshots for unreadable text,
  clipped UI and unclear objectives, benchmarked against human-labelled screenshots
  before it is trusted; phone/tablet layouts; a two-player isolation scenario.

## 3. Fun and worth returning to (people only)

No automated check proves fun or retention. These come from people:

- The Telegram review card asks: Is the goal obvious without help? Would you keep
  playing after five minutes? Can you say why you'd come back?
- Before scaling: one novice playtest per game, then basic analytics (onboarding funnel,
  session length, day-1/day-7 return) once a game is public.

## Scope that keeps builds to hours

One place, one core mechanic, one progression axis, one social hook, three stations,
up to five meaningful upgrades, fixed art kit. No trading, procedural worlds, custom
inventory frameworks, cross-place travel, combat, or monetization until a game has
players. Fill in `design/concept.md` (the design contract) before building.
