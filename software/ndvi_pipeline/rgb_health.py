"""
RGB vegetation health scoring for drone imagery.

Two independent per-cell indices:
  HSV ratio  — green / (green + 0.5*yellow + brown + 1)
  VARI       — (G-R)/(G+R-B+1e-10), Gitelson et al. 2002, normalised to 0-1

Combined score = average of both. Cells are classified into four tiers.
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Tier system
# ---------------------------------------------------------------------------
TIER_HEALTHY  = 'Healthy'
TIER_MONITOR  = 'Monitor'
TIER_STRESSED = 'Action Needed'
TIER_CRITICAL = 'Critical'

# BGR colours used by stitch_grid for cell borders
TIER_COLORS_BGR = {
    TIER_HEALTHY:  (0,  180,  0),    # green
    TIER_MONITOR:  (0,  200, 230),   # yellow
    TIER_STRESSED: (0,  140, 255),   # orange
    TIER_CRITICAL: (0,    0, 220),   # red
}

_TIER_PLOT_COLORS = {
    TIER_HEALTHY:  'darkgreen',
    TIER_MONITOR:  'goldenrod',
    TIER_STRESSED: 'darkorange',
    TIER_CRITICAL: 'darkred',
}

_RECOMMENDATIONS = {
    TIER_HEALTHY:  'No intervention required',
    TIER_MONITOR:  'Schedule visual inspection within 2 weeks',
    TIER_STRESSED: 'Prioritize irrigation and inspect for pests or disease within 1 week',
    TIER_CRITICAL: (
        'Immediate intervention required — likely plant loss without action within 48 hours'
    ),
}


def classify_tier(score):
    if score >= 0.65: return TIER_HEALTHY
    if score >= 0.40: return TIER_MONITOR
    if score >= 0.20: return TIER_STRESSED
    return TIER_CRITICAL


def get_recommendation(tier):
    return _RECOMMENDATIONS[tier]


# ---------------------------------------------------------------------------
# Cell-level scoring
# ---------------------------------------------------------------------------

def rgb_cell_score(hsv_cell):
    """Green/yellow/brown HSV ratio. Yellow weighted as half as bad as brown."""
    h, s, v = hsv_cell[:, :, 0], hsv_cell[:, :, 1], hsv_cell[:, :, 2]

    not_shadow = v > 30
    not_sky    = ~((h > 90) & (h < 130) & (s > 50))
    valid      = not_shadow & not_sky

    green_mask  = (h >= 35) & (h <= 85) & (s > 80)  & valid
    yellow_mask = (h >= 20) & (h <  35) & (s > 100) & (v > 100) & valid
    brown_mask  = (h >= 10) & (h <  35) & valid & ~yellow_mask

    green  = int(np.sum(green_mask))
    yellow = int(np.sum(yellow_mask))
    brown  = int(np.sum(brown_mask))

    return green / (green + yellow * 0.5 + brown + 1)


def vari_score(bgr_cell):
    """VARI normalised to 0-1. Clips raw VARI to [-0.2, 0.6] before rescaling."""
    f = bgr_cell.astype(float) / 255.0
    B = f[:, :, 0].mean()
    G = f[:, :, 1].mean()
    R = f[:, :, 2].mean()
    raw  = (G - R) / (G + R - B + 1e-10)
    return float((np.clip(raw, -0.2, 0.6) + 0.2) / 0.8)


def combined_cell_score(hsv_cell, bgr_cell):
    """Average of HSV ratio score and normalised VARI."""
    return (rgb_cell_score(hsv_cell) + vari_score(bgr_cell)) / 2.0


# ---------------------------------------------------------------------------
# Health report
# ---------------------------------------------------------------------------

def generate_health_report(scores, tiers, label, out_path):
    """Write a plain-text health report alongside the grid image."""
    n_rows, n_cols = scores.shape
    total = n_rows * n_cols

    counts = {t: 0 for t in [TIER_HEALTHY, TIER_MONITOR, TIER_STRESSED, TIER_CRITICAL]}
    for row in tiers:
        for t in row:
            counts[t] += 1

    overall   = float(np.mean(scores))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    sep = '=========================================='
    lines = [
        sep,
        'LEAF GUARDIAN HEALTH REPORT',
        f'Site: {label}',
        f'Date: {timestamp}',
        f'Grid: {n_rows}x{n_cols} ({total} zones analyzed)',
        sep,
        'SUMMARY',
        f'Healthy zones:       {counts[TIER_HEALTHY]:>3}  ({counts[TIER_HEALTHY]/total*100:.0f}%)',
        f'Monitor zones:       {counts[TIER_MONITOR]:>3}  ({counts[TIER_MONITOR]/total*100:.0f}%)',
        f'Action Needed zones: {counts[TIER_STRESSED]:>3}  ({counts[TIER_STRESSED]/total*100:.0f}%)',
        f'Critical zones:      {counts[TIER_CRITICAL]:>3}  ({counts[TIER_CRITICAL]/total*100:.0f}%)',
        f'Overall site health score: {overall:.2f} / 1.00',
        sep,
        'PRIORITY ZONES REQUIRING ATTENTION',
    ]

    flagged = [
        f'  Zone ({i+1},{j+1}): {tiers[i][j].upper()} — {get_recommendation(tiers[i][j])}'
        for i in range(n_rows)
        for j in range(n_cols)
        if tiers[i][j] in (TIER_STRESSED, TIER_CRITICAL)
    ]
    lines += flagged if flagged else ['  None — all zones Healthy or Monitor.']

    lines += [
        sep,
        'METHODOLOGY NOTE',
        'Health scores computed using two independent RGB indices: green/yellow/brown',
        'pixel ratio (HSV-based) and VARI (Visible Atmospherically Resistant Index,',
        'Gitelson et al. 2002). Scores represent visible-light health proxies only.',
        'NDVI camera recommended for confirmation of stressed zones.',
        sep,
    ]

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(f'  Health report -> {out_path}')


# ---------------------------------------------------------------------------
# Standalone grid analysis (single image)
# ---------------------------------------------------------------------------

def rgb_health_grid(image_path, grid_size=4, label='test'):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f'Cannot read image: {image_path}')

    hsv           = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h_img, w_img  = img.shape[:2]
    cell_h, cell_w = h_img // grid_size, w_img // grid_size

    scores = np.zeros((grid_size, grid_size))
    tiers  = [[None] * grid_size for _ in range(grid_size)]

    for i in range(grid_size):
        for j in range(grid_size):
            y0, x0       = i * cell_h, j * cell_w
            hsv_cell     = hsv[y0:y0+cell_h, x0:x0+cell_w]
            bgr_cell     = img[y0:y0+cell_h, x0:x0+cell_w]
            scores[i, j] = combined_cell_score(hsv_cell, bgr_cell)
            tiers[i][j]  = classify_tier(scores[i, j])

    # --- Figure ---
    masked = np.ma.masked_equal(scores, 0)
    cmap   = plt.cm.RdYlGn.copy()
    cmap.set_bad(color='black')

    _, ax = plt.subplots(figsize=(7, 7))
    im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label='Health Score (0-1)')
    ax.set_title(f'RGB Grid Health Map — {label} ({grid_size}x{grid_size})')

    for i in range(grid_size):
        for j in range(grid_size):
            t = tiers[i][j]
            ax.text(j, i - 0.12, f'{scores[i, j]:.2f}',
                    ha='center', va='center', fontsize=9, color='black')
            ax.text(j, i + 0.22, t,
                    ha='center', va='center', fontsize=6,
                    color=_TIER_PLOT_COLORS[t], fontweight='bold')
            ax.add_patch(plt.Rectangle(
                (j - 0.5, i - 0.5), 1, 1,
                linewidth=2, edgecolor=_TIER_PLOT_COLORS[t], facecolor='none',
            ))

    out_png = f'data/drone_imagery/rgb_grid_{label}.png'
    out_txt = f'data/drone_imagery/health_report_{label}.txt'
    os.makedirs('data/drone_imagery', exist_ok=True)
    plt.savefig(out_png, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Grid image    -> {out_png}')

    generate_health_report(scores, tiers, label, out_txt)
    return scores


if __name__ == '__main__':
    rgb_health_grid('data/drone_imagery/test/healthy_image.jpg', grid_size=6, label='healthy')
