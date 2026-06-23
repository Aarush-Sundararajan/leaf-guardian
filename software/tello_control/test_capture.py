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
from djitellopy import Tello

_REPO_ROOT  = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUTPUT_PATH = os.path.join(_REPO_ROOT, 'data', 'drone_imagery', 'test_capture.jpg')

STREAM_INIT_S  = 2
STABILISE_S    = 3

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

    print('Capturing frame...')
    frame = drone.get_frame_read().frame
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    cv2.imwrite(OUTPUT_PATH, frame)
    h, w = frame.shape[:2]
    print(f'Saved to {OUTPUT_PATH}  ({w}x{h} px)')

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
