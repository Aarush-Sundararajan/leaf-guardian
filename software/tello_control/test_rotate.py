"""
Yaw control test for DJI Tello.

Rotates 360 degrees clockwise then 360 degrees counter-clockwise, returning
to the original heading. Tests the yaw accuracy needed for the lawnmower
survey pattern in waypoint_mission.py.

Usage (from repo root):
    py software/tello_control/test_rotate.py
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

    print(f'Stabilising ({STABILISE_S}s)...')
    time.sleep(STABILISE_S)

    print('Rotating clockwise 360 degrees...')
    drone.rotate_clockwise(360)

    print(f'Stabilising ({STABILISE_S}s)...')
    time.sleep(STABILISE_S)

    print('Rotating counter-clockwise 360 degrees...')
    drone.rotate_counter_clockwise(360)

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
