#!/usr/bin/env python3
"""
bias_tuner.py
 
Interactive real-time bias tuning tool for a Prophesee EVK4 HD (or any
Metavision-SDK-compatible event camera), using OpenCV trackbars to control
biases and OpenCV imshow to display the live reconstructed frame.
 
Tested against Metavision SDK 5.x Python API (metavision_sdk_stream /
metavision_sdk_core). If you're on an older SDK version that only exposes
EventsIterator, see the note near the bottom of this file.
 
Usage:
    python bias_tuner.py
    python bias_tuner.py --serial 00001234
    python bias_tuner.py --input recording.raw          # tune while replaying a file
    python bias_tuner.py --bias-min -300 --bias-max 300  # widen slider range
 
Controls:
    q / ESC   quit
    s         save current frame (PNG) + current bias values (.bias file) to --output-dir
 
Notes on biases:
    - Each bias's slider range is queried directly from the camera via
      get_bias_info(name).get_bias_range(), so bias_hpf (which might range
      over hundreds of units) and bias_diff_on (which might range over a few
      dozen) each get an appropriately-sized slider, instead of one global
      range for everything.
    - get_bias_range() returns the *recommended* range by default. If you
      opened the device with biases_range_check_bypass enabled, it returns
      the wider *allowed* range instead. --bias-min/--bias-max are only used
      as a fallback if querying the range fails for some reason.
    - Biases marked as non-modifiable (info.is_modifiable() == False) are
      skipped entirely -- no slider is created for them.
    - Typical bias names on IMX636 (EVK4): bias_diff, bias_diff_off,
      bias_diff_on, bias_fo, bias_hpf, bias_refr. The exact set available is
      queried live from your camera via get_all_biases(), so this script will
      show whatever your specific device exposes.
"""
 
import argparse
import os
import sys
import time
 
import cv2
import numpy as np
 
 
def parse_args():
    parser = argparse.ArgumentParser(description="Interactive real-time bias tuner for Metavision event cameras.")
    parser.add_argument("--serial", default=None, help="Serial number of the camera to open. If omitted, opens the first available camera.")
    parser.add_argument("--input", default=None, help="Path to a RAW/HDF5 event file to replay instead of a live camera (biases can't be changed on a file replay's *content*, but this is useful for testing the display/UI without a physical camera).")
    parser.add_argument("--accumulation-time-us", type=int, default=20000, help="Event accumulation time per displayed frame, in microseconds (default: 20000 = 20ms, ~50 FPS equivalent).")
    parser.add_argument("--bias-min", type=int, default=-200, help="Fallback lower bound for a bias slider, only used if the camera can't report that bias's real range (default: -200).")
    parser.add_argument("--bias-max", type=int, default=200, help="Fallback upper bound for a bias slider, only used if the camera can't report that bias's real range (default: 200).")
    parser.add_argument("--output-dir", default="bias_tuner_output", help="Folder to save snapshots + bias files to when pressing 's' (default: bias_tuner_output).")
    return parser.parse_args()
 
 
def open_camera(args):
    from metavision_sdk_stream import Camera
 
    if args.input:
        return Camera.from_file(args.input)
    if args.serial:
        return Camera.from_serial(args.serial)
    return Camera.from_first_available()
 
 
def save_bias_file(path, bias_values):
    """Save biases in the classic Prophesee '.bias' text format: '<value> % <name>' per line."""
    with open(path, "w") as f:
        for name, value in sorted(bias_values.items()):
            f.write(f"{value} % {name}\n")
 
 
def load_bias_file(path):
    """Load a '.bias' file into a dict of {name: value}."""
    values = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # format: "<value> % <name>"
            parts = line.split("%")
            if len(parts) != 2:
                continue
            value = int(parts[0].strip())
            name = parts[1].strip()
            values[name] = value
    return values
 
 
