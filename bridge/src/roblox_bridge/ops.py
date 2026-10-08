"""Whitelisted Studio operations.

Jobs name an operation; they never supply tool names or Luau. Every tool name and
every Luau snippet that can reach Studio is a constant in this file.

The built-in Studio MCP only lists its full tool surface while a Studio session is
connected, so names are resolved at runtime from `tools/list` against candidate lists.
Only `list_roblox_studios` has been seen live so far; the other candidates come from
Roblox's published MCP servers and must be confirmed with `roblox-bridge tools`
while Studio is open (see docs/roblox/HOST_BRIDGE.md).
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
    INSPECT = "INSPECT"
    START_PLAYTEST = "START_PLAYTEST"
    PROBE = "PROBE"
    GET_LOGS = "GET_LOGS"
    STOP_PLAYTEST = "STOP_PLAYTEST"


# Each op tries these (tool, fixed arguments) pairs in order; first tool present wins.
CANDIDATES: dict[Op, list[tuple[str, dict]]] = {
    Op.START_PLAYTEST: [
        ("start_playtest", {}),
        ("start_stop_play", {"mode": "start_play"}),
    ],
    Op.STOP_PLAYTEST: [
        ("stop_playtest", {}),
        ("start_stop_play", {"mode": "stop"}),
    ],
    Op.GET_LOGS: [
        ("get_output_logs", {}),
        ("get_console_output", {}),
    ],
}

# Tools that execute Luau; the snippet goes into the tool's single required string param.
RUN_CODE_TOOLS = ["run_code", "execute_luau", "run_luau", "execute_code"]
RUNTIME_EVAL_TOOLS = ["eval_server_runtime", "run_script_in_play_mode", *RUN_CODE_TOOLS]

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
            return self._call(op, Tool("list_roblox_studios"), {})
        tools = self.tools()
        if op is Op.LIST_TOOLS:
            data = {n: sorted(t.params) for n, t in sorted(tools.items())}
            return OpResult(op, "PASS", data=data)
        if op is Op.INSPECT:
            return self._run_luau(op, RUN_CODE_TOOLS, INSPECT_LUAU)
        if op is Op.PROBE:
            return self._run_luau(op, RUNTIME_EVAL_TOOLS, PROBE_LUAU)
        for name, args in CANDIDATES[op]:
            if name in tools:
                return self._call(op, tools[name], dict(args))
        return self._unsupported(op, [n for n, _ in CANDIDATES[op]])

    def _run_luau(self, op: Op, candidates: list[str], snippet: str) -> OpResult:
        tools = self.tools()
        for name in candidates:
            tool = tools.get(name)
            param = _code_param(tool) if tool else None
            if tool and param:
                return self._call(op, tool, {param: snippet.strip()})
        return self._unsupported(op, candidates)

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

    def _unsupported(self, op: Op, wanted: list[str]) -> OpResult:
        return OpResult(op, "UNSUPPORTED",
                        error=f"none of {wanted} offered; available: {sorted(self.tools())}")


def _code_param(tool: Tool) -> str | None:
    props = tool.input_schema.get("properties", {})
    required = tool.input_schema.get("required", list(props))
    strings = [p for p in required if props.get(p, {}).get("type") == "string"
               and p != "studio_id"]
    return strings[0] if len(strings) == 1 else None


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
