#!/usr/bin/env bash
# Create an isolated game project from the template.
# Usage: tools/new_game.sh <game_id> "<Display Name>"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ID="${1:?usage: tools/new_game.sh <game_id> \"<Display Name>\"}"
NAME="${2:-$ID}"
[[ "$ID" =~ ^[a-z][a-z0-9_]{2,40}$ ]] || { echo "game_id must be lower_snake_case" >&2; exit 2; }
DEST="$ROOT/games/$ID"
[[ -e "$DEST" ]] && { echo "games/$ID already exists" >&2; exit 2; }
cp -R "$ROOT/games/_template" "$DEST"
rm -rf "$DEST/artifacts"/*
grep -rlI "__GAME_" "$DEST" | while read -r f; do
  sed -i '' -e "s/__GAME_ID__/$ID/g" -e "s/__GAME_NAME__/$NAME/g" "$f"
done
echo "created games/$ID"
