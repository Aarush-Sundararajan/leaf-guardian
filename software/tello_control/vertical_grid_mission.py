# VERTICAL GRID MISSION — captures a grid of forward-facing photos at different
# heights and lateral positions. Useful for mapping vegetation on slopes, walls,
# or any vertical surface. Requires ROWS * STEP_V cm of vertical clearance above
# the takeoff point. For a 3x3 grid with STEP_V=40: needs ~120 cm clear above takeoff.
#
# Usage (from repo root):
#   py software/tello_control/vertical_grid_mission.py                         # MockTello, 3x3
#   py software/tello_control/vertical_grid_mission.py --rows 2 --cols 2      # MockTello, 2x2
#   py software/tello_control/vertical_grid_mission.py --real                  # live Tello

import os
import sys
import time

import cv2
import numpy as np

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'ndvi_pipeline')))
from stitch_grid import run as stitch_run

# ---------------------------------------------------------------------------
# Parameters — edit these to change the grid layout
# ---------------------------------------------------------------------------
ROWS        = 3    # number of vertical rows (top to bottom)
COLS        = 3    # number of columns per row (left to right)
STEP_H      = 40   # horizontal distance between columns (cm, min 20)
STEP_V      = 40   # vertical distance between rows (cm; drone descends each row)
SAVE_FOLDER = os.path.join(_REPO_ROOT, 'data', 'drone_imagery', 'vertical_grid')

FLUSH_S   = 2    # seconds to discard corrupt early frames before capture
MIN_MEAN  = 10   # reject frames with mean pixel value at or below this (black/stuck)

# ---------------------------------------------------------------------------
# Command-line flags:  --real | --rows N | --cols N
# ---------------------------------------------------------------------------
USE_REAL = '--real' in sys.argv
for _flag, _key in (('--rows', 'ROWS'), ('--cols', 'COLS')):
    if _flag in sys.argv:
        globals()[_key] = int(sys.argv[sys.argv.index(_flag) + 1])

# ---------------------------------------------------------------------------
# MockTello — hardware-free stand-in (no streamon/get_frame_read needed)
# ---------------------------------------------------------------------------
class MockTello:
    _battery = 85

    def connect(self):    print('[MOCK] Connected')
    def takeoff(self):    print('[MOCK] Takeoff');  time.sleep(0.05)
    def land(self):       print('[MOCK] Land');     time.sleep(0.05)
    def streamoff(self):  print('[MOCK] streamoff')
    def end(self):        print('[MOCK] Connection closed')
    def get_battery(self): return self._battery

    def move_up(self, cm):      self._move('up',      cm)
    def move_down(self, cm):    self._move('down',    cm)
    def move_left(self, cm):    self._move('left',    cm)
    def move_right(self, cm):   self._move('right',   cm)
    def move_forward(self, cm): self._move('forward', cm)
    def move_back(self, cm):    self._move('back',    cm)

    def _move(self, direction, cm):
        self._battery -= 1
        print(f'[MOCK] move_{direction} {cm} cm')
        time.sleep(0.05)

# ---------------------------------------------------------------------------
# Frame capture
# ---------------------------------------------------------------------------
def _wb_method_a(frame):
    """Empirical Tello blue-cast correction: R×1.8, G×1.2, B×0.7."""
    b, g, r = cv2.split(frame)
    return cv2.merge([
        np.clip(b.astype(float) * 0.7, 0, 255).astype('uint8'),
        np.clip(g.astype(float) * 1.2, 0, 255).astype('uint8'),
        np.clip(r.astype(float) * 1.8, 0, 255).astype('uint8'),
    ])


def capture_real(drone):
    """Flush stale frames then return the first non-black frame."""
    t = time.monotonic()
    while time.monotonic() - t < FLUSH_S:
        drone.get_frame_read().frame

    t = time.monotonic()
    while time.monotonic() - t < 5.0:
        frame = drone.get_frame_read().frame
        if float(frame.mean()) > MIN_MEAN:
            return _wb_method_a(frame)

    raise RuntimeError('No valid frame after flush — stream may be stuck')


