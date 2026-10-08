import json
import sys
from pathlib import Path

import pytest

from roblox_bridge.jobs import AT002_OPS, JobError, parse_job, process_once, run_job
from roblox_bridge.mcp_client import McpClient, McpError
from roblox_bridge.ops import Bridge, Op

FAKE = str(Path(__file__).with_name("fake_mcp_server.py"))

MODERN_TOOLS = [
    {"name": "start_playtest", "params": ["studio_id"]},
    {"name": "stop_playtest", "params": ["studio_id"]},
    {"name": "get_output_logs", "params": ["studio_id"]},
    {"name": "run_code", "params": ["code", "studio_id"]},
    {"name": "eval_server_runtime", "params": ["source", "studio_id"]},
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
    factory = fake(tools=MODERN_TOOLS, studios=[{"studio_id": "s-1", "name": "Place"}])
    report = run_job(at002(), factory)
    assert report["status"] == "PASS", report
    assert report["studio_id"] == "s-1"
    calls = fake.calls()
    assert [c["name"] for c in calls] == ["list_roblox_studios", "run_code", "start_playtest",
                                          "eval_server_runtime", "get_output_logs",
                                          "stop_playtest"]
    assert all(c["arguments"].get("studio_id") == "s-1" for c in calls[1:])
    assert "GetChildren" in calls[1]["arguments"]["code"]


def test_legacy_tool_names_resolve_with_fixed_args(fake):
    factory = fake(tools=[{"name": "start_stop_play", "params": ["mode"]},
                          {"name": "get_console_output", "params": []},
                          {"name": "run_code", "params": ["command"]}],
                   studios=["only"])
    assert run_job(at002(), factory)["status"] == "PASS"
    modes = [c["arguments"]["mode"] for c in fake.calls() if c["name"] == "start_stop_play"]
    assert modes == ["start_play", "stop"]


def test_failure_mid_playtest_still_stops_playtest(fake):
    factory = fake(tools=MODERN_TOOLS, studios=["s"], errors=["eval_server_runtime"])
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert report["results"][-1]["op"] == "STOP_PLAYTEST"
    assert report["results"][-1].get("cleanup") is True
    assert fake.calls()[-1]["name"] == "stop_playtest"


def test_missing_tool_is_unsupported_not_guessed(fake):
    factory = fake(tools=[], studios=["s"])
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert report["results"][-1]["status"] == "UNSUPPORTED"
    assert "available" in report["results"][-1]["error"]


def test_ambiguous_studio_requires_explicit_id(fake):
    factory = fake(tools=MODERN_TOOLS, studios=["a", "b"])
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert [c["name"] for c in fake.calls()] == ["list_roblox_studios"]
    assert run_job(at002(studio_id="b"), factory)["status"] == "PASS"


def test_dry_run_never_touches_studio(fake):
    factory = fake(tools=MODERN_TOOLS, studios=["s"])
    report = run_job(at002(dry_run=True), factory)
    assert {r["status"] for r in report["results"]} == {"DRY_RUN"}
    assert fake.calls() == []


def test_hung_tool_times_out(fake):
    factory = fake(tools=MODERN_TOOLS, hang=["get_output_logs"])
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
    factory = fake(tools=MODERN_TOOLS, studios=["s"])
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


def test_no_studio_open_fails_with_actionable_reason(fake):
    factory = fake(tools=[], studios=[])
    report = run_job(at002(), factory)
    assert report["status"] == "FAIL"
    assert [r["op"] for r in report["results"]] == ["LIST_STUDIOS"]
    assert "open Studio" in report["results"][0]["error"]
