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
import hashlib, json, shutil, sys
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
lock = json.loads(lock_path.read_text()) if lock_path.is_file() else {}
for kit in wanted:
    manifest = json.loads((kits_root / kit / "kit.json").read_text())
    recorded = lock.get(kit, {}).get("files", {})
    installed = {}
    for item in manifest["files"]:
        src, dst = kits_root / kit / item["from"], game / item["to"]
        if dst.exists() and sha(dst) != sha(src) and recorded.get(item["to"]) != sha(dst):
            sys.exit(f"{item['to']} was changed in this game; not overwriting (kit {kit})")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        installed[item["to"]] = sha(dst)
    lock[kit] = {"version": manifest["version"], "files": installed}
    print(f"installed {kit} {manifest['version']}")
lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
PY
