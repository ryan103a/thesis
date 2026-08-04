#!/usr/bin/env python3
"""
Camera calibration from checkerboard photos using OpenCV.

Usage:
    python calibrate_camera.py --dir /path/to/photos --cols 9 --rows 6 --square-size 25

Outputs:
    - Prints camera matrix, distortion coefficients, and reprojection error
    - Saves results to <dir>/calibration_result.npz (and .json)
    - Optionally saves annotated images and undistorted preview
"""

import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(
        description="Calibrate a camera from checkerboard images using OpenCV."
    )
    parser.add_argument(
        "--dir", "-d", required=True,
        help="Directory containing checkerboard images."
    )
    parser.add_argument(
        "--cols", type=int, default=9,
        help="Number of INTERNAL corners along the checkerboard's width (default: 9)."
    )
    parser.add_argument(
        "--rows", type=int, default=6,
        help="Number of INTERNAL corners along the checkerboard's height (default: 6)."
    )
    parser.add_argument(
        "--square-size", type=float, default=1.0,
        help="Size of one checkerboard square in real-world units (e.g. mm). "
             "Default 1.0 means intrinsics/extrinsics stay in 'square units'."
    )
    parser.add_argument(
        "--extensions", nargs="+", default=["jpg", "jpeg", "png", "bmp", "tif", "tiff"],
        help="Image file extensions to look for (default: common image formats)."
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Display each image with detected corners as it's processed."
    )
    parser.add_argument(
        "--save-annotated", action="store_true",
        help="Save copies of images with detected corners drawn, into <dir>/annotated/."
    )
    parser.add_argument(
        "--save-undistorted", action="store_true",
        help="Save an undistorted version of the first successfully processed image."
    )
    parser.add_argument(
        "--use-sb", action="store_true",
        help="Use the more robust cv2.findChessboardCornersSB detector instead of the classic one."
    )
    return parser.parse_args()


def find_images(directory, extensions):
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(directory, f"*.{ext}")))
        files.extend(glob.glob(os.path.join(directory, f"*.{ext.upper()}")))
    return sorted(set(files))


def main():
    args = parse_args()

    if not os.path.isdir(args.dir):
        print(f"Error: directory not found: {args.dir}")
        sys.exit(1)

    images = find_images(args.dir, args.extensions)
    if not images:
        print(f"Error: no images found in {args.dir} with extensions {args.extensions}")
        sys.exit(1)

    print(f"Found {len(images)} images in {args.dir}")

    checkerboard = (args.cols, args.rows)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    objp = np.zeros((checkerboard[0] * checkerboard[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:checkerboard[0], 0:checkerboard[1]].T.reshape(-1, 2)
    objp *= args.square_size

    objpoints = []
    imgpoints = []
    used_images = []
    gray_shape = None

    annotated_dir = os.path.join(args.dir, "annotated")
    if args.save_annotated:
        os.makedirs(annotated_dir, exist_ok=True)

    for fname in images:
        img = cv2.imread(fname)
        if img is None:
            print(f"  [skip] could not read {fname}")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_shape = gray.shape[::-1]

        if args.use_sb:
            ret, corners = cv2.findChessboardCornersSB(gray, checkerboard, None)
        else:
            ret, corners = cv2.findChessboardCorners(
                gray, checkerboard,
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FAST_CHECK
            )

        if ret:
            objpoints.append(objp)

            if not args.use_sb:
                corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            imgpoints.append(corners)
            used_images.append(fname)
            print(f"  [ok]   {os.path.basename(fname)}")

            if args.show or args.save_annotated:
                vis = img.copy()
                cv2.drawChessboardCorners(vis, checkerboard, corners, ret)
                if args.show:
                    cv2.imshow("Corners", vis)
                    cv2.waitKey(200)
                if args.save_annotated:
                    out_path = os.path.join(annotated_dir, os.path.basename(fname))
                    cv2.imwrite(out_path, vis)
        else:
            print(f"  [fail] corners not found in {os.path.basename(fname)}")

    if args.show:
        cv2.destroyAllWindows()

    if len(objpoints) < 3:
        print(f"\nError: only {len(objpoints)} usable image(s) found. "
              f"Need at least a handful (ideally 15-25) with clearly detected corners.")
        sys.exit(1)

    print(f"\nUsing {len(objpoints)}/{len(images)} images for calibration...")

    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, gray_shape, None, None
    )

    print("\n=== Calibration Results ===")
    print(f"Reprojection error (RMS): {ret:.4f} pixels")
    print("\nCamera matrix (intrinsics):")
    print(camera_matrix)
    print("\nDistortion coefficients (k1, k2, p1, p2, k3, ...):")
    print(dist_coeffs.ravel())

    fx, fy = camera_matrix[0, 0], camera_matrix[1, 1]
    cx, cy = camera_matrix[0, 2], camera_matrix[1, 2]
    print(f"\nfx={fx:.2f}  fy={fy:.2f}  cx={cx:.2f}  cy={cy:.2f}")

    # Per-image reprojection error breakdown
    print("\nPer-image reprojection error:")
    mean_error = 0
    per_image_errors = []
    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(
            objpoints[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs
        )
        detected = np.asarray(imgpoints[i], dtype=np.float32).reshape(-1, 2)
        projected = np.asarray(imgpoints2, dtype=np.float32).reshape(-1, 2)
        error = float(np.linalg.norm(detected - projected, axis=1).mean())
        per_image_errors.append(error)
        mean_error += error
        print(f"  {os.path.basename(used_images[i])}: {error:.4f}")
    print(f"Mean per-image error: {mean_error / len(objpoints):.4f}")

    # Save results
    npz_path = os.path.join(args.dir, "calibration_result.npz")
    np.savez(
        npz_path,
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
        rvecs=np.array(rvecs, dtype=object),
        tvecs=np.array(tvecs, dtype=object),
        reprojection_error=ret,
        image_size=gray_shape,
    )
    print(f"\nSaved: {npz_path}")

    json_path = os.path.join(args.dir, "calibration_result.json")
    with open(json_path, "w") as f:
        json.dump({
            "camera_matrix": camera_matrix.tolist(),
            "dist_coeffs": dist_coeffs.ravel().tolist(),
            "reprojection_error_rms": float(ret),
            "image_size": list(gray_shape),
            "images_used": [os.path.basename(p) for p in used_images],
            "per_image_reprojection_error": per_image_errors,
            "checkerboard_internal_corners": list(checkerboard),
            "square_size": args.square_size,
        }, f, indent=2)
    print(f"Saved: {json_path}")

    if args.save_undistorted:
        img = cv2.imread(used_images[0])
        h, w = img.shape[:2]
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
            camera_matrix, dist_coeffs, (w, h), 1, (w, h)
        )
        undistorted = cv2.undistort(img, camera_matrix, dist_coeffs, None, newcameramtx)
        out_path = os.path.join(args.dir, "undistorted_preview.jpg")
        cv2.imwrite(out_path, undistorted)
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
