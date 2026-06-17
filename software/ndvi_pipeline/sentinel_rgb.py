import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib.pyplot as plt
from sentinel_utils import crop_band

_BAND_DIR = 'data/sentinel_data/2022_aug'
_PREFIX   = 'T10SEG_20220812T184931'


def sat_rgb_cell_score(r_cell, g_cell, b_cell):
    """Score vegetation health from satellite surface reflectance (0–1 float).

    Uses Excess Green (ExG = 2G − R − B) as a proxy for photosynthetically
    active cover.  Dense green vegetation reaches ~0.12; bare soil/urban sits
    near 0; water goes slightly negative.  Ceiling of 0.12 normalises to 0–1.
    """
    exg = 2.0 * g_cell - r_cell - b_cell
    return float(np.mean(np.clip(exg, 0.0, 0.12) / 0.12))


def sat_rgb_health_grid(r, g, b, grid_size, label):
    h, w = r.shape
    cell_h, cell_w = h // grid_size, w // grid_size

    scores = np.zeros((grid_size, grid_size))
    for i in range(grid_size):
        for j in range(grid_size):
            r_c = r[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            g_c = g[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            b_c = b[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            scores[i, j] = sat_rgb_cell_score(r_c, g_c, b_c)

    masked = np.ma.masked_equal(scores, 0)
    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad(color='black')

    plt.figure(figsize=(6, 6))
    plt.imshow(masked, cmap=cmap, vmin=0, vmax=1)
    plt.colorbar(label='Health Score (0-1)')
    plt.title(f'Sentinel RGB Grid Health Map - {label}')
    for i in range(grid_size):
        for j in range(grid_size):
            plt.text(j, i, f'{scores[i,j]:.2f}', ha='center', va='center', fontsize=8)
    plt.savefig(f'data/sentinel_data/grid_analyses/sat_rgb_grid_{label}.png', dpi=150)
    plt.close()
    print(f'Saved to data/sentinel_data/grid_analyses/sat_rgb_grid_{label}.png')
    print(scores)
    return scores


def compute_sentinel_rgb(b04_path, b03_path, b02_path, lat, lon, half_m, label, grid_size):
    r = crop_band(b04_path, lat, lon, half_m)
    g = crop_band(b03_path, lat, lon, half_m)
    b = crop_band(b02_path, lat, lon, half_m)

    # Linear percentile stretch: clip at 98th percentile so bright outliers
    # (specular water, rooftops) don't wash out the vegetation signal.
    rgb_stack = np.stack([r, g, b], axis=2)
    p98 = np.percentile(rgb_stack, 98)
    rgb_display = np.clip(rgb_stack / p98, 0.0, 1.0)

    plt.figure(figsize=(7, 7))
    plt.imshow(rgb_display)
    plt.axis('off')
    plt.title(f'Sentinel-2 True Color (B04/B03/B02) — {label}')
    plt.tight_layout()
    plt.savefig(f'data/sentinel_data/color_images/sat_rgb_{label}.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Saved to data/sentinel_data/color_images/sat_rgb_{label}.png')

    return sat_rgb_health_grid(r, g, b, grid_size, label)


if __name__ == '__main__':
    compute_sentinel_rgb(
        f'{_BAND_DIR}/{_PREFIX}_B04_10m.jp2',
        f'{_BAND_DIR}/{_PREFIX}_B03_10m.jp2',
        f'{_BAND_DIR}/{_PREFIX}_B02_10m.jp2',
        lat=37.552707, lon=-122.092559, half_m=1000,
        label='2022-Aug-CoyoteHills', grid_size=9,
    )
