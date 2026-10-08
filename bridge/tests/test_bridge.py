import json
import sys
from pathlib import Path

import pytest

from roblox_bridge.jobs import AT002_OPS, CHECKS, JobError, parse_job, process_once, run_job
from roblox_bridge.mcp_client import McpClient, McpError
from roblox_bridge import ops
from roblox_bridge.ops import Bridge, Op

FAKE = str(Path(__file__).with_name("fake_mcp_server.py"))

# Real Studio 0.742 tool surface used by the bridge (schemas abbreviated).
STUDIO_TOOLS = [
    {"name": "get_studio_state", "params": ["studio_id"]},
    {"name": "start_stop_play", "params": ["is_start", "studio_id"]},
    {"name": "get_console_output", "params": ["studio_id"]},
    {"name": "execute_luau", "params": ["code", "datamodel_type", "studio_id"]},
]


@pytest.fixture
def fake(monkeypatch, tmp_path):
    log = tmp_path / "calls.jsonl"

    def configure(**cfg):
        monkeypatch.setenv("FAKE_MCP", json.dumps({"log": str(log), **cfg}))
        return lambda: McpClient([sys.executable, FAKE], timeout=5)

    configure.calls = lambda: ([json.loads(l) for l in log.read_text().splitlines()]
                               if log.exists() else [])
    return configure


def at002(**kw):
    return parse_job({"job_id": "t", "ops": [o.value for o in AT002_OPS], **kw})


def test_at002_passes_and_routes_studio_id(fake):
    factory = fake(tools=STUDIO_TOOLS, studios=[{"id": "s-1", "name": "Place"}])
    report = run_job(at002(), factory)
    assert report["status"] == "PASS", report
    assert report["studio_id"] == "s-1"
    calls = fake.calls()
    assert [c["name"] for c in calls] == ["list_roblox_studios", "execute_luau",
                                          "start_stop_play", "execute_luau", "execute_luau",
                                          "get_console_output", "start_stop_play"]
    assert all(c["arguments"].get("studio_id") == "s-1" for c in calls[1:])
    inspect, start, ready, probe, _, stop = calls[1:]
    assert inspect["arguments"]["datamodel_type"] == "Edit"
    assert start["arguments"]["is_start"] is True and stop["arguments"]["is_start"] is False
    assert ready["arguments"]["datamodel_type"] == probe["arguments"]["datamodel_type"] == "Server"


def test_playtest_without_player_times_out_and_stops(fake, monkeypatch):
    monkeypatch.setattr(ops, "READY_TIMEOUT_SECONDS", 0.3)
    monkeypatch.setattr(ops, "READY_POLL_SECONDS", 0.05)
    factory = fake(tools=STUDIO_TOOLS, studios=["s"], players=0)
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert report["results"][2]["status"] == "TIMEOUT"
    assert fake.calls()[-1] == {"name": "start_stop_play",
                                "arguments": {"is_start": False, "studio_id": "s"}}


def test_failure_mid_playtest_still_stops_playtest(fake):
    factory = fake(tools=STUDIO_TOOLS, studios=["s"], errors=["get_console_output"])
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert report["results"][-1]["op"] == "STOP_PLAYTEST"
    assert fake.calls()[-1]["arguments"]["is_start"] is False


def test_missing_tool_is_unsupported_not_guessed(fake):
    factory = fake(tools=[], studios=["s"])
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert report["results"][-1]["status"] == "UNSUPPORTED"
    assert "available" in report["results"][-1]["error"]


def test_ambiguous_studio_requires_explicit_id(fake):
    factory = fake(tools=STUDIO_TOOLS, studios=["a", "b"])
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert [c["name"] for c in fake.calls()] == ["list_roblox_studios"]
    assert run_job(at002(studio_id="b"), factory)["status"] == "PASS"


def test_dry_run_never_touches_studio(fake):
    factory = fake(tools=STUDIO_TOOLS, studios=["s"])
    report = run_job(at002(dry_run=True), factory)
    assert {r["status"] for r in report["results"]} == {"DRY_RUN"}
    assert fake.calls() == []


def test_hung_tool_times_out(fake):
    factory = fake(tools=STUDIO_TOOLS, hang=["get_console_output"])
    with factory() as client:
        res = Bridge(client, timeout=0.5).run(Op.GET_LOGS)
    assert res.status == "TIMEOUT"


def test_client_reports_dead_server():
    with pytest.raises(McpError):
        McpClient([sys.executable, "-c", "pass"], timeout=2).start()


@pytest.mark.parametrize("raw", [
    {"job_id": "x", "ops": ["START_PLAYTEST"], "tool": "run_code"},
    {"job_id": "x", "ops": ["RUN_ARBITRARY_LUAU"]},
    {"job_id": "../etc", "ops": ["INSPECT"]},
    {"job_id": "x", "ops": []},
    {"job_id": "x", "ops": ["INSPECT"], "timeout_seconds": 10_000},
])
def test_job_validation_rejects(raw):
    with pytest.raises(JobError):
        parse_job(raw)


