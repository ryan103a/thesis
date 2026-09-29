#!/bin/bash
# Usage: ./convert_to_db3.sh <bag_name>
# Converts /home/ryan/unsw/thesis/ros_recordings/<bag_name> (mcap) to <bag_name>_db3 (sqlite3)

DATASET_ROOT="/home/ryan/unsw/thesis/ros_recordings"

if [ -z "$1" ]; then
    echo "Usage: $0 <bag_name>"
    exit 1
fi

INPUT_DIR="$DATASET_ROOT/$1"
OUTPUT_DIR="$DATASET_ROOT/${1}_db3"

if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: Input bag '$INPUT_DIR' does not exist."
    exit 1
fi

if [ -d "$OUTPUT_DIR" ]; then
    echo "ERROR: Output bag '$OUTPUT_DIR' already exists."
    exit 1
fi

CONFIG=$(mktemp /tmp/convert_XXXXXX.yaml)
trap 'rm -f "$CONFIG"' EXIT

cat > "$CONFIG" <<EOF
output_bags:
  - uri: $OUTPUT_DIR
    storage_id: sqlite3
    all: true
EOF

echo "Converting $INPUT_DIR -> $OUTPUT_DIR"
ros2 bag convert -i "$INPUT_DIR" -o "$CONFIG"
