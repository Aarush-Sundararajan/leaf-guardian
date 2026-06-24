# NOTE: "downvision 1" is not officially documented in the Tello SDK and may
# not work on all firmware versions. If the saved image looks identical to a
# forward-facing shot, the camera switch likely did not take effect.
#
# Usage (from repo root): py software/tello_control/test_downward_camera.py

import os
import time

import cv2
import numpy as np
from djitellopy import Tello

_REPO_ROOT   = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUTPUT_PATH  = os.path.join(_REPO_ROOT, 'data', 'drone_imagery', 'test_downward.jpg')
RAW_PATH     = os.path.join(_REPO_ROOT, 'data', 'drone_imagery', 'test_downward_raw.jpg')

FLUSH_S    = 3
MAX_WAIT_S = 5
MIN_MEAN   = 10

drone     = Tello()
streaming = False
took_off  = False

try:
    print('Connecting...')
    drone.connect()
    time.sleep(2)
    battery = drone.get_battery()
    print(f'Battery: {battery}%')
    if battery < 50:
        print(f'WARNING: Battery is {battery}%. Charge to 80%+ before running this script.')
        import sys; sys.exit(1)

    print('Starting video stream...')
    drone.streamon()
    streaming = True
    time.sleep(4)

    print('Taking off...')
    drone.takeoff()
    took_off = True
    time.sleep(3)

    print('Moving up 60 cm...')
    drone.move_up(60)
    time.sleep(3)

    print('Moving forward 80 cm...')
    drone.move_forward(80)
    time.sleep(3)

    print('Switching to downward camera (downvision 1)...')
    drone.send_command_with_return('downvision 1')
    time.sleep(2)

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
        raise RuntimeError(f'No valid frame after {FLUSH_S + MAX_WAIT_S}s — stream may be stuck')

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    cv2.imwrite(RAW_PATH, frame)
    print(f'Raw frame saved to {RAW_PATH}')

    b, g, r   = cv2.split(frame)
    b_mean, g_mean, r_mean = float(b.mean()), float(g.mean()), float(r.mean())
    overall   = (b_mean + g_mean + r_mean) / 3.0
    b_wb = np.clip(b.astype(float) * (overall / b_mean), 0, 255).astype('uint8')
    g_wb = np.clip(g.astype(float) * (overall / g_mean), 0, 255).astype('uint8')
    r_wb = np.clip(r.astype(float) * (overall / r_mean), 0, 255).astype('uint8')
    cv2.imwrite(OUTPUT_PATH, cv2.merge([b_wb, g_wb, r_wb]))
    h, w = frame.shape[:2]
    print(f'White-balanced frame saved to {OUTPUT_PATH}  ({w}x{h} px, mean: {mean_val:.1f})')

    print('Switching back to forward camera (downvision 0)...')
    drone.send_command_with_return('downvision 0')
    time.sleep(1)

    print('Moving back 80 cm...')
    drone.move_back(80)
    time.sleep(2)

    print('Moving down 60 cm...')
    drone.move_down(60)
    time.sleep(2)

    print('Landing...')
    drone.land()
    took_off = False

    print('Stopping video stream...')
    drone.streamoff()
    streaming = False

    battery_end = drone.get_battery()
    print(f'Battery after landing: {battery_end}%  (used {battery - battery_end}%)')

except Exception as exc:
    print(f'Error: {exc}')
    if took_off:
        print('Attempting emergency land...')
        try:
            drone.land()
        except Exception:
            pass
    if streaming:
        try:
            drone.streamoff()
        except Exception:
            pass

finally:
    drone.end()
    print('Connection closed.')
