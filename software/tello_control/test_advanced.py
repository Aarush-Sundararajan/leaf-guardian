# REQUIRES: 1.5 m ceiling clearance. Clear 2 m x 2 m floor space minimum.
# Usage (from repo root): py software/tello_control/test_advanced.py
import sys
import time
from djitellopy import Tello

drone    = Tello()
took_off = False

try:
    print('Connecting...')
    drone.connect()
    time.sleep(2)
    battery = drone.get_battery()
    print(f'Battery: {battery}%')
    if battery < 50:
        print(f'WARNING: Battery is {battery}%. Flips may be disabled below 50%. '
              f'Charge to 80%+ before running this script.')
        sys.exit(1)
    print('Taking off...')
    drone.takeoff()
    took_off = True
    time.sleep(3)
    print('Moving up 60 cm to flip altitude...')
    drone.move_up(60)
    time.sleep(3)
    print('Flipping forward...')
    drone.flip_forward()
    time.sleep(3)
    print('Moving forward 80 cm...')
    drone.move_forward(80)
    time.sleep(2)
    print('Moving up 40 cm to restore flip altitude...')
    drone.move_up(40)
    time.sleep(3)
    print('Flipping left...')
    drone.flip_left()
    time.sleep(3)
    print('Moving left 80 cm...')
    drone.move_left(80)
    time.sleep(2)
    print('Moving up 40 cm to restore flip altitude...')
    drone.move_up(40)
    time.sleep(3)
    print('Rotating clockwise 360 degrees...')
    drone.rotate_clockwise(360)
    time.sleep(3)
    print('Flipping back...')
    drone.flip_back()
    time.sleep(3)
    print('Landing...')
    drone.land()
    took_off = False
    battery_end = drone.get_battery()
    print(f'Battery after landing: {battery_end}%  (used {battery - battery_end}%)')
except Exception as exc:
    print(f'Error: {exc}')
    if took_off:
        try:
            drone.land()
        except Exception:
            pass
finally:
    drone.end()
    print('Connection closed.')
