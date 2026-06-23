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

_REPO_ROOT  = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUTPUT_PATH = os.path.join(_REPO_ROOT, 'data', 'drone_imagery', 'test_capture.jpg')
RAW_PATH    = os.path.join(_REPO_ROOT, 'data', 'drone_imagery', 'test_capture_raw.jpg')

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

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    cv2.imwrite(RAW_PATH, frame)
    print(f'Raw frame saved to {RAW_PATH}')

    # Gray-world white balance: scale each channel so its mean matches the
    # average of all three channel means, then clip back to uint8.
    b, g, r   = cv2.split(frame)
    b_mean, g_mean, r_mean = float(b.mean()), float(g.mean()), float(r.mean())
    overall   = (b_mean + g_mean + r_mean) / 3.0
    b_wb = np.clip(b.astype(float) * (overall / b_mean), 0, 255).astype('uint8')
    g_wb = np.clip(g.astype(float) * (overall / g_mean), 0, 255).astype('uint8')
    r_wb = np.clip(r.astype(float) * (overall / r_mean), 0, 255).astype('uint8')
    frame_wb  = cv2.merge([b_wb, g_wb, r_wb])

    cv2.imwrite(OUTPUT_PATH, frame_wb)
    h, w = frame_wb.shape[:2]
    print(f'White-balanced frame saved to {OUTPUT_PATH}  '
          f'({w}x{h} px, mean pixel value: {mean_val:.1f})')

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
