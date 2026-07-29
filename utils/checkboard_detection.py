#!/usr/bin/env python3
"""
detect_checkerboard.py

Scan a folder of images (e.g. grayscale frames reconstructed from event camera
data) for a checkerboard calibration pattern using OpenCV, and copy/save only
the images where detection succeeded into an output folder, with the detected
corners drawn on for visual verification.

Usage:
    python detect_checkerboard.py --input_dir frames/ --output_dir detected/ \
        --cols 9 --rows 6

Notes:
    --cols / --rows refer to the number of INTERNAL corners of the checkerboard
    (i.e. one less than the number of squares in each direction). E.g. a
    standard 10x7 square checkerboard has 9x6 internal corners.
"""

import argparse
import os
import sys
import csv

import cv2
import numpy as np


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".pgm", ".ppm"}


def parse_args():
    parser = argparse.ArgumentParser(description="Detect checkerboard patterns in a folder of images.")
    parser.add_argument("--input_dir", required=True, help="Folder containing input images.")
    parser.add_argument("--output_dir", required=True, help="Folder to write successful detections to.")
    parser.add_argument("--cols", type=int, default=9, help="Number of internal corners per row (default: 9).")
    parser.add_argument("--rows", type=int, default=6, help="Number of internal corners per column (default: 6).")
    parser.add_argument(
        "--use_sb",
        action="store_true",
        help="Use cv2.findChessboardCornersSB (newer, often more robust to low contrast/noise) "
             "instead of the classic cv2.findChessboardCorners.",
    )
    parser.add_argument(
        "--no_subpixel",
        action="store_true",
        help="Skip sub-pixel corner refinement (only applies to the classic detector).",
    )
    parser.add_argument(
        "--save_raw_copies",
        action="store_true",
        help="Also save an unannotated copy of each successful image (alongside the annotated one).",
    )
    return parser.parse_args()


def find_images(input_dir):
    files = []
    for name in sorted(os.listdir(input_dir)):
        ext = os.path.splitext(name)[1].lower()
        if ext in IMAGE_EXTS:
            files.append(name)
    return files


def detect_corners(gray, pattern_size, use_sb, refine_subpixel):
    """Run checkerboard detection on a grayscale image. Returns (success, corners)."""
    if use_sb:
        flags = cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY
        found, corners = cv2.findChessboardCornersSB(gray, pattern_size, flags=flags)
        return found, corners

    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FAST_CHECK
    found, corners = cv2.findChessboardCorners(gray, pattern_size, flags=flags)

    if found and refine_subpixel:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

    return found, corners


def main():
    args = parse_args()
    pattern_size = (args.cols, args.rows)

    if not os.path.isdir(args.input_dir):
        print(f"Error: input_dir '{args.input_dir}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    if args.save_raw_copies:
        os.makedirs(os.path.join(args.output_dir, "raw"), exist_ok=True)

    image_names = find_images(args.input_dir)
    if not image_names:
        print(f"No images found in '{args.input_dir}'.")
        return

    print(f"Found {len(image_names)} images. Looking for a {pattern_size[0]}x{pattern_size[1]} "
          f"internal-corner checkerboard...")

    results = []
    num_success = 0

    for name in image_names:
        path = os.path.join(args.input_dir, name)
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)

        if img is None:
            print(f"  [skip] Could not read: {name}")
            results.append((name, False, "unreadable"))
            continue

        # Ensure grayscale for detection, but keep a BGR version for drawing.
        if img.ndim == 2:
            gray = img
            bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.ndim == 3 and img.shape[2] == 3:
            bgr = img
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            print(f"  [skip] Unexpected image shape {img.shape}: {name}")
            results.append((name, False, "bad_shape"))
            continue

        found, corners = detect_corners(gray, pattern_size, args.use_sb, not args.no_subpixel)

        if found:
            num_success += 1
            annotated = bgr.copy()
            cv2.drawChessboardCorners(annotated, pattern_size, corners, found)

            out_path = os.path.join(args.output_dir, name)
            cv2.imwrite(out_path, annotated)

            if args.save_raw_copies:
                cv2.imwrite(os.path.join(args.output_dir, "raw", name), bgr)

            print(f"  [ok]   {name}")
            results.append((name, True, ""))
        else:
            print(f"  [miss] {name}")
            results.append((name, False, "not_detected"))

    # Write a summary CSV log.
    log_path = os.path.join(args.output_dir, "detection_log.csv")
    with open(log_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "detected", "reason"])
        writer.writerows(results)

    print(f"\nDone. {num_success}/{len(image_names)} images had a successful detection.")
    print(f"Annotated detections saved to: {args.output_dir}")
    print(f"Log saved to: {log_path}")


if __name__ == "__main__":
    main()