def capture_mock(row, col):
    """Solid-color placeholder image with row.col label, varying shade per cell."""
    green = min(60 + (row * COLS + col) * 15, 220)
    img   = np.full((480, 640, 3), (40, green, 50), dtype=np.uint8)
    label = f'{row}.{col}'
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 2.5, 3)
    cv2.putText(img, label, ((640 - tw) // 2, (480 + th) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 3, cv2.LINE_AA)
    return img


def save_photo(frame, row, col):
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    path = os.path.join(SAVE_FOLDER, f'{row}.{col}.jpg')
    cv2.imwrite(path, frame)
    print(f'  Saved -> {path}')

# ---------------------------------------------------------------------------
# Main mission
# ---------------------------------------------------------------------------
if USE_REAL:
    from djitellopy import Tello
    drone = Tello()
else:
    drone = MockTello()

streaming = False
took_off  = False

try:
    print(f'{"REAL" if USE_REAL else "MOCK"} mode | {ROWS}x{COLS} grid | '
          f'STEP_H={STEP_H} cm  STEP_V={STEP_V} cm')
    print(f'Vertical clearance needed: {60 + (ROWS - 1) * STEP_V} cm above takeoff')
    print(f'Photos -> {SAVE_FOLDER}\n')

    print('Connecting...')
    drone.connect()
    time.sleep(2)

    battery = drone.get_battery()
    print(f'Battery: {battery}%')
    if battery < 50:
        print(f'WARNING: Battery is {battery}%. Charge to 80%+ before running this script.')
        sys.exit(1)

    if USE_REAL:
        print('Starting video stream...')
        drone.streamon()
        streaming = True
        time.sleep(4)

    print('Taking off...')
    drone.takeoff()
    took_off = True
    time.sleep(3)

    print('Moving up 60 cm to starting altitude (top-left of grid)...')
    drone.move_up(60)
    time.sleep(2)

    # -----------------------------------------------------------------------
    # Lawnmower grid capture
    # Row 1 is the topmost row; drone descends between rows.
    # Odd rows (1, 3, ...) travel left → right.
    # Even rows (2, 4, ...) travel right → left.
    # -----------------------------------------------------------------------
    for row in range(1, ROWS + 1):
        going_right = (row % 2 == 1)
        col_seq     = range(1, COLS + 1) if going_right else range(COLS, 0, -1)

        for col_idx, col in enumerate(col_seq):
            print(f'\n[Row {row}/{ROWS}, Col {col}/{COLS}] Capturing photo...')
            frame = capture_real(drone) if USE_REAL else capture_mock(row, col)
            save_photo(frame, row, col)
            time.sleep(2)

            if col_idx < COLS - 1:
                if going_right:
                    print(f'Moving right {STEP_H} cm...')
                    drone.move_right(STEP_H)
                else:
                    print(f'Moving left {STEP_H} cm...')
                    drone.move_left(STEP_H)
                time.sleep(2)

        if row < ROWS:
            print(f'\nStepping down {STEP_V} cm to row {row + 1}...')
            drone.move_down(STEP_V)
            time.sleep(2)

    # -----------------------------------------------------------------------
    # Return to center
    # -----------------------------------------------------------------------
    vertical_lost = (ROWS - 1) * STEP_V
    if vertical_lost > 0:
        print(f'\nRestoring altitude (moving up {vertical_lost} cm)...')
        drone.move_up(vertical_lost)
        time.sleep(2)

    # After the last row: odd ROWS → ended going right → at rightmost col
    #                     even ROWS → ended going left  → at leftmost col
    last_row_ends_right = (ROWS % 2 == 1)
    current_col         = COLS if last_row_ends_right else 1
    center_col          = (COLS + 1) / 2
    h_offset            = int(round((center_col - current_col) * STEP_H))
    if h_offset > 0:
        print(f'Moving right {h_offset} cm to center column...')
        drone.move_right(h_offset)
        time.sleep(2)
    elif h_offset < 0:
        print(f'Moving left {abs(h_offset)} cm to center column...')
        drone.move_left(abs(h_offset))
        time.sleep(2)

    if USE_REAL:
        print('Stopping video stream before land...')
        drone.streamoff()
        streaming = False
        time.sleep(1)

    print('\nLanding...')
    drone.land()
    took_off = False

    battery_end = drone.get_battery()
    print(f'Battery after landing: {battery_end}%  (used {battery - battery_end}%)')

    # -----------------------------------------------------------------------
    # Post-mission stitch
    # -----------------------------------------------------------------------
    print('\n--- Post-mission stitch ---')
    stitch_out = os.path.join(SAVE_FOLDER, 'stitched_results')
    try:
        _, _, scores = stitch_run(SAVE_FOLDER, stitch_out)
        tag = f'{ROWS}x{COLS}'
        print(f'Composite : {os.path.join(stitch_out, f"composite_{tag}.png")}')
        print(f'Analyzed  : {os.path.join(stitch_out, f"analyzed_{tag}.png")}')
        print(f'Mean health score: {float(np.mean(scores)):.3f}')
    except Exception as stitch_exc:
        print(f'Stitch failed: {stitch_exc}')

except Exception as exc:
    print(f'\nError: {exc}')
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
