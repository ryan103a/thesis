#!/usr/bin/env bash
set -u

# Edit these three paths
FOLDERS=(
  "$HOME/unsw/thesis/ros_recordings/pool-test-1-1-10-26/event_data"
  "$HOME/unsw/thesis/ros_recordings/pool-test-2-1-10-26/event_data"
  "$HOME/unsw/thesis/ros_recordings/pool-test-3-1-10-26/event_data"
)

FILES=(sync-primary.raw sync-secondary.raw)
CONVERT="$HOME/e2calib/python/convert.py"

for dir in "${FOLDERS[@]}"; do
  for f in "${FILES[@]}"; do
    path="$dir/$f"

    if [[ ! -f "$path" ]]; then
      echo "SKIP (not found): $path" >&2
      continue
    fi

    echo "Converting: $path"
    python3 "$CONVERT" "$path" || echo "FAILED: $path" >&2
  done
done

echo "Done."
