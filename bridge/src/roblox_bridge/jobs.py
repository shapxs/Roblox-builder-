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
from roblox_bridge.scenario import NAME as SCENARIO_NAME

JOB_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ALLOWED_KEYS = {"job_id", "ops", "studio_id", "studio_name", "dry_run", "timeout_seconds",
                "project_dir", "scenario", "scenario_dir"}
# Screenshots and preview video land in <capture root>/<job_id>-<timestamp>/.
DEFAULT_CAPTURE_ROOT = "~/Roblox Games/artifacts/captures"
# Controller-owned scenarios may only come from these roots (outside any game repo).
DEFAULT_POLICY_ROOTS = ["~/Roblox Games/policy"]
# SYNC may only read projects under these roots (colon-separated override in env).
DEFAULT_PROJECT_ROOTS = ["~/Roblox Games/games", "~/Voya/AutoDevFactory/worktrees",
                         "~/Roblox Games/artifacts/rc-src"]  # frozen release sources
MAX_OPS = 20
MAX_TIMEOUT = 600

# The AT-002 sequence: find Studio, inspect, play, probe, read output, stop.
AT002_OPS = [Op.LIST_STUDIOS, Op.INSPECT, Op.START_PLAYTEST, Op.PROBE, Op.GET_LOGS,
             Op.STOP_PLAYTEST]
# Read-only ops that still run after a failure, so a failed job carries its evidence.
DIAGNOSTIC_OPS = {Op.GET_LOGS}
# Named checks Forge can request. `core`: load the project and prove it boots cleanly.
CHECKS: dict[str, list[Op]] = {
    "at002": AT002_OPS,
    "core": [Op.LIST_STUDIOS, Op.SYNC, Op.START_PLAYTEST, Op.HEALTH, Op.GET_LOGS,
             Op.STOP_PLAYTEST],
    # `capture`: core plus a scripted scenario recorded to screenshots and a preview MP4.
    # HEALTH runs again after the scenario: errors raised by selling, upgrading or UI
    # updates happen after the first check and must still fail the run.
    "capture": [Op.LIST_STUDIOS, Op.SYNC, Op.START_PLAYTEST, Op.HEALTH, Op.SCENARIO,
                Op.HEALTH, Op.GET_LOGS, Op.STOP_PLAYTEST],
}


def capture_root() -> Path:
    raw = os.environ.get("ROBLOX_BRIDGE_CAPTURE_ROOT", DEFAULT_CAPTURE_ROOT)
    return Path(raw).expanduser().resolve()


def project_roots() -> list[Path]:
    raw = os.environ.get("ROBLOX_BRIDGE_PROJECT_ROOTS")
    roots = raw.split(":") if raw else DEFAULT_PROJECT_ROOTS
    return [Path(r).expanduser().resolve() for r in roots if r]


def _scenario_dir(value: object) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise JobError("scenario_dir must be a string")
    raw = os.environ.get("ROBLOX_BRIDGE_POLICY_ROOTS")
    roots = [Path(r).expanduser().resolve()
             for r in (raw.split(":") if raw else DEFAULT_POLICY_ROOTS) if r]
    path = Path(value).expanduser().resolve()
    if not any(root == path or root in path.parents for root in roots):
        raise JobError(f"scenario_dir {path} is outside the policy roots")
    if not path.is_dir():
        raise JobError(f"scenario_dir {path} does not exist")
    return path


def _project_dir(value: object) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise JobError("project_dir must be a string")
    path = Path(value).expanduser().resolve()
    if not any(root == path or root in path.parents for root in project_roots()):
        raise JobError(f"project_dir {path} is outside the allowed project roots")
    if not (path / "default.project.json").is_file():
        raise JobError(f"project_dir {path} has no default.project.json")
    return path


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
    studio_name = raw.get("studio_name")
    if studio_name is not None and (not isinstance(studio_name, str) or not studio_name.strip()):
        raise JobError("studio_name must be a non-empty string")
    project_dir = _project_dir(raw.get("project_dir"))
    if Op.SYNC in parsed_ops and project_dir is None:
        raise JobError("SYNC requires project_dir")
    scenario = raw.get("scenario")
    if Op.SCENARIO in parsed_ops:
        if project_dir is None or not isinstance(scenario, str) or not SCENARIO_NAME.match(
                scenario):
            raise JobError("SCENARIO requires project_dir and a scenario name")
    elif scenario is not None:
        raise JobError("scenario given without a SCENARIO op")
    scenario_dir = _scenario_dir(raw.get("scenario_dir"))
    return {
        "job_id": job_id,
        "project_dir": project_dir,
        "scenario": scenario,
        "scenario_dir": scenario_dir,
        "ops": parsed_ops,
        "studio_id": studio_id,
        "studio_name": studio_name,
        "dry_run": bool(raw.get("dry_run", False)),
        "timeout_seconds": timeout,
    }