def test_queue_writes_results_and_archives_jobs(fake, tmp_path, monkeypatch):
    factory = fake(tools=STUDIO_TOOLS, studios=["s"])
    root = tmp_path / "queue"
    (root / "jobs").mkdir(parents=True)
    (root / "jobs" / "good.json").write_text(json.dumps(
        {"job_id": "good", "ops": ["LIST_STUDIOS", "START_PLAYTEST", "STOP_PLAYTEST"]}))
    (root / "jobs" / "bad.json").write_text(json.dumps({"job_id": "bad", "ops": ["NOPE"]}))
    assert process_once(root, factory) == 2
    assert json.loads((root / "results" / "good.json").read_text())["status"] == "PASS"
    assert json.loads((root / "results" / "bad.json").read_text())["status"] == "REJECTED"
    assert sorted(p.name for p in (root / "done").iterdir()) == ["bad.json", "good.json"]
    assert list((root / "jobs").iterdir()) == []


def test_no_studio_open_fails_with_actionable_reason(fake, monkeypatch):
    monkeypatch.setattr(ops, "DISCOVERY_SECONDS", 0.2)
    monkeypatch.setattr(ops, "READY_POLL_SECONDS", 0.05)
    factory = fake(tools=[], studios=[])
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert [r["op"] for r in report["results"]] == ["LIST_STUDIOS"]
    assert "open Studio" in report["results"][0]["error"]


@pytest.fixture
def game(tmp_path, monkeypatch):
    """A copy of the real template under an allowed project root."""
    import shutil

    root = tmp_path / "games"
    shutil.copytree(Path(__file__).parents[2] / "games" / "_template", root / "demo",
                    ignore=shutil.ignore_patterns("artifacts"))
    monkeypatch.setenv("ROBLOX_BRIDGE_PROJECT_ROOTS", str(root))
    return root / "demo"


def core(game, **kw):
    return parse_job({"job_id": "c", "ops": [o.value for o in CHECKS["core"]],
                      "project_dir": str(game), **kw})


def test_core_syncs_the_project_then_checks_health(fake, game):
    factory = fake(tools=STUDIO_TOOLS, studios=["s"])
    report = run_job(core(game), factory)
    assert report["status"] == "PASS", report
    sync = fake.calls()[1]
    assert sync["name"] == "execute_luau" and sync["arguments"]["datamodel_type"] == "Edit"
    assert "ForgeManaged" in sync["arguments"]["code"]
    assert "function Economy.collect" in sync["arguments"]["code"]  # project source as data


def test_runtime_error_fails_core_but_still_collects_logs_and_stops(fake, game):
    factory = fake(tools=STUDIO_TOOLS, studios=["s"], health={
        "ready": False, "players": [],
        "errors": ["ServerScriptService.Server:125: attempt to index nil with 'Value'"]})
    report = run_job(core(game), factory)
    assert report["status"] == "FAIL"
    ops_run = [(r["op"], r["status"]) for r in report["results"]]
    assert ops_run[-3:] == [("HEALTH", "FAIL"), ("GET_LOGS", "PASS"), ("STOP_PLAYTEST", "PASS")]
    assert "attempt to index nil" in report["results"][3]["error"]


def test_client_errors_fail_health(fake, game):
    factory = fake(tools=STUDIO_TOOLS, studios=["s"],
                   client={"errors": ["Client:3: boom"], "screens": []})
    report = run_job(core(game), factory)
    assert report["status"] == "FAIL"
    assert "client: Client:3: boom" in report["results"][3]["error"]


def test_project_dir_must_be_under_allowed_roots(game, tmp_path):
    with pytest.raises(JobError, match="outside the allowed"):
        core(tmp_path)  # tmp_path itself is outside the games root
    with pytest.raises(JobError, match="SYNC requires project_dir"):
        parse_job({"job_id": "x", "ops": ["SYNC"]})


def test_sync_refuses_files_outside_project_and_odd_classes(game):
    from roblox_bridge.sync import SyncError, _tree

    with pytest.raises(SyncError, match="outside the project"):
        _tree({"name": "x", "className": "ModuleScript", "filePaths": ["../../etc.luau"]}, game)
    with pytest.raises(SyncError, match="only scripts and folders"):
        _tree({"name": "x", "className": "Part"}, game)


def test_sync_payload_cannot_escape_the_long_string():
    from roblox_bridge.sync import sync_code

    code = sync_code({"project": "p", "mounts": [{"path": ["S"], "node": {
        "name": "m", "className": "ModuleScript", "children": [],
        "source": "return ']]' .. ']=]' .. ']==]'"}}]})
    assert "JSONDecode([===[" in code and code.count("]===]") == 1
