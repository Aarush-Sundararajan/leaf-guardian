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
from rgb_health import (combined_cell_score, classify_tier,
                         TIER_COLORS_BGR, generate_health_report)

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

    Each cell is scored using combined_cell_score (HSV ratio + VARI average),
    classified into a tier, and rendered with a tier-coloured border plus a
    two-line label (score / tier name). Returns annotated image, score grid,
    and tier grid.
    """
    analysis_rows = source_rows * 3
    analysis_cols = source_cols * 3

    img_h, img_w = composite.shape[:2]
    cell_h = img_h // analysis_rows
    cell_w = img_w // analysis_cols

    hsv    = cv2.cvtColor(composite, cv2.COLOR_BGR2HSV)
    scores = np.zeros((analysis_rows, analysis_cols))
    tiers  = [[None] * analysis_cols for _ in range(analysis_rows)]

    for i in range(analysis_rows):
        for j in range(analysis_cols):
            y0, x0          = i * cell_h, j * cell_w
            hsv_cell        = hsv[y0:y0+cell_h, x0:x0+cell_w]
            bgr_cell        = composite[y0:y0+cell_h, x0:x0+cell_w]
            scores[i, j]    = combined_cell_score(hsv_cell, bgr_cell)
            tiers[i][j]     = classify_tier(scores[i, j])

    # --- Score-based heat overlay ---
    overlay = np.zeros_like(composite)
    for i in range(analysis_rows):
        for j in range(analysis_cols):
            y0, x0 = i * cell_h, j * cell_w
            overlay[y0:y0+cell_h, x0:x0+cell_w] = _score_to_bgr(scores[i, j])

    annotated = cv2.addWeighted(composite, 0.55, overlay, 0.45, 0)

    # --- Tier-coloured cell borders ---
    for i in range(analysis_rows):
        for j in range(analysis_cols):
            y0, x0 = i * cell_h, j * cell_w
            cv2.rectangle(annotated,
                          (x0, y0), (x0 + cell_w - 1, y0 + cell_h - 1),
                          TIER_COLORS_BGR[tiers[i][j]], 3)

    # --- Two-line labels: score (white) + tier name (tier colour) ---
    font  = cv2.FONT_HERSHEY_SIMPLEX
    fs    = max(0.28, min(cell_w, cell_h) / 140)
    thick = max(1, int(fs * 1.5))

    for i in range(analysis_rows):
        for j in range(analysis_cols):
            y0, x0     = i * cell_h, j * cell_w
            score_txt  = f'{scores[i, j]:.2f}'
            tier_txt   = tiers[i][j]
            tier_color = TIER_COLORS_BGR[tiers[i][j]]

            (sw, sh), _ = cv2.getTextSize(score_txt, font, fs, thick)
            sx = x0 + (cell_w - sw) // 2
            sy = y0 + cell_h // 3 + sh // 2
            cv2.putText(annotated, score_txt, (sx+1, sy+1), font, fs,
                        (0, 0, 0), thick + 1, cv2.LINE_AA)
            cv2.putText(annotated, score_txt, (sx, sy), font, fs,
                        (255, 255, 255), thick, cv2.LINE_AA)

            (tw, th), _ = cv2.getTextSize(tier_txt, font, fs, thick)
            tx = x0 + (cell_w - tw) // 2
            ty = y0 + 2 * cell_h // 3 + th // 2
            cv2.putText(annotated, tier_txt, (tx+1, ty+1), font, fs,
                        (0, 0, 0), thick + 1, cv2.LINE_AA)
            cv2.putText(annotated, tier_txt, (tx, ty), font, fs,
                        tier_color, thick, cv2.LINE_AA)

    return annotated, scores, tiers


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

    analyzed, scores, tiers = analyze_composite(composite, grid_rows, grid_cols)

    os.makedirs(out_dir, exist_ok=True)
    tag = f'{grid_rows}x{grid_cols}'

    comp_path     = os.path.join(out_dir, f'composite_{tag}.png')
    analyzed_path = os.path.join(out_dir, f'analyzed_{tag}.png')
    label         = os.path.basename(os.path.normpath(folder))
    report_path   = os.path.join(out_dir, f'health_report_{label}.txt')

    cv2.imwrite(comp_path,     composite)
    cv2.imwrite(analyzed_path, analyzed)

    print(f'  Composite saved : {comp_path}')
    print(f'  Analyzed saved  : {analyzed_path}')

    mean_score = float(np.mean(scores))
    print(f'  Mean health score across composite: {mean_score:.3f}')

    generate_health_report(scores, tiers, label, report_path)

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
