"""
stitch_grid.py -- Drone survey grid stitcher and health analyser.

Pipeline:
  1. Scan a folder for <row>.<col>.jpg files and auto-detect grid dimensions.
  2. Stitch tiles into a seamless composite (no letterboxing -- tiles are
     resized to a common dimension so borders connect directly).
  3. Run RGB health analysis on the full composite using a finer analysis
     grid of (source_rows * 3) x (source_cols * 3) cells.
  4. Save both the raw composite and the annotated analysis image.

Usage (from repo root):
    python software/ndvi_pipeline/stitch_grid.py <folder> [out_dir]
    python software/ndvi_pipeline/stitch_grid.py          # default: grid_test/
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
from rgb_health import rgb_cell_score

# ---------------------------------------------------------------------------
# 1. Grid detection
# ---------------------------------------------------------------------------

def scan_grid_folder(folder):
    """Return tiles dict, grid_rows, grid_cols from <row>.<col>.jpg filenames."""
    pat   = re.compile(r'^(\d+)\.(\d+)\.jpe?g$', re.IGNORECASE)
    tiles = {}
    for fname in os.listdir(folder):
        m = pat.match(fname)
        if m:
            r, c = int(m.group(1)), int(m.group(2))
            tiles[(r, c)] = os.path.join(folder, fname)

    if not tiles:
        raise ValueError(f'No <row>.<col>.jpg files found in: {folder}')

    grid_rows = max(r for r, _ in tiles)
    grid_cols = max(c for _, c in tiles)

    missing = [
        f'{r}.{c}'
        for r in range(1, grid_rows + 1)
        for c in range(1, grid_cols + 1)
        if (r, c) not in tiles
    ]
    if missing:
        print(f'  WARNING: missing tiles for {grid_rows}x{grid_cols} grid: '
              f'{", ".join(missing)}')

    return tiles, grid_rows, grid_cols


# ---------------------------------------------------------------------------
# 2. Seamless composite stitch
# ---------------------------------------------------------------------------

def stitch_composite(tiles, grid_rows, grid_cols):
    """Tile images into a seamless composite with no padding or letterboxing.

    All images are resized to a common tile size (largest dimensions found)
    so their borders connect directly. Assumes all source images share the
    same aspect ratio.
    """
    images = {}
    for (r, c), path in tiles.items():
        img = cv2.imread(path)
        if img is None:
            print(f'  WARNING: could not read {path}')
        images[(r, c)] = img

    loaded = [img for img in images.values() if img is not None]
    tile_w = max(img.shape[1] for img in loaded)
    tile_h = max(img.shape[0] for img in loaded)
    print(f'  Common tile size: {tile_w} x {tile_h} px')

    composite = np.zeros((grid_rows * tile_h, grid_cols * tile_w, 3), dtype=np.uint8)

    for r in range(1, grid_rows + 1):
        for c in range(1, grid_cols + 1):
            y0 = (r - 1) * tile_h
            x0 = (c - 1) * tile_w
            img = images.get((r, c))
            if img is not None:
                if img.shape[1] != tile_w or img.shape[0] != tile_h:
                    img = cv2.resize(img, (tile_w, tile_h), interpolation=cv2.INTER_AREA)
                composite[y0:y0+tile_h, x0:x0+tile_w] = img
            # Missing tile left black

    return composite, tile_w, tile_h


# ---------------------------------------------------------------------------
# 3. RGB health analysis on the full composite
# ---------------------------------------------------------------------------

def _score_to_bgr(score):
    """Map 0-1 health score to BGR: red (0) -> yellow (0.5) -> green (1)."""
    if score <= 0.5:
        t = score * 2
        return (0, int(200 * t), 200)           # red -> yellow
    else:
        t = (score - 0.5) * 2
        return (0, 200, int(200 * (1 - t)))      # yellow -> green


def analyze_composite(composite, source_rows, source_cols):
    """Analyse composite health with a (source_rows*3) x (source_cols*3) grid.

    Scores each cell using the same green/brown HSV logic as rgb_health.py,
    then returns an annotated copy with a semi-transparent colour overlay,
    grid lines, and per-cell score labels.
    """
    analysis_rows = source_rows * 3
    analysis_cols = source_cols * 3

    img_h, img_w = composite.shape[:2]
    cell_h = img_h // analysis_rows
    cell_w = img_w // analysis_cols

    hsv    = cv2.cvtColor(composite, cv2.COLOR_BGR2HSV)
    scores = np.zeros((analysis_rows, analysis_cols))

    for i in range(analysis_rows):
        for j in range(analysis_cols):
            cell = hsv[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            scores[i, j] = rgb_cell_score(cell)

    # --- Build colour overlay ---
    overlay = np.zeros_like(composite)
    for i in range(analysis_rows):
        for j in range(analysis_cols):
            y0, x0 = i * cell_h, j * cell_w
            overlay[y0:y0+cell_h, x0:x0+cell_w] = _score_to_bgr(scores[i, j])

    annotated = cv2.addWeighted(composite, 0.55, overlay, 0.45, 0)

    # --- Grid lines ---
    for i in range(1, analysis_rows):
        y = i * cell_h
        cv2.line(annotated, (0, y), (img_w, y), (220, 220, 220), 1)
    for j in range(1, analysis_cols):
        x = j * cell_w
        cv2.line(annotated, (x, 0), (x, img_h), (220, 220, 220), 1)

    # --- Score labels ---
    font  = cv2.FONT_HERSHEY_SIMPLEX
    fs    = max(0.3, min(cell_w, cell_h) / 120)
    thick = max(1, int(fs * 1.8))

    for i in range(analysis_rows):
        for j in range(analysis_cols):
            text = f'{scores[i, j]:.2f}'
            (tw, th), _ = cv2.getTextSize(text, font, fs, thick)
            tx = j * cell_w + (cell_w - tw) // 2
            ty = i * cell_h + (cell_h + th) // 2
            cv2.putText(annotated, text, (tx+1, ty+1), font, fs,
                        (0, 0, 0), thick + 1, cv2.LINE_AA)
            cv2.putText(annotated, text, (tx, ty), font, fs,
                        (255, 255, 255), thick, cv2.LINE_AA)

    return annotated, scores


# ---------------------------------------------------------------------------
# 4. Orchestrator
# ---------------------------------------------------------------------------

def run(folder, out_dir=None):
    if out_dir is None:
        out_dir = os.path.join(folder, 'stitched_results')

    tiles, grid_rows, grid_cols = scan_grid_folder(folder)
    print(f'  Detected: {grid_rows}x{grid_cols} grid '
          f'({len(tiles)}/{grid_rows*grid_cols} tiles present)')

    composite, tile_w, tile_h = stitch_composite(tiles, grid_rows, grid_cols)

    analysis_rows = grid_rows * 3
    analysis_cols = grid_cols * 3
    print(f'  Analysis grid: {analysis_rows}x{analysis_cols} '
          f'({analysis_rows*analysis_cols} cells)')

    analyzed, scores = analyze_composite(composite, grid_rows, grid_cols)

    os.makedirs(out_dir, exist_ok=True)
    tag = f'{grid_rows}x{grid_cols}'

    comp_path     = os.path.join(out_dir, f'composite_{tag}.png')
    analyzed_path = os.path.join(out_dir, f'analyzed_{tag}.png')

    cv2.imwrite(comp_path,     composite)
    cv2.imwrite(analyzed_path, analyzed)

    print(f'  Composite saved : {comp_path}')
    print(f'  Analyzed saved  : {analyzed_path}')

    mean_score = float(np.mean(scores))
    print(f'  Mean health score across composite: {mean_score:.3f}')

    return composite, analyzed, scores


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('--'):
        folder  = sys.argv[1]
        out_dir = sys.argv[2] if len(sys.argv) >= 3 else None
    else:
        folder  = os.path.join('data', 'drone_imagery', 'grid_test')
        out_dir = os.path.join('data', 'drone_imagery', 'grid_test', 'stitched_results')

    print(f'Folder: {folder}')
    run(folder, out_dir)
