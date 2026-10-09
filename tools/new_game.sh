#!/usr/bin/env bash
# Create an isolated game project from the template.
# Usage: tools/new_game.sh <game_id> "<Display Name>"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ID="${1:?usage: tools/new_game.sh <game_id> \"<Display Name>\"}"
NAME="${2:-$ID}"
[[ "$ID" =~ ^[a-z][a-z0-9_]{2,40}$ ]] || { echo "game_id must be lower_snake_case" >&2; exit 2; }
if [[ -z "${NAME//[[:space:]]/}" || "$NAME" == *[$'\n'$'\r'$'\t']* ]]; then
  echo "display name must be non-empty and contain no control characters" >&2
  exit 2
fi
DEST="$ROOT/games/$ID"
[[ -e "$DEST" ]] && { echo "games/$ID already exists" >&2; exit 2; }
cp -R "$ROOT/games/_template" "$DEST"
rm -rf "$DEST/artifacts"/*
python3 - "$DEST" "$ID" "$NAME" <<'PY'
from pathlib import Path
import json
import sys

dest, game_id, name = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
if not name.strip() or any(ord(char) < 32 for char in name):
    raise SystemExit("display name must be non-empty and contain no control characters")
for path in dest.rglob("*"):
    if not path.is_file():
        continue
    try:
        content = path.read_text()
    except UnicodeDecodeError:
        continue
    if path.name == "forge_game.yaml":
        content = content.replace("name: __GAME_NAME__", "name: " + json.dumps(name))
    # Inside JSON strings the name must be JSON-escaped (quotes, backslashes).
    shown = json.dumps(name)[1:-1] if path.suffix == ".json" else name
    updated = content.replace("__GAME_ID__", game_id).replace("__GAME_NAME__", shown)
    if updated != content:
        path.write_text(updated)
PY
echo "created games/$ID"
