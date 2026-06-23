"""
Flip test for DJI Tello.

Ascends to a safe flip altitude, performs a forward flip, then lands.

WARNING: flip_forward() requires at least 1 meter of clear vertical space
ABOVE the drone at the moment of the flip. Do not attempt this in a room
with a low ceiling. The Tello takes off to roughly 50 cm by default;
move_up(50) brings it to ~1 m before the flip is triggered.

Usage (from repo root):
    py software/tello_control/test_flip.py
"""

import time
from djitellopy import Tello

STABILISE_S = 2

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

    print('Ascending 50 cm to reach safe flip altitude (~1 m total)...')
    drone.move_up(50)

    print(f'Stabilising ({STABILISE_S}s)...')
    time.sleep(STABILISE_S)

    print('Flipping forward...')
    drone.flip_forward()

    print(f'Stabilising after flip ({STABILISE_S}s)...')
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
