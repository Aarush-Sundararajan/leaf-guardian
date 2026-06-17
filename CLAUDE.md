# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

leaf-guardian is an autonomous drone system for native plant health monitoring at ecological restoration sites. It fuses two data sources:
- **Sentinel-2 satellite imagery** — multi-spectral bands used to compute NDVI
- **Tello drone RGB imagery** — ground-level photos analyzed via HSV color classification

## Running Scripts

All scripts must be run from the **repo root** because data paths are relative (e.g., `data/sentinel_data/...`).

```bash
# Compute NDVI from Sentinel-2 bands and generate health grid map
python software/ndvi_pipeline/sentinel_ndvi.py

# Compute RGB health grid from drone imagery
python software/ndvi_pipeline/rgb_health.py
```

Scripts are not importable modules — each has a hardcoded entry-point call at the bottom that should be updated to point at the target data files before running.

## Dependencies

```bash
pip install numpy matplotlib rasterio opencv-python djitellopy
```

- `rasterio` — reads Sentinel-2 `.jp2` band files
- `cv2` (opencv-python) — reads drone `.jpg` images and converts BGR→HSV
- `djitellopy` — Tello drone SDK (used in `software/tello_control/`, not yet implemented)

## Architecture

### NDVI Pipeline (`software/ndvi_pipeline/sentinel_ndvi.py`)

1. **`compute_ndvi(red_path, nir_path, label, grid_size)`** — reads Sentinel-2 B04 (Red) and B08 (NIR) `.jp2` files, divides raw DN values by 10000 (Sentinel-2 surface reflectance scaling factor), computes NDVI = `(NIR - Red) / (NIR + Red + 1e-10)`, saves a full NDVI map PNG, then calls `ndvi_health_grid`.
2. **`ndvi_health_grid(ndvi_array, grid_size, label)`** — divides the NDVI array into an NxN grid, scores each cell as `clip(mean_ndvi, 0, 0.8) / 0.8` (0–1 scale), and saves a color-coded grid PNG to `data/sentinel_data/`.

### RGB Pipeline (`software/ndvi_pipeline/rgb_health.py`)

1. **`rgb_health_grid(image_path, grid_size, label)`** — loads a drone photo, converts BGR→HSV, divides into NxN cells, scores each via `rgb_cell_score`.
2. **`rgb_cell_score(hsv_cell)`** — classifies pixels as green (H: 35–85) or brown (H: 10–35), filters out shadows (V ≤ 30) and sky (H: 90–130 with high saturation), returns `green / (green + brown)`.

Output PNGs go to `data/drone_imagery/`.

### Planned: Tello Control (`software/tello_control/`)

Empty placeholder. Will use `djitellopy` to automate flight paths over restoration sites and capture imagery for the RGB pipeline.

## Data Layout

- `data/sentinel_data/2022_aug/` — Sentinel-2 `.jp2` band files (B04=Red, B08=NIR)
- `data/sentinel_data/*.png` — NDVI map and grid outputs
- `data/drone_imagery/test/` — raw Tello/phone camera `.jpg` images
- `data/drone_imagery/*.png` — RGB health grid outputs
- `data/flight_logs/` — placeholder for Tello flight logs

Large `.tif` files are gitignored.
