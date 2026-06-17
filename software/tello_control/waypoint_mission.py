"""
Lawnmower survey mission for DJI Tello.

Flies a back-and-forth grid over a rows x cols area, capturing a photo
at every waypoint. Photo capture is a placeholder stub — swap in a real
camera trigger by editing capture_photo() only.

Usage:
    python software/tello_control/waypoint_mission.py          # MockTello, 3x3 grid
    python software/tello_control/waypoint_mission.py --real   # live drone
"""

import json
import os
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths  (script lives 2 levels below repo root)
# ---------------------------------------------------------------------------
_REPO_ROOT  = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
FLIGHT_LOGS = os.path.join(_REPO_ROOT, 'data', 'flight_logs')

# ---------------------------------------------------------------------------
# Mock drone — identical public interface to djitellopy.Tello
# ---------------------------------------------------------------------------
class MockTello:
    """Hardware-free stand-in for djitellopy.Tello.

    Battery starts at 85% and drains 1% per move so the log looks realistic.
    """
    _BATTERY_START = 85
    _BATTERY_DRAIN = 1

    def __init__(self):
        self._battery = self._BATTERY_START

    def connect(self):
        print('[MOCK] Connected to Tello (simulated)')

    def takeoff(self):
        print('[MOCK] Taking off...')
        time.sleep(0.1)

    def land(self):
        print('[MOCK] Landing...')
        time.sleep(0.1)

    def get_battery(self):
        return self._battery

    def move_forward(self, cm): self._move('forward', cm)
    def move_right(self, cm):   self._move('right',   cm)
    def move_back(self, cm):    self._move('back',    cm)
    def move_left(self, cm):    self._move('left',    cm)

    def _move(self, direction, cm):
        self._battery -= self._BATTERY_DRAIN
        print(f'[MOCK] Moving {direction} {cm} cm')
        time.sleep(0.05)

# ---------------------------------------------------------------------------
# Camera capture — swap this one function for real hardware later
# ---------------------------------------------------------------------------
def capture_photo(waypoint_idx, row, col, label):
    """Placeholder camera trigger.

    To use real hardware: replace this body with your camera SDK call
    (e.g. tello.take_picture(), a GPIO trigger, etc.) and return a dict
    with at minimum 'waypoint_idx' and 'filename'.
    """
    filename = f'data/drone_imagery/{label}_r{row:02d}_c{col:02d}.jpg'
    print(f'[CAPTURE] Waypoint {waypoint_idx:>2d}  row={row} col={col}  -> {filename}')
    return {
        'waypoint_idx': waypoint_idx,
        'row':          row,
        'col':          col,
        'filename':     filename,
    }

# ---------------------------------------------------------------------------
# Path generation
# ---------------------------------------------------------------------------
def generate_lawnmower_path(rows, cols):
    """Return an ordered list of steps for a lawnmower survey.

    Each step is a tuple:
      ('capture', row, col)          — hover and shoot
      ('move', direction, distance)  — fly to next position

    Even columns travel forward (row 0 → rows-1).
    Odd  columns travel back   (row rows-1 → 0).
    Columns are connected by a single 'right' shift.
    """
    steps = []
    for col in range(cols):
        going_forward = (col % 2 == 0)
        row_seq = range(rows) if going_forward else range(rows - 1, -1, -1)

        for i, row in enumerate(row_seq):
            steps.append(('capture', row, col))
            if i < rows - 1:
                steps.append(('move', 'forward' if going_forward else 'back', None))

        if col < cols - 1:
            steps.append(('move', 'right', None))

    return steps

# ---------------------------------------------------------------------------
# Mission runner
# ---------------------------------------------------------------------------
_MOVE_FN = {
    'forward': 'move_forward',
    'right':   'move_right',
    'back':    'move_back',
    'left':    'move_left',
}

def run_mission(tello, rows=3, cols=3, step_cm=50, label='survey'):
    """Connect, fly the lawnmower grid, land. Returns a flight-log dict."""
    tello.connect()

    battery_start = tello.get_battery()
    print(f'Battery before flight: {battery_start}%')
    print(f'Pattern: lawnmower {rows}x{cols}, {step_cm} cm steps '
          f'({rows * cols} waypoints)\n')

    tello.takeoff()
    t_start = time.monotonic()

    path    = generate_lawnmower_path(rows, cols)
    photos  = []
    wp_idx  = 0

    for step in path:
        if step[0] == 'capture':
            _, row, col = step
            photos.append(capture_photo(wp_idx, row, col, label))
            wp_idx += 1
        else:
            _, direction, _ = step
            getattr(tello, _MOVE_FN[direction])(step_cm)

    tello.land()
    duration = round(time.monotonic() - t_start, 1)

    battery_end = tello.get_battery()
    print(f'\nBattery after flight:  {battery_end}%')

    return {
        'timestamp':        datetime.utcnow().isoformat() + 'Z',
        'battery_start':    battery_start,
        'battery_end':      battery_end,
        'battery_used':     battery_start - battery_end,
        'duration_seconds': duration,
        'pattern':          f'lawnmower_{rows}x{cols}_{step_cm}cm',
        'grid': {
            'rows':    rows,
            'cols':    cols,
            'step_cm': step_cm,
        },
        'waypoints_flown': wp_idx,
        'photos':           photos,
    }

# ---------------------------------------------------------------------------
# Flight log
# ---------------------------------------------------------------------------
def save_flight_log(log: dict) -> str:
    os.makedirs(FLIGHT_LOGS, exist_ok=True)
    ts   = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
    path = os.path.join(FLIGHT_LOGS, f'flight_{ts}.json')
    with open(path, 'w') as f:
        json.dump(log, f, indent=2)
    print(f'Flight log saved to {path}')
    return path

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    use_real = '--real' in sys.argv

    if use_real:
        from djitellopy import Tello
        drone = Tello()
        print('Using real Tello drone')
    else:
        drone = MockTello()
        print('Using MockTello (pass --real to fly live)\n')

    log = run_mission(drone, rows=3, cols=3, step_cm=50, label='survey')
    save_flight_log(log)

    print('\nFlight log JSON:')
    print(json.dumps(log, indent=2))
