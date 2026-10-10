#!/usr/bin/env python3
"""Compare installed kits against controller-owned manifests and source files."""
import hashlib
import json
import sys
from pathlib import Path


def check(game: Path, require_all: bool = False) -> list[str]:
    kits = Path(__file__).resolve().parent.parent / "kits"
    catalog = {item["id"] for item in json.loads((kits / "catalog.json").read_text())}
    lock_path = game / "kits.lock.json"
    if lock_path.is_symlink():
        return ["kits.lock.json is a symlink"]
    if not lock_path.is_file():
        return ["kits.lock.json is missing"] if require_all or (game / "src/shared/Kits").exists() else []
    try:
        lock = json.loads(lock_path.read_text())
    except (ValueError, OSError) as exc:
        return [f"kits.lock.json cannot be read: {exc}"]
    errors = []
    expected_ids = catalog if require_all else set(lock)
    for kit in sorted(expected_ids):
        if kit not in catalog:
            errors.append(f"unknown kit: {kit}")
            continue
        manifest = json.loads((kits / kit / "kit.json").read_text())
        recorded = lock.get(kit)
        if not isinstance(recorded, dict):
            errors.append(f"{kit}: missing lock entry")
            continue
        if recorded.get("version") != manifest["version"]:
            errors.append(f"{kit}: version differs from controller manifest")
        expected_files = {}
        for item in manifest["files"]:
            source = kits / kit / item["from"]
            destination = game / item["to"]
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            expected_files[item["to"]] = digest
            if destination.is_symlink() or not destination.is_file():
                errors.append(f"{kit}: missing or linked {item['to']}")
            elif hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                errors.append(f"{kit}: changed {item['to']}")
        if recorded.get("files") != expected_files:
            errors.append(f"{kit}: lock file hashes differ from controller sources")
    if set(lock) - catalog:
        errors.append("lock contains unknown kits")
    return errors


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--all"):
        sys.exit("usage: check_kits.py GAME [--all]")
    problems = check(Path(sys.argv[1]).resolve(), len(sys.argv) == 3)
    if problems:
        sys.exit("kit integrity failed:\n" + "\n".join(problems))
    print("kit integrity passed")
