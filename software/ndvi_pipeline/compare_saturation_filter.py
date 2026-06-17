import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
import matplotlib.pyplot as plt

from rgb_health import rgb_health_grid          # already has the s > 80 fix
from sentinel_ndvi import compute_ndvi

IMAGE     = 'data/sentinel_data/color_images/sat_rgb_2022-Aug-CoyoteHills.png'
GRID_SIZE = 9
LAT, LON, HALF_M = 37.552707, -122.092559, 1000

# --- Before: original hue-only logic, reproduced inline ---
def _cell_score_hue_only(hsv_cell):
    h, s, v = hsv_cell[:, :, 0], hsv_cell[:, :, 1], hsv_cell[:, :, 2]
    not_shadow = v > 30
    not_sky    = ~((h > 90) & (h < 130) & (s > 50))
    valid      = not_shadow & not_sky
    green = np.sum((h >= 35) & (h <= 85) & valid)           # hue only
    brown = np.sum((h >= 10) & (h < 35)  & valid)
    return green / (green + brown) if (green + brown) > 0 else 0.0

img = cv2.imread(IMAGE)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
h_px, w_px = img.shape[:2]
cell_h, cell_w = h_px // GRID_SIZE, w_px // GRID_SIZE

rgb_before = np.zeros((GRID_SIZE, GRID_SIZE))
for i in range(GRID_SIZE):
    for j in range(GRID_SIZE):
        cell = hsv[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
        rgb_before[i, j] = _cell_score_hue_only(cell)

# --- After: fixed rgb_health_grid (hue + s > 80) ---
rgb_after = rgb_health_grid(IMAGE, grid_size=GRID_SIZE, label='coyote-sat-fixed')

# --- NDVI grid over the same crop ---
ndvi_scores = compute_ndvi(
    'data/sentinel_data/2022_aug/T10SEG_20220812T184931_B04_10m.jp2',
    'data/sentinel_data/2022_aug/T10SEG_20220812T184931_B08_10m.jp2',
    '2022-Aug-CoyoteHills', grid_size=GRID_SIZE,
    lat=LAT, lon=LON, half_m=HALF_M,
)

disc_before = np.abs(rgb_before - ndvi_scores)
disc_after  = np.abs(rgb_after  - ndvi_scores)

# --- Side-by-side comparison ---
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for ax, disc, title in zip(
    axes,
    [disc_before, disc_after],
    ['Hue only  (yesterday)', 'Hue + saturation > 80  (today)'],
):
    im = ax.imshow(disc, cmap='Reds', vmin=0, vmax=1)
    ax.set_title(f'RGB vs NDVI Discrepancy\n{title}', fontsize=11)
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            ax.text(j, i, f'{disc[i,j]:.2f}', ha='center', va='center', fontsize=7)

plt.colorbar(im, ax=axes[1], label='|RGB score − NDVI score|')
plt.suptitle(
    'Saturation filter effect on water-channel misclassification\n'
    'Coyote Hills area — Sentinel-2 true-color PNG, 2022-Aug',
    fontsize=11,
)
plt.tight_layout()
plt.savefig('data/sentinel_data/combined_maps/discrepancy_comparison.png', dpi=150)
plt.close()
print('Saved to data/sentinel_data/combined_maps/discrepancy_comparison.png')
