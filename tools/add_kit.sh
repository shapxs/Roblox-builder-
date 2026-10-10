#!/usr/bin/env bash
# Install system kits into a game. Usage:
#   tools/add_kit.sh games/<id> <kit> [<kit> ...]
#   tools/add_kit.sh games/<id> --all
# Files go where each kit's kit.json says; kits.lock.json in the game records what is
# installed. A file the game has changed since install is never overwritten.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GAME="$(cd "${1:?usage: tools/add_kit.sh games/<id> <kit>...|--all}" && pwd)"
shift
exec python3 - "$ROOT/kits" "$GAME" "$@" <<'PY'
import hashlib, json, os, sys, tempfile
from pathlib import Path

kits_root, game, wanted = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
if not wanted:
    sys.exit("name at least one kit, or --all")
if not (game / "default.project.json").is_file():
    sys.exit(f"{game} is not a Rojo game (no default.project.json)")
catalog = {k["id"]: k for k in json.loads((kits_root / "catalog.json").read_text())}
if wanted == ["--all"]:
    wanted = sorted(catalog)
unknown = [k for k in wanted if k not in catalog]
if unknown:
    sys.exit(f"unknown kits: {unknown}; available: {sorted(catalog)}")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

lock_path = game / "kits.lock.json"
if lock_path.is_symlink():
    sys.exit("kits.lock.json must not be a symlink")
lock = json.loads(lock_path.read_text()) if lock_path.is_file() else {}
updated = dict(lock)
planned = []
destinations = set()

def safe_file(root: Path, relative: str, *, source: bool) -> Path:
    name = Path(relative)
    if name.is_absolute() or not name.parts or any(p in (".", "..") for p in name.parts):
        sys.exit(f"unsafe kit path: {relative}")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        sys.exit(f"kit path escapes its root: {relative}")
    for component in (path, *path.parents):
        if component == root:
            break
        if component.is_symlink():
            sys.exit(f"kit path contains a symlink: {relative}")
    if source and not path.is_file():
        sys.exit(f"kit source is missing: {relative}")
    return path

# Finish every conflict and containment check before changing the game tree.
for kit in wanted:
    manifest = json.loads((kits_root / kit / "kit.json").read_text())
    if manifest.get("id") != kit:
        sys.exit(f"kit manifest id mismatch: {kit}")
    recorded = lock.get(kit, {}).get("files", {})
    installed = {}
    for item in manifest["files"]:
        src = safe_file(kits_root / kit, item["from"], source=True)
        dst = safe_file(game, item["to"], source=False)
        if dst in destinations:
            sys.exit(f"duplicate kit destination: {item['to']}")
        destinations.add(dst)
        if dst.exists() and not dst.is_file():
            sys.exit(f"kit destination is not a file: {item['to']}")
        data = src.read_bytes()
        new_hash = hashlib.sha256(data).hexdigest()
        if dst.exists() and sha(dst) != new_hash and recorded.get(item["to"]) != sha(dst):
            sys.exit(f"{item['to']} was changed in this game; not overwriting (kit {kit})")
        planned.append((dst, data, src.stat().st_mode, item["to"]))
        installed[item["to"]] = new_hash
    updated[kit] = {"version": manifest["version"], "files": installed}

old_files = {dst: (dst.read_bytes(), dst.stat().st_mode) if dst.exists() else None
             for dst, _, _, _ in planned}
old_lock = lock_path.read_bytes() if lock_path.exists() else None
written = []
created_dirs = []
with tempfile.TemporaryDirectory(prefix="kit-install-", dir=game.parent) as temp:
    staging = Path(temp)
    try:
        for index, (dst, data, mode, label) in enumerate(planned):
            missing = []
            parent = dst.parent
            while parent != game and not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                created_dirs.append(directory)
            # A concurrent replacement must not turn a checked path into a link.
            safe_file(game, label, source=False)
            staged = staging / str(index)
            staged.write_bytes(data)
            os.chmod(staged, mode & 0o777)
            os.replace(staged, dst)
            written.append(dst)
        staged_lock = staging / "lock.json"
        staged_lock.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n")
        os.replace(staged_lock, lock_path)
    except Exception:
        for dst in reversed(written):
            previous = old_files[dst]
            if previous is None:
                dst.unlink(missing_ok=True)
            else:
                restore = staging / ("restore-" + str(len(written)))
                restore.write_bytes(previous[0])
                os.chmod(restore, previous[1] & 0o777)
                os.replace(restore, dst)
        if old_lock is None:
            lock_path.unlink(missing_ok=True)
        else:
            restore_lock = staging / "restore-lock"
            restore_lock.write_bytes(old_lock)
            os.replace(restore_lock, lock_path)
        for directory in reversed(created_dirs):
            directory.rmdir()
        raise
for kit in wanted:
    print(f"installed {kit} {updated[kit]['version']}")
PY
