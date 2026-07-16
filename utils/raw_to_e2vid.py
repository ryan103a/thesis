#!/usr/bin/env parser
import os
import argparse
from metavision_core.event_io import EventsIterator

def convert_raw_to_text(input_path, output_path, time_offset=0.0):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        return

    # Initialize the iterator to read the RAW or DAT file
    mv_iterator = EventsIterator(input_path=input_path, relative_timestamps=False)
    
    # Extract dimensions from file metadata
    height, width = mv_iterator.get_size()
    if width is None or height is None:
        # Fallback to EVK4-HD native resolution if metadata isn't present
        width, height = 1280, 720 

    print(f"Processing: {input_path}")
    print(f"Sensor Resolution: {width}x{height}")
    if time_offset != 0.0:
        print(f"Applying Unix epoch time offset: {time_offset}")
    
    print(f"Writing text output to: {output_path}...")

    with open(output_path, "w") as f:
        # 1. Write the spatial resolution header expected by loaders like E2VID
        f.write(f"{width} {height}\n")
        
        # 2. Stream through chunks to maintain a low memory footprint
        total_events = 0
        for events in mv_iterator:
            # Convert internal integer microseconds to seconds float + offset
            timestamps_sec = (events['t'] / 1e6) + time_offset
            
            # Vectorized formatting for speed
            lines = [
                f"{t:.12f} {ev['x']} {ev['y']} {ev['p']}\n"
                for t, ev in zip(timestamps_sec, events)
            ]
            f.writelines(lines)
            
            total_events += len(events)
            if total_events % 10_000_000 == 0:
                print(f" -> Exported {total_events:,} events...")

    print(f"Success! Total events written: {total_events:,}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert Prophesee EVK4-HD (.raw/.dat) event streams to standard space-delimited text format."
    )
    
    # Positional or named arguments for input/output files
    parser.add_argument("-i", "--input", required=True, help="Path to the source binary .raw or .dat file.")
    parser.add_argument("-o", "--output", required=True, help="Path to save the converted .txt output file.")
    
    # Optional offset argument for Unix epoch alignment
    parser.add_argument(
        "--offset", 
        type=float, 
        default=0.0, 
        help="Optional Unix timestamp float to offset the starting time (useful for MVSEC/E2VID alignment)."
    )

    args = parser.parse_args()
    
    convert_raw_to_text(input_path=args.input, output_path=args.output, time_offset=args.offset)
