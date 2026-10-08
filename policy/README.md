# Controller-owned acceptance policy

Forge's own tests and Studio scenarios. Lives outside every game repo, so a builder
working in a game's worktree can never edit or weaken them.

- `<game_id>/` overrides for one game; `_baseline/` applies to any game without one.
- `tests/run.luau`: Lune invariant tests. Mounted read-only at `/policy` in the sandbox
  and run by `roblox-gate unit` after the game's own tests (`GAME_ROOT` = the game).
- `scenarios/*.json`: Studio scenarios for `roblox-studio capture|edges`.

Changing a file here changes what every build must pass: review it like a gate change.
