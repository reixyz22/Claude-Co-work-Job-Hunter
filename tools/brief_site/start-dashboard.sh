#!/usr/bin/env bash
# Convenience launcher. Drains anything queued, rebuilds, then serves.
cd "$(dirname "$0")"
python3 drain_queue.py --root "${JOBHUNT_ROOT:-$HOME/mnt/Claude}" --dry-run
exec python3 serve.py --root "${JOBHUNT_ROOT:-$HOME/mnt/Claude}" "$@"
