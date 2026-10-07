#!/usr/bin/env bash
# Checks that need no test framework: the package must compile, every theme
# must resolve to real files, and every theme must clear the contrast floor.
#
# usage: scripts/dev.sh check|test
set -euo pipefail

app="$(cd "$(dirname "$0")/../app" && pwd)"
python="${THEME_PYTHON:-python3}"
export PYTHONPATH="$app"

case "${1:-}" in
  check)
    echo "› compiling package"
    "$python" -m compileall -q "$app/theme"
    echo "› resolving every theme"
    "$python" -m theme doctor
    ;;
  test)
    echo "› contrast audit"
    "$python" -m theme contrast
    ;;
  *)
    echo "usage: scripts/dev.sh check|test" >&2
    exit 2
    ;;
esac
