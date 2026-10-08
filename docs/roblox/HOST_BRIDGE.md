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

## Status (2026-10-08)

- Verified live: the MCP handshake with Studio 0.736's `StudioMCP`, and
  `list_roblox_studios`. Studio's own playtest and code tools only show up once a Studio
  session is connected.
- Not yet verified: the names and arguments of the playtest, log and code tools. They are
  candidates (`ops.py` `CANDIDATES`) taken from Roblox's published MCP servers. A missing
  tool returns `UNSUPPORTED` with the real tool list; the bridge never guesses further.
  Once Studio is open, `roblox-bridge tools` gives the ground truth for fixing the mapping.
