"""Whitelisted Studio operations.

Jobs name an operation; they never supply tool names or Luau. Every tool name and
every Luau snippet that can reach Studio is a constant in this file.

Tool names and arguments match Studio 0.742's built-in MCP server (seen live
2026-10-08). Studio's own tools are only listed while a place is connected;
`list_roblox_studios` is served by the proxy and always callable.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from roblox_bridge.mcp_client import McpClient, McpError, Tool


class Op(StrEnum):
    LIST_STUDIOS = "LIST_STUDIOS"
    LIST_TOOLS = "LIST_TOOLS"
    STUDIO_STATE = "STUDIO_STATE"
    INSPECT = "INSPECT"
    START_PLAYTEST = "START_PLAYTEST"
    PROBE = "PROBE"
    GET_LOGS = "GET_LOGS"
    STOP_PLAYTEST = "STOP_PLAYTEST"


READY_LUAU = 'return #game:GetService("Players"):GetPlayers()'
READY_POLL_SECONDS = 1.0
READY_TIMEOUT_SECONDS = 45.0
# Studio registers with a freshly started proxy a few seconds after it launches.
DISCOVERY_SECONDS = 10.0

INSPECT_LUAU = """
local out = {}
for _, svc in { "Workspace", "ReplicatedStorage", "ServerScriptService", "StarterPlayer" } do
	local s = game:GetService(svc)
	local names = {}
	for _, c in s:GetChildren() do table.insert(names, c.Name .. ":" .. c.ClassName) end
	out[svc] = names
end
return game:GetService("HttpService"):JSONEncode({ placeId = game.PlaceId, tree = out })
"""

PROBE_LUAU = """
local Players = game:GetService("Players")
local players = {}
for _, p in Players:GetPlayers() do
	table.insert(players, { name = p.Name, attributes = p:GetAttributes() })
end
return game:GetService("HttpService"):JSONEncode({
	running = game:GetService("RunService"):IsRunning(),
	players = players,
})
"""

# op -> (tool, fixed arguments). Luau ops carry their snippet and target datamodel.
CALLS: dict[Op, tuple[str, dict]] = {
    Op.STUDIO_STATE: ("get_studio_state", {}),
    Op.INSPECT: ("execute_luau", {"code": INSPECT_LUAU.strip(), "datamodel_type": "Edit"}),
    Op.START_PLAYTEST: ("start_stop_play", {"is_start": True}),
    Op.PROBE: ("execute_luau", {"code": PROBE_LUAU.strip(), "datamodel_type": "Server"}),
    Op.GET_LOGS: ("get_console_output", {}),
    Op.STOP_PLAYTEST: ("start_stop_play", {"is_start": False}),
}


@dataclass
class OpResult:
    op: str
    status: str  # PASS | FAIL | ERROR | TIMEOUT | UNSUPPORTED | DRY_RUN
    tool: str | None = None
    data: object = None
    error: str | None = None
    duration_ms: int = 0
    studio_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"PASS", "DRY_RUN"}

    def to_dict(self) -> dict:
        return asdict(self) | {"ok": self.ok}


@dataclass
class Bridge:
    client: McpClient
    studio_id: str | None = None
    dry_run: bool = False
    timeout: float = 60.0
    _tools: dict[str, Tool] = field(default_factory=dict)

    def tools(self, refresh: bool = False) -> dict[str, Tool]:
        if refresh or not self._tools:
            self._tools = {t.name: t for t in self.client.list_tools()}
        return self._tools

    def run(self, op: Op | str) -> OpResult:
        op = Op(op)
        start = time.monotonic()
        try:
            result = self._dispatch(op)
        except McpError as exc:
            status = "TIMEOUT" if "timed out" in str(exc) else "ERROR"
            result = OpResult(op, status, error=str(exc))
        result.duration_ms = int((time.monotonic() - start) * 1000)
        result.studio_id = self.studio_id
        return result

    def _dispatch(self, op: Op) -> OpResult:
        if op is Op.LIST_STUDIOS:
            # Served by the proxy itself: callable even before any Studio connects,
            # when tools/list is still empty.
            deadline = time.monotonic() + DISCOVERY_SECONDS
            while True:
                result = self._call(op, Tool("list_roblox_studios"), {})
                found = isinstance(result.data, dict) and result.data.get("studios")
                if result.status != "PASS" or found or time.monotonic() >= deadline:
                    return result
                time.sleep(READY_POLL_SECONDS)
        tools = self.tools()
        if op is Op.LIST_TOOLS:
            data = {n: sorted(t.params) for n, t in sorted(tools.items())}
            return OpResult(op, "PASS", data=data)
        name, args = CALLS[op]
        if name not in tools:
            return OpResult(op, "UNSUPPORTED",
                            error=f"Studio does not offer {name!r}; available: {sorted(tools)}")
        result = self._call(op, tools[name], dict(args))
        if op is Op.START_PLAYTEST and result.status == "PASS":
            return self._wait_until_ready(result, tools["execute_luau"])
        return result

    def _wait_until_ready(self, started: OpResult, luau: Tool) -> OpResult:
        """start_stop_play returns before the server has a player; poll until it does."""
        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            probe = self._call(Op.START_PLAYTEST, luau,
                               {"code": READY_LUAU, "datamodel_type": "Server"})
            if probe.status == "PASS" and _as_int(probe.data) > 0:
                return started
            time.sleep(READY_POLL_SECONDS)
        return OpResult(Op.START_PLAYTEST, "TIMEOUT", tool=started.tool,
                        error=f"no player joined within {READY_TIMEOUT_SECONDS:.0f}s")

    def _call(self, op: Op, tool: Tool, args: dict) -> OpResult:
        if self.studio_id and "studio_id" in tool.params:
            args["studio_id"] = self.studio_id
        if self.dry_run:
            return OpResult(op, "DRY_RUN", tool=tool.name, data={"arguments": args})
        raw = self.client.call_tool(tool.name, args, timeout=self.timeout)
        data = _content(raw)
        status = "FAIL" if raw.get("isError") else "PASS"
        return OpResult(op, status, tool=tool.name, data=data,
                        error=_text(data) if status == "FAIL" else None)


def _as_int(data: object) -> int:
    try:
        return int(str(data).strip())
    except ValueError:
        return 0


def _content(raw: dict) -> object:
    """Flatten MCP tool content; decode JSON text where possible."""
    parts = []
    for item in raw.get("content", []):
        if item.get("type") != "text":
            parts.append({"type": item.get("type")})
            continue
        try:
            parts.append(json.loads(item["text"]))
        except (json.JSONDecodeError, TypeError):
            parts.append(item.get("text"))
    return parts[0] if len(parts) == 1 else parts


def _text(data: object) -> str:
    return data if isinstance(data, str) else json.dumps(data)[:2000]
