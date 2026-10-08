"""Minimal MCP stdio client (JSON-RPC 2.0, newline-delimited) with hard timeouts."""
from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from dataclasses import dataclass, field

STUDIO_MCP = "/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP"
PROTOCOL_VERSION = "2025-06-18"


class McpError(RuntimeError):
    """Transport failure, timeout, or JSON-RPC error from the server."""


@dataclass
class Tool:
    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)

    @property
    def params(self) -> set[str]:
        return set(self.input_schema.get("properties", {}))


class McpClient:
    def __init__(self, command: list[str] | None = None, *, timeout: float = 30.0) -> None:
        self.command = command or [STUDIO_MCP, "--stdio"]
        self.timeout = timeout
        self._proc: subprocess.Popen | None = None
        self._next_id = 0
        self._buffer = b""

    def __enter__(self) -> McpClient:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def start(self) -> dict:
        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        info = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "forge-roblox-bridge", "version": "0.1.0"},
            },
        )
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return info

    def close(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None

    def list_tools(self) -> list[Tool]:
        result = self.request("tools/list", {})
        return [
            Tool(t["name"], t.get("description", ""), t.get("inputSchema") or {})
            for t in result.get("tools", [])
        ]

    def call_tool(self, name: str, arguments: dict, *, timeout: float | None = None) -> dict:
        return self.request("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)

    def request(self, method: str, params: dict, *, timeout: float | None = None) -> dict:
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.monotonic() + (timeout or self.timeout)
        while True:
            msg = self._read(deadline)
            if msg.get("id") != rid:
                continue  # notifications and stray responses are not ours
            if "error" in msg:
                raise McpError(f"{method}: {msg['error']}")
            return msg.get("result") or {}

    def _send(self, msg: dict) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise McpError("client not started")
        try:
            self._proc.stdin.write(json.dumps(msg).encode() + b"\n")
            self._proc.stdin.flush()
        except BrokenPipeError as exc:
            raise McpError("MCP server exited") from exc

    def _read(self, deadline: float) -> dict:
        assert self._proc is not None and self._proc.stdout is not None
        fd = self._proc.stdout.fileno()
        with selectors.DefaultSelector() as sel:
            sel.register(fd, selectors.EVENT_READ)
            while b"\n" not in self._buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise McpError("timed out waiting for MCP response")
                if not sel.select(remaining):
                    continue
                chunk = os.read(fd, 65536)
                if not chunk:
                    raise McpError("MCP server closed its output")
                self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise McpError(f"malformed MCP message: {line[:200]!r}") from exc
