import json
import sys
from pathlib import Path

import pytest

from roblox_bridge.jobs import CHECKS, JobError, parse_job, run_job
from roblox_bridge.mcp_client import McpClient
from roblox_bridge.scenario import ScenarioError, load_scenario

FAKE = str(Path(__file__).with_name("fake_mcp_server.py"))
TOOLS = [{"name": n, "params": p} for n, p in [
    ("start_stop_play", ["is_start", "studio_id"]),
    ("get_console_output", ["studio_id"]),
    ("execute_luau", ["code", "datamodel_type", "studio_id"]),
    ("character_navigation", ["instance_path", "datamodel_type", "studio_id"]),
    ("user_keyboard_input", ["datamodel_type", "studio_id"]),
    ("screen_capture", ["capture_id", "studio_id"]),
]]


@pytest.fixture
def game(tmp_path, monkeypatch):
    root = tmp_path / "games" / "g"
    (root / "qa" / "scenarios").mkdir(parents=True)
    (root / "default.project.json").write_text('{"name": "g", "tree": {"$className": "DataModel"}}')
    monkeypatch.setenv("ROBLOX_BRIDGE_PROJECT_ROOTS", str(tmp_path / "games"))
    monkeypatch.setenv("ROBLOX_BRIDGE_CAPTURE_ROOT", str(tmp_path / "captures"))
    return root


def scenario(game, steps, name="s"):
    (game / "qa" / "scenarios" / f"{name}.json").write_text(json.dumps({"steps": steps}))
    return name


def fake(monkeypatch, **cfg):
    monkeypatch.setenv("FAKE_MCP", json.dumps({"tools": TOOLS, "studios": ["s1"], **cfg}))
    return lambda: McpClient([sys.executable, FAKE], timeout=10)


def capture_job(game, name):
    ops = [o.value for o in CHECKS["capture"] if o.value != "SYNC"]  # template-free project
    return parse_job({"job_id": "cap", "ops": ops, "project_dir": str(game), "scenario": name})


@pytest.mark.parametrize("steps, match", [
    ([{"interact": {"target": "Workspace; os.exit()"}}], "dotted Workspace target"),
    ([{"interact": {"target": "Collect", "times": 500}}], "times must be"),
    ([{"run_luau": "print(1)"}], "unknown action"),
    ([{"assert": {"attribute": {"Cash": [1]}}}], "attribute needs"),
    ([{"assert": {"source_contains": "x"}}], "unknown assertion"),
    ([{"capture": "../escape"}], "capture needs a name"),
    ([{"wait": 120}], "wait must be"),
    ([], "1..200 steps"),
])
def test_scenario_files_are_data_only(game, steps, match):
    with pytest.raises(ScenarioError, match=match):
        load_scenario(game, scenario(game, steps))


def test_scenario_passes_and_produces_screenshots_and_video(game, monkeypatch):
    factory = fake(monkeypatch, attributes={"Carried": 5, "Cash": 0})
    name = scenario(game, [{"assert": {"ui_visible": "MainHUD"}},
                           {"interact": {"target": "Collect", "times": 5}},
                           {"assert": {"attribute": {"Carried": 5}}},
                           {"capture": "collected"}, {"wait": 1}])
    report = run_job(capture_job(game, name), factory)
    assert report["status"] == "PASS", report
    data = next(r["data"] for r in report["results"] if r["op"] == "SCENARIO")
    assert [Path(p).name for p in data["screenshots"]] == ["collected.jpg", "final.jpg"]
    assert data["frames"] > 0 and data["video"] and Path(data["video"]).stat().st_size > 0
    assert Path(report["capture_dir"]).parent == game.parents[1] / "captures"


def test_failed_assertion_reports_expected_and_actual_then_stops(game, monkeypatch):
    factory = fake(monkeypatch, attributes={"Carried": 2})
    name = scenario(game, [{"assert": {"attribute": {"Carried": 5}}}])
    report = run_job(capture_job(game, name), factory)
    step = next(r for r in report["results"] if r["op"] == "SCENARIO")
    assert report["status"] == "FAIL" and step["status"] == "FAIL"
    assert '"expected": {"Carried": 5}' in step["error"] and '"Carried": 2' in step["error"]
    assert report["results"][-1]["op"] == "STOP_PLAYTEST"


def test_scenario_job_needs_a_valid_name(game):
    ops = ["LIST_STUDIOS", "SCENARIO"]
    with pytest.raises(JobError, match="scenario name"):
        parse_job({"job_id": "x", "ops": ops, "project_dir": str(game), "scenario": "../x"})
    with pytest.raises(JobError, match="without a SCENARIO op"):
        parse_job({"job_id": "x", "ops": ["LIST_STUDIOS"], "scenario": "s"})


def test_errors_raised_during_gameplay_fail_the_capture(game, monkeypatch):
    clean = {"ready": True, "errors": [], "players": [{"name": "p", "ready": True}]}
    broken = clean | {"errors": ["ServerScriptService.Server:80: attempt to compare nil"]}
    factory = fake(monkeypatch, attributes={"Carried": 1}, health_seq=[clean, broken])
    name = scenario(game, [{"interact": {"target": "Sell"}}])
    report = run_job(capture_job(game, name), factory)
    health = [r for r in report["results"] if r["op"] == "HEALTH"]
    assert [h["status"] for h in health] == ["PASS", "FAIL"]  # second check, after gameplay
    assert "attempt to compare nil" in health[1]["error"]
    assert report["status"] == "FAIL"


def test_preview_is_real_time_not_sped_up(game, monkeypatch):
    factory = fake(monkeypatch, attributes={})
    name = scenario(game, [{"wait": 2}])
    report = run_job(capture_job(game, name), factory)
    data = next(r["data"] for r in report["results"] if r["op"] == "SCENARIO")
    assert data["video_speed"] == "real-time"
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", data["video"]], capture_output=True, text=True)
    # ~2 s of scenario + 2 s settle: a sped-up preview would be about half that.
    assert float(out.stdout) >= 3.0


def test_wedged_capture_tool_fails_fast_with_a_clear_reason(game, monkeypatch):
    monkeypatch.setattr("roblox_bridge.scenario.CAPTURE_TIMEOUT_SECONDS", 1.0)
    factory = fake(monkeypatch, attributes={}, hang=["screen_capture"])
    name = scenario(game, [{"capture": "spawn"}])
    report = run_job(capture_job(game, name), factory)
    step = next(r for r in report["results"] if r["op"] == "SCENARIO")
    assert step["status"] == "FAIL" and "restart Roblox Studio" in step["error"]
    assert step["data"]["capture_unresponsive"] is True
    assert report["results"][-1]["op"] == "STOP_PLAYTEST"
