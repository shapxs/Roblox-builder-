# Forge Roblox Host Bridge

A host-side program that is the only path from Forge to Roblox Studio. Forge's Docker
sandbox stays network-free and unchanged.

```text
Forge controller (host)  ──job JSON──▶  bridge  ──MCP stdio──▶  StudioMCP  ──▶  Roblox Studio
                         ◀─result JSON─          ◀──────────────
```

The builder model never talks to the bridge. The Forge controller, which already runs on
the host, submits jobs when a task's Studio gate runs. That keeps Studio control out of the
model's hands entirely.

## Safety properties

- Jobs name operations from a fixed list: `LIST_STUDIOS`, `LIST_TOOLS`, `INSPECT`,
  `START_PLAYTEST`, `PROBE`, `GET_LOGS`, `STOP_PLAYTEST`. Jobs cannot supply tool names
  or Luau. Every snippet that reaches Studio is a constant in `ops.py`.
- Unknown job keys, unknown ops, bad ids, and oversized timeouts are rejected.
- Every MCP call has a hard timeout. A playtest that was started is always stopped,
  even after a failure.
- `dry_run` resolves tools and arguments without calling Studio.
- With several Studios open, a job must name its `studio_id`. The bridge adds it to every
  tool whose schema accepts one.
- The bridge has no third-party dependencies (stdlib only).

## Usage

```bash
cd ~/Roblox\ Games/bridge
.venv/bin/roblox-bridge tools          # real tool names + params (Studio must be open)
.venv/bin/roblox-bridge at002          # acceptance test AT-002
.venv/bin/roblox-bridge serve ../queue # process queue/jobs/*.json -> queue/results/
.venv/bin/pytest -q                    # tests against a fake MCP server
```

## Status

AT-002 passed live on 2026-10-08 against Studio 0.742 ("Forge Experience", placeId
104663411813641): LIST_STUDIOS 3.0 s, INSPECT, START_PLAYTEST 6.6 s (server reports
1 player), PROBE, GET_LOGS, STOP_PLAYTEST. ~11 s end to end.

Live facts the bridge depends on:
- Studio registers with a fresh `StudioMCP` proxy ~3 s after it starts; LIST_STUDIOS
  polls for up to 10 s.
- Tools used: `list_roblox_studios`, `get_studio_state`, `start_stop_play {is_start}`,
  `get_console_output`, `execute_luau {code, datamodel_type: Edit|Server|Client}`.
- `start_stop_play` returns before the server has a player; START_PLAYTEST polls the
  Server DataModel until one joins (45 s cap).
- Also offered and not yet used: `screen_capture`, `character_navigation`,
  `user_mouse_input`, `user_keyboard_input`, `search_game_tree`, `inspect_instance`,
  `script_read`, `multi_edit`. Asset generation/insertion and `http_get` are deliberately
  not exposed.
