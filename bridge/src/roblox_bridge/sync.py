"""Push a Rojo project's scripts into the open Studio place (Edit DataModel).

Rojo's own sourcemap decides the file -> instance mapping. Services and the
containers Studio already has (StarterPlayerScripts, ...) are looked up, never
created. The top-most project-made Folder/Script under them is a "mount": it
is replaced as a unit and tagged ForgeManaged, so a sync never deletes
anything the bridge did not create.

The Luau that runs in Studio is the constant SYNC_LUAU; project files travel
only as JSON data that it decodes and assigns to Script.Source.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

CREATABLE = {"Folder", "Script", "LocalScript", "ModuleScript"}
SOURCE_SUFFIXES = (".luau", ".lua")
MAX_PAYLOAD_BYTES = 2_000_000
ROJO = os.path.expanduser("~/.rokit/bin/rojo")


class SyncError(ValueError):
    pass


SYNC_LUAU = """
local HttpService = game:GetService("HttpService")
local payload = HttpService:JSONDecode(__PAYLOAD__)

local function build(node, parent)
	local inst = Instance.new(node.className)
	inst.Name = node.name
	if node.source then
		inst.Source = node.source
	end
	for _, child in node.children do
		build(child, inst)
	end
	inst.Parent = parent
	return inst
end

local created = 0
for _, mount in payload.mounts do
	local parent = game:GetService(mount.path[1])
	for i = 2, #mount.path do
		parent = parent:FindFirstChild(mount.path[i])
		if parent == nil then
			error("sync: missing container " .. table.concat(mount.path, "."))
		end
	end
	local existing = parent:FindFirstChild(mount.node.name)
	if existing then
		if existing:GetAttribute("ForgeManaged") ~= true then
			error("sync: refusing to replace unmanaged " .. existing:GetFullName())
		end
		existing:Destroy()
	end
	local root = build(mount.node, parent)
	root:SetAttribute("ForgeManaged", true)
	created += 1
end
return HttpService:JSONEncode({ mounts = created, project = payload.project })
"""


def build_payload(project_dir: Path) -> dict:
    project_dir = Path(project_dir).resolve()
    if not (project_dir / "default.project.json").is_file():
        raise SyncError(f"{project_dir} has no default.project.json")
    proc = subprocess.run(
        [ROJO, "sourcemap", "default.project.json", "--include-non-scripts"],
        cwd=project_dir, capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise SyncError(f"rojo sourcemap failed: {proc.stderr.strip()[:1000]}")
    root = json.loads(proc.stdout)
    mounts: list[dict] = []
    for service in root.get("children", []):
        _collect(service, [service["name"]], project_dir, mounts)
    payload = {"project": root.get("name"), "mounts": mounts}
    if len(json.dumps(payload)) > MAX_PAYLOAD_BYTES:
        raise SyncError("project too large to sync in one call")
    return payload


def _collect(node: dict, path: list[str], project_dir: Path, mounts: list[dict]) -> None:
    for child in node.get("children", []):
        if child["className"] in CREATABLE:
            mounts.append({"path": path, "node": _tree(child, project_dir)})
        else:
            _collect(child, [*path, child["name"]], project_dir, mounts)


def _tree(node: dict, project_dir: Path) -> dict:
    cls = node["className"]
    if cls not in CREATABLE:
        raise SyncError(f"cannot sync {cls} {node['name']!r}: only scripts and folders")
    out = {"name": node["name"], "className": cls, "children": []}
    if cls != "Folder":
        files = [f for f in node.get("filePaths", []) if f.endswith(SOURCE_SUFFIXES)]
        if len(files) != 1:
            raise SyncError(f"{node['name']!r}: expected one source file, got {files}")
        source = (project_dir / files[0]).resolve()
        if project_dir not in source.parents:
            raise SyncError(f"{files[0]} is outside the project")
        out["source"] = source.read_text()
    out["children"] = [_tree(c, project_dir) for c in node.get("children", [])]
    return out


def sync_code(payload: dict) -> str:
    data = json.dumps(payload)
    level = 0
    while f"]{'=' * level}]" in data:
        level += 1
    literal = f"[{'=' * level}[{data}]{'=' * level}]"
    return SYNC_LUAU.strip().replace("__PAYLOAD__", literal)
