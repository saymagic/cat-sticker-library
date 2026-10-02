#!/usr/bin/env bash
set -eu
task_root="$(cd "$(dirname "$0")/.." && pwd)"
task_python="${CAT_STICKER_PYTHON:-python3}"
if [ -z "${CAT_STICKER_PYTHON:-}" ] && [ -x "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3" ]; then
  task_python="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
fi
cd "$task_root"
"$task_python" scripts/test_sticker_library.py
"$task_python" scripts/test_publish_library.py
"$task_python" scripts/publish_library.py restore
"$task_python" scripts/sticker_library.py check --deep
"$task_python" scripts/publish_library.py build
"$task_python" scripts/publish_library.py push
