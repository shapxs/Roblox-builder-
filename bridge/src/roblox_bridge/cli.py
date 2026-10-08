"""roblox-bridge CLI.

  roblox-bridge tools                   list Studio MCP tools and their parameters
  roblox-bridge op <OP> [--studio ID]   run one whitelisted op
  roblox-bridge at002 [--dry-run]       run the AT-002 acceptance sequence
  roblox-bridge check <name> --project DIR   run a named check (core, capture, at002)
  roblox-bridge recover --studio-name N stop any playtest and confirm Edit mode
  roblox-bridge serve <queue-dir>       process <dir>/jobs/*.json forever
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

from roblox_bridge.jobs import CHECKS, _pick_studio, parse_job, run_job, serve
from roblox_bridge.mcp_client import McpClient
from roblox_bridge.ops import Bridge, Op


RECOVER_SECONDS = 60.0


def _terminate(signum, frame):  # noqa: ARG001
    # SystemExit unwinds through run_job's finally, which stops any running playtest.
    sys.exit(128 + signum)


def main(argv: list[str] | None = None) -> int:
    signal.signal(signal.SIGTERM, _terminate)
    ap = argparse.ArgumentParser(prog="roblox-bridge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools")
    p_op = sub.add_parser("op")
    p_op.add_argument("op", choices=[o.value for o in Op])
    p_op.add_argument("--studio")
    p_op.add_argument("--dry-run", action="store_true")
    p_at = sub.add_parser("at002")
    p_at.add_argument("--studio")
    p_at.add_argument("--studio-name", help="require the Studio whose title contains this")
    p_at.add_argument("--dry-run", action="store_true")
    p_at.add_argument("--out", type=Path)
    p_check = sub.add_parser("check")
    p_check.add_argument("name", choices=sorted(CHECKS))
    p_check.add_argument("--project")
    p_check.add_argument("--scenario", default="core_loop")
    p_check.add_argument("--studio")
    p_check.add_argument("--studio-name", help="require the Studio whose title contains this")
    p_check.add_argument("--dry-run", action="store_true")
    p_check.add_argument("--out", type=Path)
    p_rec = sub.add_parser("recover")
    p_rec.add_argument("--studio-name")
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("root", type=Path)
    args = ap.parse_args(argv)

    if args.cmd == "serve":
        serve(args.root)
        return 0
    if args.cmd == "recover":
        return recover(args.studio_name)
    if args.cmd == "tools":
        with McpClient() as client:
            for t in client.list_tools():
                print(f"{t.name}\n  params: {json.dumps(t.input_schema.get('properties', {}))}"
                      f"\n  {t.description[:300]}")
        return 0
    if args.cmd == "op":
        with McpClient() as client:
            res = Bridge(client, studio_id=args.studio, dry_run=args.dry_run).run(args.op)
        print(json.dumps(res.to_dict(), indent=2, default=str))
        return 0 if res.ok else 1
    name = "at002" if args.cmd == "at002" else args.name
    job = parse_job({"job_id": name, "ops": [o.value for o in CHECKS[name]],
                     "studio_id": args.studio, "dry_run": args.dry_run,
                     "studio_name": getattr(args, "studio_name", None),
                     "project_dir": getattr(args, "project", None),
                     **({"scenario": args.scenario} if name == "capture" else {})})
    report = run_job(job)
    text = json.dumps(report, indent=2, default=str)
    if args.out:
        args.out.write_text(text)
    print(text)
    return 0 if report["status"] == "PASS" else 1


def recover(studio_name: str | None) -> int:
    """After a killed or timed-out run: stop play on a fresh connection, confirm Edit mode.

    Exit 0 = Studio is back in Edit mode; 1 = still not in Edit mode; 2 = Studio not found.
    """
    with McpClient() as client:
        bridge = Bridge(client)
        found = bridge.run(Op.LIST_STUDIOS)
        studio_id, reason = _pick_studio(found.data, studio_name) if found.ok else (None,
                                                                                  found.error)
        if studio_id is None:
            print(json.dumps({"recovered": False, "error": reason}))
            return 2
        bridge.studio_id = studio_id
        # Right after a killed run Studio may still be finishing the dead client's last
        # call and refuse to stop, so retry until Edit mode or the deadline.
        deadline = time.monotonic() + RECOVER_SECONDS
        while True:
            state = bridge.run(Op.STUDIO_STATE)
            in_edit = state.ok and "Current Studio Mode: Edit" in str(state.data)
            if in_edit or time.monotonic() >= deadline:
                break
            bridge.run(Op.STOP_PLAYTEST)
            time.sleep(2.0)
    print(json.dumps({"recovered": in_edit, "studio_id": studio_id,
                      "state": str(state.data)[:300]}))
    return 0 if in_edit else 1
