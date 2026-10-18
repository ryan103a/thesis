#!/usr/bin/env bash
set -u

# Directory containing offline_reconstruction.py (EDIT THIS)
RECON_DIR="$HOME/e2calib/python"

VENV="$HOME/e2vid/.venv"
BAGS=(
  pool-test-1-1-10-26
  pool-test-2-1-10-26
  pool-test-3-1-10-26
)
FILES=(sync-primary.h5 sync-secondary.h5)

IN_ROOT="$HOME/unsw/thesis/ros_recordings"
OUT_ROOT="$HOME/unsw/thesis/reconstructions"

if [[ ! -f "$VENV/bin/activate" ]]; then
  echo "venv not found: $VENV" >&2
  exit 1
fi
if [[ ! -f "$RECON_DIR/offline_reconstruction.py" ]]; then
  echo "offline_reconstruction.py not found in: $RECON_DIR" >&2
  exit 1
fi

set +u
source "$VENV/bin/activate"
set -u

cd "$RECON_DIR" || exit 1

for bag in "${BAGS[@]}"; do
  out_dir="$OUT_ROOT/$bag"
  mkdir -p "$out_dir"

  for file in "${FILES[@]}"; do
    h5="$IN_ROOT/$bag/event_data/$file"
    dataset="${file%.h5}"   # e.g. sync-primary

    if [[ ! -f "$h5" ]]; then
      echo "SKIP (not found): $h5" >&2
      continue
    fi

    echo "Reconstructing: $h5 -> $out_dir ($dataset)"
    python offline_reconstruction.py \
      --freq_hz 10 \
      --upsample_rate 2 \
      --h5file "$h5" \
      --output_folder "$out_dir" \
      --dataset_name "$dataset" \
      --height 720 \
      --width 1280 \
      --use_gpu || echo "FAILED: $h5" >&2
  done
done

echo "Done."
