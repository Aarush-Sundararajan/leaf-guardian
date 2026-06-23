"""
Basic movement test for DJI Tello.

Connects, takes off, moves forward 50 cm then left 50 cm (with stabilisation
pauses between moves), lands, and prints battery before and after.

Usage (from repo root):
    py software/tello_control/test_move.py
"""

import time
from djitellopy import Tello

STEP_CM      = 50
STABILISE_S  = 2

drone = Tello()
took_off = False

try:
    print('Connecting to Tello...')
    drone.connect()
    battery_start = drone.get_battery()
    print(f'Battery: {battery_start}%')

    print('Taking off...')
    drone.takeoff()
    took_off = True

    print(f'Stabilising ({STABILISE_S}s)...')
    time.sleep(STABILISE_S)

    print(f'Moving forward {STEP_CM} cm...')
    drone.move_forward(STEP_CM)

    print(f'Stabilising ({STABILISE_S}s)...')
    time.sleep(STABILISE_S)

    print(f'Moving left {STEP_CM} cm...')
    drone.move_left(STEP_CM)

    print(f'Stabilising ({STABILISE_S}s)...')
    time.sleep(STABILISE_S)

    print('Landing...')
    drone.land()
    took_off = False

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

finally:
    drone.end()
    print('Connection closed.')
