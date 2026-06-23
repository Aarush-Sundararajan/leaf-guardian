"""
Advanced capability test for DJI Tello.

REQUIRES: at least 1.5 m ceiling clearance for flips. Clear 2 m x 2 m floor
space minimum. Do not attempt in a low-ceiling room or near obstacles.

Sequence: takeoff → ascend → flip forward → fast forward move →
          flip left → fast left move → 360 spin → flip back → land.

Usage (from repo root):
    py software/tello_control/test_advanced.py
"""

import time
from djitellopy import Tello

FLIP_SPEED  = 30   # cm/s — slower speed before flips for stability
MOVE_SPEED  = 60   # cm/s — faster speed for the forward/left moves

drone    = Tello()
took_off = False

try:
    print('Connecting to Tello...')
    drone.connect()
    battery_start = drone.get_battery()
    print(f'Battery: {battery_start}%')

    print('Taking off...')
    drone.takeoff()
    took_off = True

    print('Ascending 60 cm to reach safe flip altitude...')
    drone.move_up(60)
    time.sleep(2)

    print('Flip 1 of 3: flipping forward...')
    drone.set_speed(FLIP_SPEED)
    drone.flip_forward()
    time.sleep(2)

    print(f'Moving forward 80 cm at {MOVE_SPEED} cm/s...')
    drone.set_speed(MOVE_SPEED)
    drone.move_forward(80)
    time.sleep(1.5)

    print('Flip 2 of 3: flipping left...')
    drone.set_speed(FLIP_SPEED)
    drone.flip_left()
    time.sleep(2)

    print(f'Moving left 80 cm at {MOVE_SPEED} cm/s...')
    drone.set_speed(MOVE_SPEED)
    drone.move_left(80)
    time.sleep(1.5)

    print('Rotating clockwise 360 degrees...')
    drone.rotate_clockwise(360)
    time.sleep(2)

    print('Flip 3 of 3: flipping back...')
    drone.set_speed(FLIP_SPEED)
    drone.flip_back()
    time.sleep(2)

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
