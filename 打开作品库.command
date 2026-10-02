#!/bin/zsh
set -eu
task_root="${0:A:h}"
task_python="${CAT_STICKER_PYTHON:-$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
if [[ ! -x "$task_python" ]]; then task_python="$(command -v python3)"; fi
"$task_root/scripts/library.sh" refresh
exec "$task_python" "$task_root/scripts/serve_library.py" --open
