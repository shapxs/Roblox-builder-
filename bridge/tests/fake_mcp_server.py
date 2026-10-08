"""Scriptable stand-in for Studio's MCP proxy, driven by the FAKE_MCP env var (JSON):

  tools:   [{name, params: [..]}]         tools to advertise
  studios: [..]                           list_roblox_studios payload
  errors:  [tool names]                   tools that return isError
  hang:    [tool names]                   tools that never answer
  log:     path                           append every tools/call as a JSON line
"""
import json
import os
import sys

cfg = json.loads(os.environ.get("FAKE_MCP", "{}"))
# Like the real proxy, list_roblox_studios is callable but never advertised.
tools = cfg.get("tools", [])


def schema(params):
    return {"type": "object", "properties": {p: {"type": "string"} for p in params},
            "required": [p for p in params if p != "studio_id"]}


def reply(rid, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    msg = json.loads(line)
    method, rid = msg.get("method"), msg.get("id")
    if method == "initialize":
        reply(rid, {"protocolVersion": "2025-06-18", "serverInfo": {"name": "fake"}})
    elif method == "tools/list":
        # A stray notification first, to prove the client skips it.
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/x"}) + "\n")
        reply(rid, {"tools": [{"name": t["name"], "description": "",
                               "inputSchema": schema(t["params"])} for t in tools]})
    elif method == "tools/call":
        name, args = msg["params"]["name"], msg["params"]["arguments"]
        if cfg.get("log"):
            with open(cfg["log"], "a") as f:
                f.write(json.dumps({"name": name, "arguments": args}) + "\n")
        if name in cfg.get("hang", []):
            continue
        if name == "list_roblox_studios":
            text = json.dumps({"studios": cfg.get("studios", [])})
        else:
            text = json.dumps({"tool": name, "ok": True})
        reply(rid, {"content": [{"type": "text", "text": text}],
                    "isError": name in cfg.get("errors", [])})
