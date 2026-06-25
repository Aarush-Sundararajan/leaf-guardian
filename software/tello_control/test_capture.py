"""
Camera capture test for DJI Tello.

Starts the video stream, takes off, hovers briefly, grabs a single frame,
saves it as a JPEG, then lands. Verifies that streamon() initialises cleanly
and that get_frame_read().frame produces a usable image before the full
waypoint mission is attempted.

Usage (from repo root):
    py software/tello_control/test_capture.py
"""

import os
import time

import cv2
import numpy as np
from djitellopy import Tello

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
_IMG_DIR   = os.path.join(_REPO_ROOT, 'data', 'drone_imagery')
RAW_PATH   = os.path.join(_IMG_DIR, 'test_capture_raw.jpg')
PATH_A     = os.path.join(_IMG_DIR, 'test_capture_methodA.jpg')
PATH_B     = os.path.join(_IMG_DIR, 'test_capture_methodB.jpg')
PATH_C     = os.path.join(_IMG_DIR, 'test_capture_methodC.jpg')


def _stretch(ch):
    """Per-channel histogram stretch: map 2nd–98th percentile to 0–255."""
    lo, hi = float(np.percentile(ch, 2)), float(np.percentile(ch, 98))
    if hi <= lo:
        return ch.copy()
    return np.clip((ch.astype(float) - lo) / (hi - lo) * 255, 0, 255).astype('uint8')

STREAM_INIT_S  = 4   # streamon() needs 5-6 s total; 4 s before takeoff + 3 s after
STABILISE_S    = 3
FLUSH_S        = 3   # discard the first few seconds of frames (often black/corrupt)
MAX_WAIT_S     = 5   # max extra time to wait for a non-black frame after flushing
MIN_MEAN       = 10  # frames with mean pixel value <= this are treated as black

drone     = Tello()
streaming = False
took_off  = False

try:
    print('Connecting to Tello...')
    drone.connect()
    battery_start = drone.get_battery()
    print(f'Battery: {battery_start}%')

    print('Starting video stream...')
    drone.streamon()
    streaming = True

    print(f'Waiting {STREAM_INIT_S}s for stream to initialise...')
    time.sleep(STREAM_INIT_S)

    print('Taking off...')
    drone.takeoff()
    took_off = True

    print(f'Stabilising ({STABILISE_S}s)...')
    time.sleep(STABILISE_S)

    print(f'Flushing initial frames ({FLUSH_S}s)...')
    t_flush = time.monotonic()
    while time.monotonic() - t_flush < FLUSH_S:
        drone.get_frame_read().frame

    print(f'Waiting for a non-black frame (mean > {MIN_MEAN}, up to {MAX_WAIT_S}s)...')
    frame = None
    mean_val = 0.0
    t_wait = time.monotonic()
    while time.monotonic() - t_wait < MAX_WAIT_S:
        candidate = drone.get_frame_read().frame
        mean_val = float(candidate.mean())
        if mean_val > MIN_MEAN:
            frame = candidate
            break

    if frame is None:
        raise RuntimeError(
            f'No valid frame after {FLUSH_S + MAX_WAIT_S}s — stream may be stuck'
        )

    os.makedirs(_IMG_DIR, exist_ok=True)
    b, g, r = cv2.split(frame)
    h, w    = frame.shape[:2]
    print(f'Raw channel means — R: {r.mean():.1f}  G: {g.mean():.1f}  B: {b.mean():.1f}  '
          f'(overall mean: {mean_val:.1f})  [{w}x{h}]')

    cv2.imwrite(RAW_PATH, frame)
    print(f'Raw saved to {RAW_PATH}')

    # Method A: empirical Tello-specific scaling (R×1.8, G×1.2, B×0.7)
    method_a = cv2.merge([
        np.clip(b.astype(float) * 0.7, 0, 255).astype('uint8'),
        np.clip(g.astype(float) * 1.2, 0, 255).astype('uint8'),
        np.clip(r.astype(float) * 1.8, 0, 255).astype('uint8'),
    ])
    cv2.imwrite(PATH_A, method_a)
    print(f'Method A (manual R×1.8 G×1.2 B×0.7) saved to {PATH_A}')

    # Method B: per-channel histogram stretch (2nd–98th percentile → 0–255)
    cv2.imwrite(PATH_B, cv2.merge([_stretch(b), _stretch(g), _stretch(r)]))
    print(f'Method B (per-channel histogram stretch) saved to {PATH_B}')

    # Method C: LAB color space + CLAHE on L channel only
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cv2.imwrite(PATH_C, cv2.cvtColor(cv2.merge([clahe.apply(l), a_ch, b_ch]),
                                      cv2.COLOR_LAB2BGR))
    print(f'Method C (LAB + CLAHE) saved to {PATH_C}')

    print('Landing...')
    drone.land()
    took_off = False

    print('Stopping video stream...')
    drone.streamoff()
    streaming = False

    battery_end = drone.get_battery()
    print(f'Battery after landing: {battery_end}%  (used {battery_start - battery_end}%)')

except Exception as exc:
    print(f'\nError during flight: {exc}')
    if took_off:
        print('Attempting emergency land...')
        try:
            drone.land()
        except Exception as land_exc:
            print(f'Emergency land also failed: {land_exc}')
    if streaming:
        try:
            drone.streamoff()
        except Exception:
            pass

finally:
    drone.end()
    print('Connection closed.')
