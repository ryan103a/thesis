#!/usr/bin/env python3
"""
Stereo-calibrate two EVK4 HD cameras from E2Calib reconstructions and write
the JSON calibration file expected by metavision_stereo_matching.

Usage:
  python stereo_calib_to_prophesee.py \
      --master_dir recon_master/ --slave_dir recon_slave/ \
      --cols 9 --rows 6 --square 25 \
      --out calibration.json

--cols/--rows are INNER corners (not squares). --square is square size in millimetres.
Image pairs are matched by sorted filename order, so reconstruct both cameras
with identical timestamps (same start time and fixed time step) in E2Calib.

Pair selection pipeline:
  1. Detect the board in both images of each pair.
  2. Blur filter: drop the blurriest pairs (--blur_percentile).
  3. Temporal spacing: keep pairs at least --min_gap frames apart.
  4. Pose diversity: choose up to --max_pairs pairs that differ most in board
     position, distance and tilt (farthest-point sampling).
  5. Calibrate, then reject views with high reprojection error and recalibrate
     (--reject_factor, --min_reject_px, --reject_iters).
"""
import argparse, glob, json, os
import cv2
import numpy as np


# ---------------------------------------------------------------- detection
def find_corners(img, pattern):
    ok, corners = cv2.findChessboardCornersSB(
        img, pattern, cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY)
    if not ok:
        flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
        ok, corners = cv2.findChessboardCorners(img, pattern, flags)
        if ok:
            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4)
            corners = cv2.cornerSubPix(img, corners, (7, 7), (-1, -1), term)
    return corners if ok else None


def board_sharpness(img, corners, pad=20):
    """Variance of the Laplacian inside the board's bounding box (higher = sharper)."""
    pts = corners.reshape(-1, 2)
    x0, y0 = np.floor(pts.min(axis=0)).astype(int) - pad
    x1, y1 = np.ceil(pts.max(axis=0)).astype(int) + pad
    h, w = img.shape
    roi = img[max(y0, 0):min(y1, h), max(x0, 0):min(x1, w)]
    if roi.size == 0:
        return 0.0
    return float(cv2.Laplacian(roi, cv2.CV_64F).var())


def pose_features(corners, pattern, size):
    """Cheap descriptor of board pose: position, distance, and tilt (perspective skew)."""
    cols, rows = pattern
    w, h = size
    c = corners.reshape(rows, cols, 2)
    top = np.linalg.norm(c[0, -1] - c[0, 0])
    bottom = np.linalg.norm(c[-1, -1] - c[-1, 0])
    left = np.linalg.norm(c[-1, 0] - c[0, 0])
    right = np.linalg.norm(c[-1, -1] - c[0, -1])
    centre = c.reshape(-1, 2).mean(axis=0)
    apparent_size = np.sqrt(0.5 * (top + bottom) * 0.5 * (left + right))
    return np.array([
        centre[0] / w,
        centre[1] / h,
        0.5 * np.log(apparent_size / w),
        2.0 * np.log(top / bottom),
        2.0 * np.log(left / right),
    ])


def farthest_point_sample(feats, scores, k):
    """Greedy pick of k diverse items, starting from the sharpest."""
    n = len(feats)
    if n <= k:
        return list(range(n))
    chosen = [int(np.argmax(scores))]
    dist = np.linalg.norm(feats - feats[chosen[0]], axis=1)
    while len(chosen) < k:
        nxt = int(np.argmax(dist))
        chosen.append(nxt)
        dist = np.minimum(dist, np.linalg.norm(feats - feats[nxt], axis=1))
    return sorted(chosen)


