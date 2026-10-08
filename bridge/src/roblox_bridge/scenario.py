"""Scripted playtest scenarios with screenshot and preview-video capture.

A scenario is JSON data in <project>/qa/scenarios/<name>.json:

    {"id": "core_loop", "max_duration_seconds": 120, "steps": [
        {"assert": {"ui_visible": "MainHUD"}},
        {"interact": {"target": "Collect", "times": 5}},
        {"assert": {"attribute": {"Carried": 5}}},
        {"capture": "collected"}
    ]}

Steps are data only. `interact` walks the character to game.Workspace.<target> and
presses E; assertions read player attributes / ScreenGui names with constant Luau and
are compared here in Python. While the scenario runs, a second MCP connection grabs
frames (~2 fps) that ffmpeg stitches into a preview MP4. A failed video never fails
the scenario.
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from roblox_bridge.mcp_client import McpClient, McpError

NAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")
PATH = re.compile(r"^[A-Za-z0-9_]{1,64}(\.[A-Za-z0-9_]{1,64}){0,7}$")
MAX_STEPS = 200
MAX_TIMES = 50
ASSERT_WAIT_SECONDS = 3.0
KEY_GAP_MS = 300
PREVIEW_FPS = 4  # frames are grabbed at ~2 fps, so previews play at ~2x speed
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"

ATTRIBUTES_LUAU = """
local p = game:GetService("Players"):GetPlayers()[1]
return game:GetService("HttpService"):JSONEncode(p and p:GetAttributes() or {})
"""
SCREENS_LUAU = """
local gui = game:GetService("Players").LocalPlayer:FindFirstChild("PlayerGui")
local names = {}
if gui then
	for _, g in gui:GetChildren() do
		if g:IsA("ScreenGui") and g.Enabled then table.insert(names, g.Name) end
	end
