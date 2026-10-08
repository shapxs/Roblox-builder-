"""Push a Rojo project's scripts into the open Studio place (Edit DataModel).

Rojo's own sourcemap decides the file -> instance mapping. Services and the
containers Studio already has (StarterPlayerScripts, ...) are looked up, never
created. The top-most project-made Folder/Script under them is a "mount",
tagged ForgeManaged.

Every sync is a full reconcile: all ForgeManaged mounts in the place are removed
and the project's mounts rebuilt, so deleted or renamed scripts never survive and
switching games leaves nothing behind. Nothing the bridge did not create is ever
touched; a name collision with an unmanaged instance aborts before any change.

Sync reproduces scripts and folders only. Projects that rely on what it cannot
reproduce (.meta.json properties, $properties/$attributes, models, values) are
rejected rather than silently tested in a different shape.

The Luau that runs in Studio is the constant SYNC_LUAU; project files travel only
as JSON data that it decodes and assigns to Script.Source. Rojo is invoked as a
pinned, checksum-verified binary, never through a tool manager that a project's
own files could redirect.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

CREATABLE = {"Folder", "Script", "LocalScript", "ModuleScript"}
SOURCE_SUFFIXES = (".luau", ".lua")
MAX_PAYLOAD_BYTES = 2_000_000
ROJO = os.environ.get("ROBLOX_BRIDGE_ROJO",
                      os.path.expanduser("~/.rokit/tool-storage/rojo-rbx/rojo/7.7.1/rojo"))
ROJO_SHA256 = os.environ.get(
    "ROBLOX_BRIDGE_ROJO_SHA256",
    "eb179af987248d13cbde0241b129e4c826aea870cfcd3c234fe19dd645acd01c")  # Rojo 7.7.1 macOS


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

local function container(path)
	local parent = game:GetService(path[1])
	for i = 2, #path do
		parent = parent:FindFirstChild(path[i])
		if parent == nil then
			error("sync: missing container " .. table.concat(path, "."))
		end
	end
	return parent
end

-- Validate everything before changing anything.
local parents = {}
for i, mount in payload.mounts do
	local parent = container(mount.path)
	local existing = parent:FindFirstChild(mount.node.name)
	if existing and existing:GetAttribute("ForgeManaged") ~= true then
		error("sync: refusing to replace unmanaged " .. existing:GetFullName())
	end
	parents[i] = parent
end

-- Full reconcile: remove every mount from earlier syncs (any game), then rebuild.
local removed = 0
for _, inst in game:GetDescendants() do
	if inst:GetAttribute("ForgeManaged") == true and inst.Parent ~= nil then
		inst:Destroy()
		removed += 1
	end
end
for i, mount in payload.mounts do
	build(mount.node, parents[i]):SetAttribute("ForgeManaged", true)
end
return HttpService:JSONEncode({
	mounts = #payload.mounts, removed = removed, project = payload.project,
	source_sha256 = payload.source_sha256,
})
"""


def rojo_binary() -> str:
    """The pinned Rojo executable, refused if its bytes are not the expected build."""
    path = Path(ROJO)
    if not path.is_file() or path.is_symlink():
        raise SyncError(f"pinned Rojo binary missing at {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != ROJO_SHA256:
        raise SyncError(f"Rojo binary at {path} has unexpected sha256 {digest[:12]}")
    return str(path)


def build_payload(project_dir: Path) -> dict:
    project_dir = Path(project_dir).resolve()
    project_file = project_dir / "default.project.json"
    if not project_file.is_file():
        raise SyncError(f"{project_dir} has no default.project.json")
    _reject_unsupported_project(project_dir, project_file)
    proc = subprocess.run(
        [rojo_binary(), "sourcemap", "default.project.json", "--include-non-scripts"],
        cwd=project_dir, capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise SyncError(f"rojo sourcemap failed: {proc.stderr.strip()[:1000]}")
    root = json.loads(proc.stdout)
    mounts: list[dict] = []
    for service in root.get("children", []):
        _collect(service, [service["name"]], project_dir, mounts)
    payload = {"project": root.get("name"), "mounts": mounts}
    payload["source_sha256"] = source_sha256(mounts)
    if len(json.dumps(payload)) > MAX_PAYLOAD_BYTES:
        raise SyncError("project too large to sync in one call")
    return payload


def source_sha256(mounts: list[dict]) -> str:
    """Identity of exactly what a sync puts in Studio: paths, classes, names, sources."""
    canonical = json.dumps(mounts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _reject_unsupported_project(project_dir: Path, project_file: Path) -> None:
    def walk(node: object, where: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("$properties", "$attributes"):
                    raise SyncError(f"{where}: {key} is not reproduced by sync")
                walk(value, f"{where}.{key}")

    try:
        walk(json.loads(project_file.read_text()).get("tree", {}), "tree")
    except json.JSONDecodeError as exc:
        raise SyncError(f"default.project.json is not valid JSON: {exc}") from exc
    for path in project_dir.rglob("*"):
        rel = path.relative_to(project_dir)
        if rel.parts[0] in (".git", "artifacts", "Packages", "ServerPackages"):
            continue
        if path.is_symlink():
            raise SyncError(f"{rel}: symlinks are not allowed in a synced project")
        if path.name.endswith(".meta.json"):
            raise SyncError(f"{rel}: .meta.json properties are not reproduced by sync")


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
            raise SyncError(f"{node['name']!r}: expected one source file, got "
                            f"{node.get('filePaths')}")
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
