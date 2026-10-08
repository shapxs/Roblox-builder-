"""roblox-bridge CLI.

  roblox-bridge tools                   list Studio MCP tools and their parameters
  roblox-bridge op <OP> [--studio ID]   run one whitelisted op
  roblox-bridge at002 [--dry-run]       run the AT-002 acceptance sequence
  roblox-bridge check <name> --project DIR   run a named check (core, at002)
  roblox-bridge serve <queue-dir>       process <dir>/jobs/*.json forever
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from roblox_bridge.jobs import CHECKS, parse_job, run_job, serve
from roblox_bridge.mcp_client import McpClient
from roblox_bridge.ops import Bridge, Op


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="roblox-bridge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools")
    p_op = sub.add_parser("op")
    p_op.add_argument("op", choices=[o.value for o in Op])
    p_op.add_argument("--studio")
    p_op.add_argument("--dry-run", action="store_true")
    p_at = sub.add_parser("at002")
    p_at.add_argument("--studio")
    p_at.add_argument("--dry-run", action="store_true")
    p_at.add_argument("--out", type=Path)
    p_check = sub.add_parser("check")
    p_check.add_argument("name", choices=sorted(CHECKS))
    p_check.add_argument("--project")
    p_check.add_argument("--studio")
    p_check.add_argument("--dry-run", action="store_true")
    p_check.add_argument("--out", type=Path)
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("root", type=Path)
    args = ap.parse_args(argv)

    if args.cmd == "serve":
        serve(args.root)
        return 0
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
                     "project_dir": getattr(args, "project", None)})
    report = run_job(job)
    text = json.dumps(report, indent=2, default=str)
    if args.out:
        args.out.write_text(text)
    print(text)
    return 0 if report["status"] == "PASS" else 1