# -------------------------------------------------------------- calibration
def run_calibration(obj_pts, m_pts, s_pts, size):
    _, K1, D1, _, _ = cv2.calibrateCamera(obj_pts, m_pts, size, None, None)
    _, K2, D2, _, _ = cv2.calibrateCamera(obj_pts, s_pts, size, None, None)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)
    rms, K1, D1, K2, D2, R, T, _, _, _, _, per_view = cv2.stereoCalibrateExtended(
        obj_pts, m_pts, s_pts, K1, D1, K2, D2, size, None, None,
        criteria=crit, flags=cv2.CALIB_FIX_INTRINSIC)
    return rms, K1, D1, K2, D2, R, T, np.asarray(per_view).reshape(-1, 2).max(axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master_dir", required=True)
    ap.add_argument("--slave_dir", required=True)
    ap.add_argument("--cols", type=int, required=True)
    ap.add_argument("--rows", type=int, required=True)
    ap.add_argument("--square", type=float, required=True, help="checkerboard square size in mm")
    ap.add_argument("--out", default="calibration.json")
    ap.add_argument("--ext", default="png")
    ap.add_argument("--blur_percentile", type=float, default=20.0,
                    help="drop this percentage of blurriest pairs (0 disables)")
    ap.add_argument("--min_gap", type=int, default=3,
                    help="minimum frame-index gap between kept pairs")
    ap.add_argument("--max_pairs", type=int, default=80,
                    help="maximum pairs to calibrate with (diversity-sampled)")
    ap.add_argument("--reject_factor", type=float, default=2.0,
                    help="reject views with error > factor x median error")
    ap.add_argument("--min_reject_px", type=float, default=0.5,
                    help="never reject views with error below this many pixels")
    ap.add_argument("--reject_iters", type=int, default=2,
                    help="rounds of outlier rejection + recalibration")
    args = ap.parse_args()

    pattern = (args.cols, args.rows)
    objp = np.zeros((args.rows * args.cols, 3), np.float32)
    square_m = args.square / 1000.0  # mm -> m, so the extrinsic translation is in metres
    objp[:, :2] = np.mgrid[0:args.cols, 0:args.rows].T.reshape(-1, 2) * square_m

    m_files = sorted(glob.glob(os.path.join(args.master_dir, f"*.{args.ext}")))
    s_files = sorted(glob.glob(os.path.join(args.slave_dir, f"*.{args.ext}")))
    if len(m_files) != len(s_files):
        raise SystemExit(f"Frame count mismatch: {len(m_files)} master vs {len(s_files)} slave")

    # ---- 1. detection ----
    total = len(m_files)
    print(f"Found {total} frame pairs. Detecting checkerboard corners...")
    cands, size = [], None
    for i, (mf, sf) in enumerate(zip(m_files, s_files)):
        mi = cv2.imread(mf, cv2.IMREAD_GRAYSCALE)
        si = cv2.imread(sf, cv2.IMREAD_GRAYSCALE)
        if mi is not None and si is not None:
            if mi.shape != si.shape:
                raise SystemExit("Master and slave image sizes differ")
            mc = find_corners(mi, pattern)
            sc = find_corners(si, pattern) if mc is not None else None
            if mc is not None and sc is not None:
                size = mi.shape[::-1]
                cands.append({
                    "idx": i, "name": os.path.basename(mf), "mc": mc, "sc": sc,
                    "sharp": min(board_sharpness(mi, mc), board_sharpness(si, sc)),
                    "feat": pose_features(mc, pattern, size),
                })
        done = i + 1
        print(f"\r  Processed {done}/{total} pairs ({100 * done // total}%) | "
              f"detected: {len(cands)} | skipped: {done - len(cands)}", end="", flush=True)
    print()
    if not cands:
        raise SystemExit("No usable pairs found. Check --cols/--rows and the reconstructions.")
    print(f"Detected in both cameras: {len(cands)} / {total}")

    # ---- 2. blur filter ----
    if args.blur_percentile > 0 and len(cands) > 10:
        thr = np.percentile([c["sharp"] for c in cands], args.blur_percentile)
        kept = [c for c in cands if c["sharp"] >= thr]
        print(f"Blur filter: dropped {len(cands) - len(kept)} blurriest pairs "
              f"(sharpness < {thr:.1f})")
        cands = kept

    # ---- 3. temporal spacing ----
    spaced, last = [], None
    for c in cands:
        if last is None or c["idx"] - last >= args.min_gap:
            spaced.append(c)
            last = c["idx"]
    print(f"Temporal spacing (>= {args.min_gap} frames): {len(cands)} -> {len(spaced)} pairs")
    cands = spaced

    # ---- 4. pose diversity ----
    feats = np.array([c["feat"] for c in cands])
    scores = np.array([c["sharp"] for c in cands])
    sel = farthest_point_sample(feats, scores, args.max_pairs)
    print(f"Pose diversity sampling (max {args.max_pairs}): {len(cands)} -> {len(sel)} pairs")
    views = [cands[j] for j in sel]
    if len(views) < 15:
        print("WARNING: fewer than ~15 pairs selected; expect an unreliable calibration")

    # ---- 5. calibrate + outlier rejection ----
    rejected = []
    for it in range(args.reject_iters + 1):
        print(f"Calibrating on {len(views)} pairs (round {it + 1})...")
        obj_pts = [objp] * len(views)
        m_pts = [v["mc"] for v in views]
        s_pts = [v["sc"] for v in views]
        rms, K1, D1, K2, D2, R, T, err = run_calibration(obj_pts, m_pts, s_pts, size)
        print(f"  Stereo RMS: {rms:.3f} px | per-view median: {np.median(err):.3f} px, "
              f"max: {err.max():.3f} px")
        if it == args.reject_iters:
            break
        thr = max(args.reject_factor * float(np.median(err)), args.min_reject_px)
        bad = [k for k in range(len(views)) if err[k] > thr]
        if not bad:
            print("  No outlier views to reject.")
            break
        if len(views) - len(bad) < 10:
            print("  WARNING: rejection would leave fewer than 10 views; stopping rejection.")
            break
        for k in bad:
            rejected.append((views[k]["name"], float(err[k])))
            print(f"  Rejected {views[k]['name']} (error {err[k]:.3f} px > {thr:.3f} px)")
        views = [v for k, v in enumerate(views) if k not in set(bad)]

    # ---- report ----
    all_pts = np.vstack([v["mc"].reshape(-1, 2) for v in views])
    cov_x = (all_pts[:, 0].max() - all_pts[:, 0].min()) / size[0] * 100
    cov_y = (all_pts[:, 1].max() - all_pts[:, 1].min()) / size[1] * 100
    print(f"\nFinal: {len(views)} pairs used, {len(rejected)} rejected as outliers")
    print(f"Stereo RMS reprojection error: {rms:.3f} px (aim for < ~0.5)")
    print(f"Baseline: {np.linalg.norm(T):.4f} m")
    print(f"Master-image corner coverage: {cov_x:.0f}% of width, {cov_y:.0f}% of height "
          f"(low values mean the edges are poorly constrained)")

    stem = os.path.splitext(args.out)[0]
    with open(stem + "_kept_pairs.txt", "w") as f:
        f.write("\n".join(v["name"] for v in views) + "\n")
    print(f"Kept pair list: {stem}_kept_pairs.txt")

    # OpenCV R,T map master(camera 1) coords -> slave(camera 2) coords, as the SDK expects
    Tm = np.eye(4)
    Tm[:3, :3] = R
    Tm[:3, 3] = T.ravel()

    def proj(K, D, desc):
        return {
            "description": desc, "type": "PINHOLE",
            "width": int(size[0]), "height": int(size[1]),
            "K": K.flatten().tolist(),
            "D": D.flatten()[:5].tolist(),
        }

    out = {
        "proj_master": proj(K1, D1, "master camera"),
        "proj_slave": proj(K2, D2, "slave camera"),
        "pose_slave_master": {"T": Tm.flatten().tolist()},
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