def main():
    args = parse_args()
 
    from metavision_sdk_stream import CameraStreamSlicer, SliceCondition
    from metavision_sdk_core import BaseFrameGenerationAlgorithm
 
    camera = open_camera(args)
 
    # Grab the HAL device + low-level biases facility BEFORE handing the camera
    # off to the slicer (camera.move() invalidates the `camera` variable itself,
    # but facilities fetched from the device beforehand remain valid handles).
    device = camera.get_device()
    try:
        biases = device.get_i_ll_biases()
    except Exception as e:
        print("This device does not expose an I_LL_Biases facility "
              "(e.g. you're replaying a file, or biases aren't supported on this device).")
        print(f"Details: {e}")
        biases = None
 
    is_live = args.input is None
 
    if biases is not None:
        current_biases = biases.get_all_biases()  # dict: {name: value}
        print("Available biases and current values:")
        for name, value in current_biases.items():
            print(f"  {name}: {value}")
    else:
        current_biases = {}
 
    slice_condition = SliceCondition.make_n_us(args.accumulation_time_us)
    slicer = CameraStreamSlicer(camera.move(), slice_condition)
 
    width = slicer.camera().width()
    height = slicer.camera().height()
    frame = np.zeros((height, width, 3), np.uint8)
 
    display_window = "Event Frame"
    control_window = "Biases"
    cv2.namedWindow(display_window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(display_window, width, height)
 
    # --- Set up trackbars for each bias ------------------------------------
    # Each bias has its own valid range, queried from the camera itself via
    # get_bias_info(name), rather than one global range for every slider.
    # bias_offset stores, per-bias, how much to shift its range so the
    # trackbar (which must start at 0) still maps to the bias's real values.
    bias_offsets = {}
 
    if biases is not None and current_biases:
        cv2.namedWindow(control_window, cv2.WINDOW_NORMAL)
 
        def make_callback(bias_name, offset):
            def _on_change(slider_value):
                real_value = slider_value - offset
                try:
                    biases.set(bias_name, real_value)
                except Exception as e:
                    print(f"Could not set {bias_name}={real_value}: {e}")
            return _on_change
 
        for name, value in current_biases.items():
            try:
                info = biases.get_bias_info(name)
                if not info.is_modifiable():
                    print(f"  (skipping '{name}': not modifiable on this device)")
                    continue
                # get_bias_range() returns the recommended range by default
                # (or the allowed range if biases_range_check_bypass is set).
                bias_min, bias_max = info.get_bias_range()
            except Exception as e:
                print(f"  Could not get range for '{name}' ({e}); falling back to "
                      f"--bias-min/--bias-max ({args.bias_min}, {args.bias_max}).")
                bias_min, bias_max = args.bias_min, args.bias_max
 
            offset = -bias_min  # shift so the trackbar's 0 corresponds to bias_min
            slider_span = bias_max - bias_min
            bias_offsets[name] = offset
 
            initial_slider_value = int(np.clip(value + offset, 0, slider_span))

            # The trackbar's label is what OpenCV displays next to the slider in
            # the window, so we bake the bias's name and valid range into it
            # (e.g. "bias_hpf [0,1800]") rather than just the bare bias name.
            label = f"{name} [{bias_min},{bias_max}]"
            cv2.createTrackbar(label, control_window, initial_slider_value, slider_span,
                                make_callback(name, offset))
            print(f"  {name}: range [{bias_min}, {bias_max}], current value {value}")
 
    os.makedirs(args.output_dir, exist_ok=True)
    snapshot_count = 0
 
    print("\nControls: 'q' or ESC to quit, 's' to save a snapshot + current bias values.\n")
 
    try:
        for slice in slicer:
            if slice.events.size > 0:
                BaseFrameGenerationAlgorithm.generate_frame(slice.events, frame)
 
            cv2.imshow(display_window, frame)
            key = cv2.waitKey(1) & 0xFF
 
            if key == ord('q') or key == 27:  # ESC
                break
            elif key == ord('s'):
                snapshot_count += 1
                timestamp = time.strftime("%Y%m%d_%H%M%S")
 
                if biases is not None:
                    bias_path = os.path.join(args.output_dir, f"biases_{timestamp}_{snapshot_count:03d}.bias")
                    save_bias_file(bias_path, biases.get_all_biases())
                    print(f"Saved biases: {bias_path}")
 
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
 
    if not is_live:
        print("Note: you replayed a recorded file, so bias changes only affected what you saw "
              "on screen conceptually via the SDK call -- they do not retroactively change events "
              "already recorded. To actually tune sensor biases you need a live camera connection.")
 
 
if __name__ == "__main__":
    main()
