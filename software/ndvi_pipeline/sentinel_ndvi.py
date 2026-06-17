import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import rasterio
import matplotlib.pyplot as plt
from sentinel_utils import crop_band

def ndvi_health_grid(ndvi_array, grid_size, label):
    h, w = ndvi_array.shape
    cell_h, cell_w = h // grid_size, w // grid_size

    scores = np.zeros((grid_size, grid_size))
    for i in range(grid_size):
        for j in range(grid_size):
            # Slice out one grid cell from the full NDVI array
            cell = ndvi_array[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            mean_ndvi = np.mean(cell)
            # Normalize to 0-1: healthy dense vegetation tops out around 0.8 NDVI,
            # so we use that as the ceiling rather than the theoretical max of 1.0
            scores[i, j] = np.clip(mean_ndvi, 0, 0.8) / 0.8

    # Mask out zero-score cells so they render black
    masked_scores = np.ma.masked_equal(scores, 0)

    # RdYlGn: red = stressed/bare, yellow = moderate, green = healthy
    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad(color='black')

    plt.figure(figsize=(6, 6))
    plt.imshow(masked_scores, cmap=cmap, vmin=0, vmax=1)
    plt.colorbar(label='Health Score (0-1)')
    plt.title(f'NDVI Grid Health Map - {label}')
    # Overlay the numeric score on each cell
    for i in range(grid_size):
        for j in range(grid_size):
            text_color = 'black' if scores[i,j] == 0 else 'black'
            plt.text(j, i, f'{scores[i,j]:.2f}', ha='center', va='center',
                     color=text_color, fontsize=8)
    plt.savefig(f'data/sentinel_data/grid_analyses/ndvi_grid_{label}.png', dpi=150)
    plt.close()
    print(f"Saved grid map to data/sentinel_data/grid_analyses/ndvi_grid_{label}.png")
    print(scores)
    return scores

def compute_ndvi(red_path, nir_path, label, grid_size=4, lat=None, lon=None, half_m=1000):
    if lat is not None:
        red = crop_band(red_path, lat, lon, half_m)
        nir = crop_band(nir_path, lat, lon, half_m)
    else:
        # Sentinel-2 stores reflectance as integers scaled by 10000; divide to get 0.0-1.0
        with rasterio.open(red_path) as f:
            red = f.read(1).astype(float) / 10000.0
        with rasterio.open(nir_path) as f:
            nir = f.read(1).astype(float) / 10000.0

    # NDVI formula: healthy plants absorb red light and reflect NIR strongly,
    # so high NDVI (near 1.0) = dense healthy vegetation, low/negative = bare soil or water
    ndvi = (nir - red) / (nir + red + 1e-10)  # 1e-10 avoids division by zero
    ndvi = np.clip(ndvi, -1, 1)

    # Exclude pixels below -0.5 (water, cloud shadows) from the site average
    mean_ndvi = float(np.nanmean(ndvi[ndvi > -0.5]))
    print(f"{label}: Mean NDVI = {mean_ndvi:.3f}")

    # Save a full-resolution NDVI map for the site
    plt.figure(figsize=(10, 8))
    plt.imshow(ndvi, cmap='RdYlGn', vmin=-0.2, vmax=0.8)
    plt.colorbar(label='NDVI')
    plt.title(f'Sentinel-2 NDVI — {label}')
    plt.savefig(f'data/sentinel_data/color_images/ndvi_{label}.png', dpi=150)
    plt.close()
    print(f"Saved to data/sentinel_data/color_images/ndvi_{label}.png")

    return ndvi_health_grid(ndvi, grid_size, label)

if __name__ == '__main__':
    # Coyote Hills, August 2022 — cropped 2 km × 2 km around the restoration site
    compute_ndvi(
        'data/sentinel_data/2022_aug/T10SEG_20220812T184931_B04_10m.jp2',
        'data/sentinel_data/2022_aug/T10SEG_20220812T184931_B08_10m.jp2',
        '2022-Aug-CoyoteHills',
        grid_size=9,
        lat=37.552707, lon=-122.092559, half_m=1000,
    )