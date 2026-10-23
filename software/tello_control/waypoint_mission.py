"""
Lawnmower survey mission for DJI Tello.

Flies a back-and-forth grid over a rows x cols area, capturing a photo
at every waypoint, then automatically stitches the results into a health
map. Photo capture is a placeholder stub — swap in a real camera trigger
by editing capture_photo() only.

Usage:
    python software/tello_control/waypoint_mission.py          # MockTello, 3x3 grid
    python software/tello_control/waypoint_mission.py --real   # live drone
"""

import json
import os
import sys
import time
from datetime import datetime

import cv2
import numpy as np

# stitch_grid lives in the sibling ndvi_pipeline package
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'ndvi_pipeline')))
from stitch_grid import run as stitch_run

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
# Camera capture
# ---------------------------------------------------------------------------

def capture_photo_mock(waypoint_idx, row_0, col_0, photo_dir):
    """Mock camera trigger. Writes a solid-color JPEG named <row>.<col>.jpg.

    row_0 / col_0 are 0-indexed internally; filenames are 1-indexed to match
    the stitch_grid convention (first tile = 1.1.jpg, not 0.0.jpg).
    """
    r1, c1   = row_0 + 1, col_0 + 1
    filepath = os.path.join(photo_dir, f'{r1}.{c1}.jpg')

    img  = np.full((300, 400, 3), (45, 105, 50), dtype=np.uint8)
    text = f'{r1}.{c1}'
    fs   = 2.5
    th   = 3
    (tw, th_px), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
    cv2.putText(img, text,
                ((400 - tw) // 2, (300 + th_px) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), th, cv2.LINE_AA)
    cv2.imwrite(filepath, img)

    print(f'[CAPTURE] Waypoint {waypoint_idx:>2d}  [{r1},{c1}]  -> {filepath}')
    return {
        'waypoint_idx': waypoint_idx,
        'row':          r1,
        'col':          c1,
        'filename':     filepath,
    }


# HARDWARE TEST DAY CHECKLIST — June 26
# Before relying on capture_photo_real() in a live mission, verify:
#
# 1. streamon() init: call tello.streamon() and immediately read a few frames
#    in a loop (get_frame_read().frame) to confirm the stream stabilises before
#    the first move command. A brief time.sleep(1-2s) after streamon() is often
#    needed for the UDP video feed to start delivering non-zero frames.
#
# 2. Capture timing: djitellopy move commands are blocking — the SDK waits for
#    the drone to acknowledge completion before returning. Confirm the drone is
#    actually stationary (not still decelerating) when capture_photo_real() is
#    called. If images are blurry, add a short sleep between move completion
#    and frame grab.
#
# 3. JPEG quality for scoring: default cv2.imwrite quality is ~95. Check that
#    the saved frame has enough color fidelity for rgb_health's HSV thresholds
#    (green H 35-85, S > 80). If scoring seems off on real images, compare the
#    raw frame array's HSV values against the saved JPEG to rule out compression
#    artifacts washing out saturation.

def capture_photo_real(tello, waypoint_idx, row_0, col_0, photo_dir):
    """Live camera capture from the Tello video stream.

    Requires tello.streamon() to have been called before the mission starts.
    Grabs a single frame from the running video feed and saves it as a JPEG.
    """
    r1, c1   = row_0 + 1, col_0 + 1
    filepath = os.path.join(photo_dir, f'{r1}.{c1}.jpg')

    frame = tello.get_frame_read().frame   # BGR numpy array from the live stream
    cv2.imwrite(filepath, frame)

    print(f'[CAPTURE] Waypoint {waypoint_idx:>2d}  [{r1},{c1}]  -> {filepath}')
    return {
        'waypoint_idx': waypoint_idx,
        'row':          r1,
        'col':          c1,
        'filename':     filepath,
    }

# ---------------------------------------------------------------------------
# Path generation
# ---------------------------------------------------------------------------
def generate_lawnmower_path(rows, cols):
    """Return an ordered list of steps for a lawnmower survey.

    Each step is a tuple:
      ('capture', row, col)          — hover and shoot  (0-indexed)
      ('move', direction, distance)  — fly to next position

    Even columns travel forward (row 0 -> rows-1).
    Odd  columns travel back   (row rows-1 -> 0).
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

def run_mission(tello, rows=3, cols=3, step_cm=50, label='survey', use_real=False):
    """Connect, fly the lawnmower grid, land, then auto-stitch captured photos."""
    photo_dir = os.path.join(_REPO_ROOT, 'data', 'drone_imagery', label)
    os.makedirs(photo_dir, exist_ok=True)

    tello.connect()
    battery_start = tello.get_battery()
    print(f'Battery before flight: {battery_start}%')
    print(f'Pattern: lawnmower {rows}x{cols}, {step_cm} cm steps '
          f'({rows * cols} waypoints)')
    print(f'Photos -> {photo_dir}\n')

    if use_real:
        tello.streamon()

    tello.takeoff()
    t_start = time.monotonic()

    path   = generate_lawnmower_path(rows, cols)
    photos = []
    wp_idx = 0

    for step in path:
        if step[0] == 'capture':
            _, row_0, col_0 = step
            if use_real:
                photos.append(capture_photo_real(tello, wp_idx, row_0, col_0, photo_dir))
            else:
                photos.append(capture_photo_mock(wp_idx, row_0, col_0, photo_dir))
            wp_idx += 1
        else:
            _, direction, _ = step
            getattr(tello, _MOVE_FN[direction])(step_cm)

    tello.land()
    if use_real:
        tello.streamoff()
    duration    = round(time.monotonic() - t_start, 1)
    battery_end = tello.get_battery()
    print(f'\nBattery after flight: {battery_end}%')

    log = {
        'timestamp':        datetime.utcnow().isoformat() + 'Z',
        'battery_start':    battery_start,
        'battery_end':      battery_end,
        'battery_used':     battery_start - battery_end,
        'duration_seconds': duration,
        'pattern':          f'lawnmower_{rows}x{cols}_{step_cm}cm',
        'grid': {'rows': rows, 'cols': cols, 'step_cm': step_cm},
        'waypoints_flown':  wp_idx,
        'photos':           photos,
    }

    # --- Post-mission stitch ---
    print('\n--- Post-mission stitch ---')
    stitch_out = os.path.join(photo_dir, 'stitched_results')
    try:
        _, _, scores = stitch_run(photo_dir, stitch_out)
        tag = f'{rows}x{cols}'
        log['stitch'] = {
            'composite': os.path.join(stitch_out, f'composite_{tag}.png'),
            'analyzed':  os.path.join(stitch_out, f'analyzed_{tag}.png'),
            'mean_health_score': round(float(np.mean(scores)), 3),
        }
    except Exception as exc:
        print(f'  Stitch failed: {exc}')
        log['stitch'] = {'error': str(exc)}

    return log

# ---------------------------------------------------------------------------
# Flight log
# ---------------------------------------------------------------------------
def save_flight_log(log: dict) -> str:
    os.makedirs(FLIGHT_LOGS, exist_ok=True)
    ts   = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
    path = os.path.join(FLIGHT_LOGS, f'flight_{ts}.json')
    with open(path, 'w') as f:
        json.dump(log, f, indent=2)
    print(f'\nFlight log saved to {path}')
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

    log = run_mission(drone, rows=3, cols=3, step_cm=50, label='survey', use_real=use_real)
    save_flight_log(log)

    print('\nFlight log JSON:')
    print(json.dumps(log, indent=2))
