#!/usr/bin/env bash
# Static gates R03-R07 + R10 for one game. Usage: tools/check.sh games/<id>
# Exits non-zero on the first failing gate. Every gate runs offline.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GAME="$(cd "${1:?usage: tools/check.sh games/<id>}" && pwd)"
POLICY="$ROOT/policy/$(basename "$GAME")"
if [[ ! -d "$POLICY/tests" && ! -d "$POLICY/scenarios" ]]; then
  POLICY="$ROOT/policy/_baseline"
fi
if [[ ! -f "$POLICY/tests/run.luau" ]]; then
  echo "required policy test missing: $POLICY/tests/run.luau" >&2
  exit 1
fi
export PATH="$HOME/.rokit/bin:$PATH"
cd "$GAME"
mkdir -p artifacts

gate() { printf '%-10s ' "$1"; shift; if out="$("$@" 2>&1)"; then echo PASS; else echo FAIL; echo "$out" | tail -40; exit 1; fi; }

if [[ "$GAME" == "$ROOT/forge-games/"* ]]; then
  gate kits python3 "$ROOT/tools/check_kits.py" "$GAME" --all
else
  gate kits python3 "$ROOT/tools/check_kits.py" "$GAME"
fi

gate format    stylua --check src tests
gate lint      selene src
gate sourcemap rojo sourcemap default.project.json --output artifacts/sourcemap.json
gate typecheck luau-lsp analyze --platform=roblox \
  --definitions="$ROOT/tools/types/globalTypes.d.luau" \
  --sourcemap=artifacts/sourcemap.json --flag:LuauSolverV2=false src
gate unit      lune run tests/run.luau
# Controller-owned invariants (policy/<game> or policy/_baseline), outside the game repo.
gate policy  env GAME_ROOT="$GAME" lune run "$POLICY/tests/run.luau"
gate build     rojo build default.project.json --output artifacts/place.rbxlx