def run_job(job: dict, client_factory: Callable[[], McpClient] = McpClient) -> dict:
    started = datetime.now(UTC).isoformat()
    capture_dir = None
    if Op.SCENARIO in job["ops"]:
        capture_dir = capture_root() / f"{job['job_id']}-{datetime.now():%Y%m%d-%H%M%S}"
    results = []
    with client_factory() as client:
        bridge = Bridge(client, studio_id=job["studio_id"], dry_run=job["dry_run"],
                        timeout=job["timeout_seconds"], project_dir=job.get("project_dir"),
                        scenario=job.get("scenario"), scenario_dir=job.get("scenario_dir"),
                        capture_dir=capture_dir,
                        client_factory=client_factory)
        playing = False
        failed = False
        try:
            for op in job["ops"]:
                if op is Op.STOP_PLAYTEST and not playing and Op.START_PLAYTEST in job["ops"]:
                    continue  # never started, nothing to stop
                if failed and op not in DIAGNOSTIC_OPS:
                    continue  # after a failure, only collect evidence (and clean up below)
                res = bridge.run(op)
                results.append(res.to_dict())
                if op is Op.LIST_STUDIOS and res.ok and bridge.studio_id is None:
                    bridge.studio_id, reason = _pick_studio(res.data, job.get("studio_name"))
                    if bridge.studio_id is None and not job["dry_run"]:
                        results[-1].update(status="FAIL", ok=False, error=reason)
                        failed = True
                        break
                if op is Op.START_PLAYTEST and res.status not in {"UNSUPPORTED", "DRY_RUN"}:
                    playing = True  # a start that timed out or failed may still have begun
                if op is Op.STOP_PLAYTEST and res.ok:
                    playing = False
                if not res.ok and op not in DIAGNOSTIC_OPS:
                    failed = True
        finally:
            # Never leave a playtest running: this also runs on exceptions and on
            # SIGTERM (the CLI turns it into SystemExit).
            if playing:
                res = bridge.run(Op.STOP_PLAYTEST)
                results.append(res.to_dict() | {"cleanup": True})
    passed = not failed and all(r["ok"] for r in results) and len(results) >= len(job["ops"])
    return {
        "job_id": job["job_id"],
        "status": "PASS" if passed else "FAIL",
        "studio_id": bridge.studio_id,
        "project_dir": str(job["project_dir"]) if job.get("project_dir") else None,
        "capture_dir": str(capture_dir) if capture_dir else None,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "results": results,
    }


def _pick_studio(data: object, name: str | None = None) -> tuple[str | None, str]:
    """(studio id, reason if none). With `name`, only a Studio whose title contains it
    qualifies, so an owner's ordinary place never becomes the QA target by accident."""
    studios = data.get("studios") if isinstance(data, dict) else None
    studios = studios if isinstance(studios, list) else []
    if name is not None:
        studios = [s for s in studios if isinstance(s, dict) and name in str(s.get("name"))]
        if len(studios) != 1:
            return None, (f"QA Studio {name!r} is not open" if not studios else
                          f"{len(studios)} open Studios match {name!r}")
    if not studios:
        return None, ("no Roblox Studio is connected: open Studio and enable "
                      "'Studio as MCP server'")
    if len(studios) != 1:
        return None, f"{len(studios)} Studios are open: pass studio_id or studio_name"
    s = studios[0]
    if isinstance(s, str):
        return s, ""
    if isinstance(s, dict):
        for key in ("studio_id", "studioId", "id"):
            if isinstance(s.get(key), str | int):
                return str(s[key]), ""
    return None, "unrecognized Studio entry"


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
