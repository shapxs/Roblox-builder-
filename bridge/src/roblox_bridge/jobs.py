"""File-backed job queue: <root>/jobs/<id>.json in, <root>/results/<id>.json out.

A job is a short list of whitelisted ops run in order against one Studio session.
If a playtest was started, STOP_PLAYTEST always runs at the end, even after a failure.
"""
from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from roblox_bridge.mcp_client import McpClient, McpError
from roblox_bridge.ops import Bridge, Op

JOB_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ALLOWED_KEYS = {"job_id", "ops", "studio_id", "dry_run", "timeout_seconds"}
MAX_OPS = 20
MAX_TIMEOUT = 600

# The AT-002 sequence: find Studio, inspect, play, probe, read output, stop.
AT002_OPS = [Op.LIST_STUDIOS, Op.INSPECT, Op.START_PLAYTEST, Op.PROBE, Op.GET_LOGS,
             Op.STOP_PLAYTEST]


class JobError(ValueError):
    pass


def parse_job(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise JobError("job must be a JSON object")
    extra = set(raw) - ALLOWED_KEYS
    if extra:
        raise JobError(f"unknown job keys: {sorted(extra)}")
    job_id = raw.get("job_id")
    if not isinstance(job_id, str) or not JOB_ID.match(job_id):
        raise JobError("job_id must match [a-z0-9-], max 64 chars")
    ops = raw.get("ops")
    if not isinstance(ops, list) or not 1 <= len(ops) <= MAX_OPS:
        raise JobError(f"ops must be a list of 1..{MAX_OPS} operations")
    try:
        parsed_ops = [Op(o) for o in ops]
    except ValueError as exc:
        raise JobError(f"unknown op: {exc}") from exc
    timeout = raw.get("timeout_seconds", 60)
    if not isinstance(timeout, int) or not 1 <= timeout <= MAX_TIMEOUT:
        raise JobError(f"timeout_seconds must be an int in 1..{MAX_TIMEOUT}")
    studio_id = raw.get("studio_id")
    if studio_id is not None and not isinstance(studio_id, str):
        raise JobError("studio_id must be a string")
    return {
        "job_id": job_id,
        "ops": parsed_ops,
        "studio_id": studio_id,
        "dry_run": bool(raw.get("dry_run", False)),
        "timeout_seconds": timeout,
    }


def run_job(job: dict, client_factory: Callable[[], McpClient] = McpClient) -> dict:
    started = datetime.now(UTC).isoformat()
    results = []
    with client_factory() as client:
        bridge = Bridge(client, studio_id=job["studio_id"], dry_run=job["dry_run"],
                        timeout=job["timeout_seconds"])
        playing = False
        for op in job["ops"]:
            if op is Op.STOP_PLAYTEST and not playing and Op.START_PLAYTEST in job["ops"]:
                continue  # never started, nothing to stop
            res = bridge.run(op)
            results.append(res.to_dict())
            if op is Op.LIST_STUDIOS and res.ok and bridge.studio_id is None:
                bridge.studio_id = _pick_studio(res.data)
                if bridge.studio_id is None and not job["dry_run"]:
                    count = _studio_count(res.data)
                    reason = ("no Roblox Studio is connected: open Studio and enable "
                              "'Studio as MCP server'" if count == 0 else
                              f"{count} Studios are open: pass an explicit studio_id")
                    results[-1].update(status="FAIL", ok=False, error=reason)
                    break
            if op is Op.START_PLAYTEST and res.ok:
                playing = True
            if op is Op.STOP_PLAYTEST and res.ok:
                playing = False
            if not res.ok:
                break
        if playing:  # cleanup: never leave a playtest running
            res = bridge.run(Op.STOP_PLAYTEST)
            results.append(res.to_dict() | {"cleanup": True})
    passed = all(r["ok"] for r in results) and len(results) >= len(job["ops"])
    return {
        "job_id": job["job_id"],
        "status": "PASS" if passed else "FAIL",
        "studio_id": bridge.studio_id,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "results": results,
    }


def _studio_count(data: object) -> int:
    studios = data.get("studios") if isinstance(data, dict) else None
    return len(studios) if isinstance(studios, list) else 0


def _pick_studio(data: object) -> str | None:
    studios = data.get("studios") if isinstance(data, dict) else None
    if not isinstance(studios, list) or len(studios) != 1:
        return None
    s = studios[0]
    if isinstance(s, str):
        return s
    if isinstance(s, dict):
        for key in ("studio_id", "studioId", "id"):
            if isinstance(s.get(key), str | int):
                return str(s[key])
    return None


def _write_atomic(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    os.replace(tmp, path)


def process_once(root: Path, client_factory: Callable[[], McpClient] = McpClient) -> int:
    jobs, results, done = (root / d for d in ("jobs", "results", "done"))
    for d in (jobs, results, done):
        d.mkdir(parents=True, exist_ok=True)
    handled = 0
    for path in sorted(jobs.glob("*.json")):
        try:
            job = parse_job(json.loads(path.read_text()))
            out = run_job(job, client_factory)
        except (JobError, json.JSONDecodeError) as exc:
            out = {"job_id": path.stem, "status": "REJECTED", "error": str(exc)}
        except McpError as exc:
            out = {"job_id": path.stem, "status": "ERROR", "error": str(exc)}
        _write_atomic(results / f"{path.stem}.json", out)
        os.replace(path, done / path.name)
        handled += 1
    return handled


def serve(root: Path, poll_seconds: float = 1.0) -> None:
    while True:
        process_once(root)
        time.sleep(poll_seconds)
