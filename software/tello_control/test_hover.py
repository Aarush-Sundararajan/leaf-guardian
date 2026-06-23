"""
Basic hover test for DJI Tello.

Connects, takes off, hovers for 5 seconds, lands, and prints battery before
and after the flight. Safe to use as a first sanity-check on new hardware.

Usage (from repo root):
    py software/tello_control/test_hover.py
"""

import time
from djitellopy import Tello

HOVER_SECONDS = 5

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

    print(f'Hovering for {HOVER_SECONDS} seconds...')
    time.sleep(HOVER_SECONDS)

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
