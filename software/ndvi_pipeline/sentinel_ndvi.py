import numpy as np
import rasterio
import matplotlib.pyplot as plt

def compute_ndvi(red_path, nir_path, label):
    with rasterio.open(red_path) as f:
        red = f.read(1).astype(float) / 10000.0
    with rasterio.open(nir_path) as f:
        nir = f.read(1).astype(float) / 10000.0

    ndvi = (nir - red) / (nir + red + 1e-10)
    ndvi = np.clip(ndvi, -1, 1)

    mean_ndvi = float(np.nanmean(ndvi[ndvi > -0.5]))
    print(f"{label}: Mean NDVI = {mean_ndvi:.3f}")

    plt.figure(figsize=(10, 8))
    plt.imshow(ndvi, cmap='RdYlGn', vmin=-0.2, vmax=0.8)
    plt.colorbar(label='NDVI')
    plt.title(f'Sentinel-2 NDVI — {label}')
    plt.savefig(f'data/sentinel_data/ndvi_{label}.png', dpi=150)
    plt.close()
    print(f"Saved to data/sentinel_data/ndvi_{label}.png")

compute_ndvi(
    'data/sentinel_data/2022_aug/T10SEG_20220812T184931_B04_10m.jp2',
    'data/sentinel_data/2022_aug/T10SEG_20220812T184931_B08_10m.jp2',
    '2022-Aug-CoyoteHills'
)