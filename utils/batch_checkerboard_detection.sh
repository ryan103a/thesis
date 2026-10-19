#!/usr/bin/env bash
set -u

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Usage: $0 names.txt" >&2
  exit 1
fi

CONFIG="$1"
SCRIPT="$HOME/unsw/thesis/utils/checkerboard_detection.py"
IN_ROOT="$HOME/unsw/thesis/reconstructions"
OUT_ROOT="$HOME/unsw/thesis/checkerboard_detections"
COLS=12
ROWS=8

if [[ ! -f "$SCRIPT" ]]; then
  echo "script not found: $SCRIPT" >&2
  exit 1
fi

BAGS=()
FOLDERS=()
section=""

while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%$'\r'}"                      # strip Windows line endings
  line="${line#"${line%%[![:space:]]*}"}"   # trim leading whitespace
  line="${line%"${line##*[![:space:]]}"}"   # trim trailing whitespace
  [[ -z "$line" || "$line" == \#* ]] && continue

  case "$line" in
    "[bags]")    section="bags";    continue ;;
    "[folders]") section="folders"; continue ;;
  esac

  case "$section" in
    bags)    BAGS+=("$line") ;;
    folders) FOLDERS+=("$line") ;;
    *) echo "Ignoring line outside a [bags]/[folders] section: $line" >&2 ;;
  esac
done < "$CONFIG"

if [[ ${#BAGS[@]} -eq 0 || ${#FOLDERS[@]} -eq 0 ]]; then
  echo "Need at least one entry under both [bags] and [folders] in $CONFIG" >&2
  exit 1
fi

for bag in "${BAGS[@]}"; do
  for folder in "${FOLDERS[@]}"; do
    in_dir="$IN_ROOT/$bag/$folder"
    out_dir="$OUT_ROOT/$bag/$folder"

    if [[ ! -d "$in_dir" ]]; then
      echo "SKIP (not found): $in_dir" >&2
      continue
    fi

    mkdir -p "$out_dir"
    echo "Detecting: $in_dir -> $out_dir"
    python3 "$SCRIPT" \
      --input_dir "$in_dir" \
      --output_dir "$out_dir" \
      --cols "$COLS" \
      --rows "$ROWS" || echo "FAILED: $in_dir" >&2
  done
done

echo "Done."