end
return game:GetService("HttpService"):JSONEncode(names)
"""


class ScenarioError(ValueError):
    pass


def load_scenario(project_dir: Path, name: str) -> dict:
    if not NAME.match(name):
        raise ScenarioError(f"bad scenario name {name!r}")
    path = Path(project_dir) / "qa" / "scenarios" / f"{name}.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ScenarioError(f"cannot read {path}: {exc}") from exc
    steps = data.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ScenarioError(f"scenario needs 1..{MAX_STEPS} steps")
    for i, step in enumerate(steps):
        _validate_step(i, step)
    limit = data.get("max_duration_seconds", 120)
    if not isinstance(limit, int) or not 10 <= limit <= 600:
        raise ScenarioError("max_duration_seconds must be an int in 10..600")
    return {"id": data.get("id", name), "steps": steps, "max_duration_seconds": limit}


def _validate_step(i: int, step: object) -> None:
    if not isinstance(step, dict) or len(step) != 1:
        raise ScenarioError(f"step {i}: must be an object with exactly one action")
    kind, arg = next(iter(step.items()))
    if kind == "interact":
        if not isinstance(arg, dict) or not PATH.match(str(arg.get("target", ""))):
            raise ScenarioError(f"step {i}: interact needs a dotted Workspace target")
        times = arg.get("times", 1)
        if not isinstance(times, int) or not 1 <= times <= MAX_TIMES:
            raise ScenarioError(f"step {i}: times must be 1..{MAX_TIMES}")
    elif kind == "assert":
        if not isinstance(arg, dict) or len(arg) != 1:
            raise ScenarioError(f"step {i}: assert takes one condition")
        (cond, value), = arg.items()
        if cond == "ui_visible":
            if not isinstance(value, str) or not NAME.match(value):
                raise ScenarioError(f"step {i}: ui_visible needs a ScreenGui name")
        elif cond == "attribute":
            if not isinstance(value, dict) or not value or not all(
                    NAME.match(k) and isinstance(v, int | float | str | bool)
                    for k, v in value.items()):
                raise ScenarioError(f"step {i}: attribute needs {{name: value}}")
        else:
            raise ScenarioError(f"step {i}: unknown assertion {cond!r}")
    elif kind == "capture":
        if not isinstance(arg, str) or not NAME.match(arg):
            raise ScenarioError(f"step {i}: capture needs a name")
    elif kind == "wait":
        if not isinstance(arg, int | float) or not 0 < arg <= 30:
            raise ScenarioError(f"step {i}: wait must be 0..30 seconds")
    else:
        raise ScenarioError(f"step {i}: unknown action {kind!r}")


class ScenarioRunner:
    def __init__(self, client: McpClient, studio_id: str, out_dir: Path,
                 client_factory=McpClient) -> None:
        self.client = client
        self.studio_id = studio_id
        self.out_dir = Path(out_dir)
        self.client_factory = client_factory
        # Studio returns an empty image when two captures overlap, so they take turns.
        self._capture_lock = threading.Lock()

    def run(self, scenario: dict) -> dict:
        shots = self.out_dir / "screenshots"
        frames = self.out_dir / "frames"
        shots.mkdir(parents=True, exist_ok=True)
        frames.mkdir(parents=True, exist_ok=True)
        stop = threading.Event()
        recorder = threading.Thread(target=self._record, args=(frames, stop), daemon=True)
        recorder.start()
        deadline = time.monotonic() + scenario["max_duration_seconds"]
        steps, ok = [], True
        try:
            for i, step in enumerate(scenario["steps"]):
                if time.monotonic() > deadline:
                    steps.append({"step": i, "status": "TIMEOUT",
                                  "detail": "scenario exceeded max_duration_seconds"})
                    ok = False
                    break
                status, detail = self._step(step, shots)
                steps.append({"step": i, "action": step, "status": status, "detail": detail})
                if status != "PASS":
                    ok = False
                    break
        finally:
            stop.set()
            recorder.join(timeout=30)
        self._capture(shots / "final.jpg")
        video, video_error = self._stitch(frames)
        return {
            "scenario": scenario["id"], "passed": ok, "steps": steps,
            "screenshots": sorted(str(p) for p in shots.glob("*.jpg")),
            "frames": len(list(frames.glob("*.jpg"))),
            "video": str(video) if video else None, "video_error": video_error,
        }

    # -- steps -----------------------------------------------------------

    def _step(self, step: dict, shots: Path) -> tuple[str, object]:
        kind, arg = next(iter(step.items()))
        if kind == "interact":
            path = f"game.Workspace.{arg['target']}"
            self._tool("character_navigation", {"datamodel_type": "Client",
                                                "instance_path": path})
            presses = []
            for _ in range(arg.get("times", 1)):
                presses += [{"action": "keyPress", "key_code": "E"},
                            {"action": "wait", "wait_time_ms": KEY_GAP_MS}]
            self._tool("user_keyboard_input", {"datamodel_type": "Client", "actions": presses})
            return "PASS", None
        if kind == "wait":
            time.sleep(arg)
            return "PASS", None
        if kind == "capture":
            for _ in range(3):
                if self._capture(shots / f"{arg}.jpg"):
                    return "PASS", None
                time.sleep(0.3)
            return "FAIL", "screen capture returned no image"
        return self._assert(arg)

    def _assert(self, arg: dict) -> tuple[str, object]:
        (cond, want), = arg.items()
        deadline = time.monotonic() + ASSERT_WAIT_SECONDS
        while True:
            if cond == "ui_visible":
                got = self._luau(SCREENS_LUAU, "Client")
                ok = isinstance(got, list) and want in got
            else:
                got = self._luau(ATTRIBUTES_LUAU, "Server")
                got = got if isinstance(got, dict) else {}
                ok = all(got.get(k) == v for k, v in want.items())
            if ok:
                return "PASS", got
            if time.monotonic() >= deadline:
                return "FAIL", {"expected": want, "actual": got}
            time.sleep(0.25)

    # -- Studio calls ----------------------------------------------------

    def _tool(self, name: str, args: dict, client: McpClient | None = None) -> dict:
        raw = (client or self.client).call_tool(name, {**args, "studio_id": self.studio_id})
        if raw.get("isError"):
            text = " ".join(i.get("text", "") for i in raw.get("content", []))
            raise McpError(f"{name}: {text[:500]}")
        return raw

    def _luau(self, code: str, datamodel: str) -> object:
        raw = self._tool("execute_luau", {"code": code.strip(), "datamodel_type": datamodel})
        text = next((i.get("text") for i in raw.get("content", []) if i.get("type") == "text"),
                    "")
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    def _capture(self, path: Path, client: McpClient | None = None) -> bool:
        try:
            with self._capture_lock:
                raw = self._tool("screen_capture", {"capture_id": path.stem}, client)
        except McpError:
            return False
        for item in raw.get("content", []):
            if item.get("type") == "image" and item.get("data"):
                path.write_bytes(base64.b64decode(item["data"]))
                return True
        return False

    def _record(self, frames: Path, stop: threading.Event) -> None:
        """Grab frames on a second connection so capture never blocks the scenario."""
        try:
            with self.client_factory() as client:
                # A Studio tool called before Studio registers with this new proxy
                # hangs until timeout, so wait for registration first.
                if not self._wait_for_studio(client, stop):
                    return
                n = 0
                while not stop.is_set():
                    if self._capture(frames / f"frame_{n:05d}.jpg", client):
                        n += 1
                    else:
                        time.sleep(0.25)
        except McpError:
            pass  # no frames means no video, never a failed scenario

    def _wait_for_studio(self, client: McpClient, stop: threading.Event,
                         limit_seconds: float = 15.0) -> bool:
        deadline = time.monotonic() + limit_seconds
        while not stop.is_set() and time.monotonic() < deadline:
            raw = client.call_tool("list_roblox_studios", {})
            text = next((i.get("text") for i in raw.get("content", [])), "") or ""
            if self.studio_id and self.studio_id in text:
                return True
            time.sleep(0.5)
        return False

    def _stitch(self, frames: Path) -> tuple[Path | None, str | None]:
        if not list(frames.glob("frame_*.jpg")):
            return None, "no frames captured"
        out = self.out_dir / "preview.mp4"
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-framerate", str(PREVIEW_FPS),
               "-i", str(frames / "frame_%05d.jpg"),
               "-vf", "scale=1280:-2,format=yuv420p", "-c:v", "libx264",
               "-preset", "veryfast", "-crf", "26", "-movflags", "+faststart", str(out)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, f"ffmpeg: {exc}"
        if proc.returncode != 0:
            return None, f"ffmpeg: {proc.stderr.strip()[:500]}"
        return out, None
