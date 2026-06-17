# Leaf Guardian — Project Summary

## What It Does

Leaf Guardian is an autonomous vegetation health monitoring system for native plant restoration sites. It fuses two independent remote sensing pipelines — satellite multispectral imagery and drone RGB photography — into a single combined health score per grid cell, with a discrepancy layer that flags where the two sensors disagree.

The current implementation focuses on **Coyote Hills Regional Park, Fremont CA**, using a Sentinel-2 L2A acquisition from August 2022 and ground-level drone photos taken in June 2026.

---

## Repository Layout

```
leaf-guardian/
├── data/
│   ├── sentinel_data/
│   │   ├── 2022_aug/                    # Raw Sentinel-2 L2A band files (.jp2)
│   │   │   ├── T10SEG_20220812T184931_B02_10m.jp2   # Blue
│   │   │   ├── T10SEG_20220812T184931_B03_10m.jp2   # Green
│   │   │   ├── T10SEG_20220812T184931_B04_10m.jp2   # Red
│   │   │   └── T10SEG_20220812T184931_B08_10m.jp2   # Near-Infrared
│   │   ├── color_images/                # Full-scene color output images
│   │   │   ├── ndvi_<label>.png         # Full-resolution NDVI map (RdYlGn)
│   │   │   └── sat_rgb_<label>.png      # True-color RGB composite (B04/B03/B02)
│   │   ├── grid_analyses/               # Per-cell scored grid maps
│   │   │   ├── ndvi_grid_<label>.png    # NDVI health grid with cell scores
│   │   │   └── sat_rgb_grid_<label>.png # Satellite RGB (ExG) health grid
│   │   └── combined_maps/               # Fused outputs and comparisons
│   │       ├── combined_map_<label>.png # Side-by-side: combined score + discrepancy
│   │       └── discrepancy_comparison.png  # Before/after filter comparison
│   ├── drone_imagery/
│   │   ├── test/                        # Raw drone/phone .jpg photos
│   │   │   └── healthy_image.jpg        # Example ground-level photo
│   │   └── rgb_grid_<label>.png         # Drone RGB health grids
│   └── flight_logs/                     # JSON flight logs written by waypoint_mission.py
│
└── software/
    ├── ndvi_pipeline/                   # All processing scripts (run from repo root)
    │   ├── sentinel_utils.py            # Shared utility: crop_band()
    │   ├── sentinel_ndvi.py             # Sentinel-2 NDVI pipeline
    │   ├── sentinel_rgb.py              # Sentinel-2 true-color + RGB health grid
    │   ├── rgb_health.py                # Drone photo RGB health grid
    │   ├── combine_maps.py              # Fuse satellite RGB + NDVI grids
    │   ├── run_combined.py              # Main entry point: runs all three + combine
    │   └── compare_saturation_filter.py # One-off: before/after saturation filter comparison
    └── tello_control/
        └── waypoint_mission.py          # Square waypoint mission + MockTello for testing
```

---

## Data Sources

### Sentinel-2 L2A — August 12, 2022
- **Tile**: T10SEG (UTM Zone 10N, EPSG:32610)
- **Full tile size**: 10,980 × 10,980 pixels at 10 m/px (~100 km × 100 km)
- **Bands used**: B02 (Blue, 490 nm), B03 (Green, 560 nm), B04 (Red, 665 nm), B08 (NIR, 842 nm)
- **Reflectance scaling**: raw DN values divided by 10,000 to get surface reflectance (0.0–1.0)
- **Crop**: all processing is windowed to a 2 km × 2 km area centred on the target coordinates; the full tile is never loaded into memory

### Drone RGB — June 2026
- Phone/Tello camera JPEGs stored in `data/drone_imagery/test/`
- Processed in BGR → HSV colour space via OpenCV

---

## Pipelines

### 1. Satellite NDVI (`sentinel_ndvi.py`)

**Entry point**: `compute_ndvi(red_path, nir_path, label, grid_size, lat, lon, half_m)`

1. `crop_band()` windows the B04 and B08 `.jp2` files to the 2 km crop around `(lat, lon)`
2. Computes NDVI = `(NIR − Red) / (NIR + Red + 1e-10)`, clipped to [−1, 1]
3. Saves a full-resolution NDVI colour map to `color_images/`
4. Calls `ndvi_health_grid()` which divides the array into an N×N grid, scores each cell as `clip(mean_ndvi, 0, 0.8) / 0.8`, and saves the scored grid to `grid_analyses/`
5. Returns the score grid

**Scoring ceiling**: 0.8 NDVI rather than the theoretical 1.0, because dense healthy vegetation in California realistically plateaus around 0.6–0.8 in late summer.

### 2. Satellite True-Color RGB (`sentinel_rgb.py`)

**Entry point**: `compute_sentinel_rgb(b04_path, b03_path, b02_path, lat, lon, half_m, label, grid_size)`

1. `crop_band()` windows B04, B03, B02 to the same 2 km crop
2. Stacks them as R/G/B, applies a 98th-percentile linear stretch for display, saves to `color_images/`
3. Calls `sat_rgb_health_grid()` which scores each N×N cell using **Excess Green**:
   - `ExG = 2G − R − B` (all in 0–1 surface reflectance)
   - Score = `clip(mean_ExG, 0, 0.12) / 0.12`
   - Ceiling of 0.12 reflects the maximum ExG achievable in dense green cover at 10 m resolution
4. Saves scored grid to `grid_analyses/`, returns the score grid

**Why ExG over HSV for satellite data**: satellite surface reflectance values are float32 (0–1), not uint8 BGR, so OpenCV HSV thresholds don't apply cleanly. ExG is a direct arithmetic measure of green reflectance dominance.

### 3. Drone RGB (`rgb_health.py`)

**Entry point**: `rgb_health_grid(image_path, grid_size, label)`

1. Reads a JPEG drone photo with OpenCV, converts BGR → HSV (uint8, H: 0–179)
2. Per N×N cell, `rgb_cell_score()` classifies pixels:
   - **Green**: H 35–85 AND saturation > 80 AND not shadow (V > 30) AND not sky (H 90–130 with S > 50)
   - **Brown**: H 10–35, same shadow/sky exclusions
   - Score = `green / (green + brown)`
3. Saves scored grid to `data/drone_imagery/`, returns the score grid

**Saturation filter (added 2026-06-16)**: the original hue-only green mask was misclassifying bay water and algae-tinted surfaces as vegetation, because their hue falls in the 35–85 range but their colour is desaturated. Adding `s > 80` removed these false positives without affecting true foliage.

### 4. Fusion (`combine_maps.py`)

**Entry point**: `combine_health_maps(rgb_scores, ndvi_scores, label)`

- **Combined score**: `(rgb_scores + ndvi_scores) / 2` — equal weight, cell-by-cell average
- **Discrepancy**: `abs(rgb_scores − ndvi_scores)` — how much the two sensors disagree per cell
- Saves a two-panel figure (combined health map + discrepancy map) to `combined_maps/`
- Returns both arrays

**Interpreting the discrepancy**:
- High NDVI, low RGB → dry annual grass (NIR structural reflectance remains but visible green pigment is gone — common in August California)
- High RGB, low NDVI → possible misclassification (e.g., algae-coloured water before the saturation fix), or dense but narrow shrubs in a mostly bare cell
- Both agree high → reliably green woody vegetation
- Both agree low → bare soil, impervious surface, or open water

### 5. Tello Waypoint Mission (`tello_control/waypoint_mission.py`)

**Entry point**: `run_mission(tello)` — accepts either a real `djitellopy.Tello` or the built-in `MockTello`.

1. Calls `tello.connect()`, logs battery percentage before takeoff
2. Calls `tello.takeoff()`
3. Flies a **4-point 50 cm square**: forward → right → back → left
4. Calls `tello.land()`, logs battery percentage after landing
5. `save_flight_log()` writes a timestamped JSON to `data/flight_logs/` containing: timestamp, battery start/end/used, total duration, pattern name, and the full waypoint list

**Switching between mock and real hardware**:
```bash
python software/tello_control/waypoint_mission.py          # MockTello (default)
python software/tello_control/waypoint_mission.py --real   # live Tello over Wi-Fi
```

**MockTello**: simulates `connect()`, `takeoff()`, `land()`, `get_battery()`, and all four `move_*()` commands. Battery starts at 85% and drains 1% per move, giving realistic log output without hardware.

### 6. Main Runner (`run_combined.py`)

Calls pipelines 2 → 1 → 4 in sequence for the same crop area and grid size, yielding consistent spatially-aligned grids ready for fusion.

---

## Shared Utility (`sentinel_utils.py`)

`crop_band(path, lat, lon, half_m=1000)`

- Opens the `.jp2` with rasterio, reprojects the WGS84 `(lat, lon)` centre into the file's CRS (EPSG:32610 for these tiles) using `rasterio.warp.transform`
- Computes the pixel window from the affine transform, clamps it to the file bounds
- Returns a windowed float64 array (DN / 10000)
- Used by both `sentinel_ndvi.py` and `sentinel_rgb.py` so crop geometry is always identical

---

## Current Study Area

| Parameter | Value |
|---|---|
| Site | Coyote Hills Regional Park, Fremont CA |
| Sentinel tile | T10SEG, 2022-08-12 |
| Last crop centre | 37.552707°N, 122.092559°W |
| Crop size | 2 km × 2 km (200 × 200 px at 10 m/px) |
| Grid size | 9 × 9 cells (~222 m per cell) |
| Mean NDVI (cropped) | 0.122 (current crop includes bay water) |

---

## Running the Pipeline

All scripts must be run from the **repo root** because all data paths are relative:

```bash
# Full pipeline: satellite RGB + NDVI + fused combined map
python software/ndvi_pipeline/run_combined.py

# Individual pipelines
python software/ndvi_pipeline/sentinel_ndvi.py
python software/ndvi_pipeline/sentinel_rgb.py

# Drone photo analysis
python software/ndvi_pipeline/rgb_health.py

# Saturation filter before/after comparison
python software/ndvi_pipeline/compare_saturation_filter.py
```

To change the study area, update `_LAT`, `_LON`, and `_HALF_M` in `run_combined.py` (and the matching `__main__` blocks in `sentinel_ndvi.py` and `sentinel_rgb.py`).

---

## Dependencies

```bash
pip install numpy matplotlib rasterio opencv-python djitellopy
```

| Package | Used for |
|---|---|
| `numpy` | Array math throughout |
| `matplotlib` | All plot and PNG output |
| `rasterio` | Reading Sentinel-2 `.jp2` files, windowed reads, CRS reprojection |
| `opencv-python` (cv2) | Drone JPEG loading, BGR → HSV conversion |
| `djitellopy` | Tello SDK — used in `waypoint_mission.py` for live drone control |

---

## Running the Drone Mission

```bash
# Test the full mission logic against MockTello (no hardware needed)
python software/tello_control/waypoint_mission.py

# Fly on a real Tello (must be connected to Tello Wi-Fi first)
python software/tello_control/waypoint_mission.py --real
```

Flight logs are written to `data/flight_logs/flight_<timestamp>.json`.

---

## Planned Work

- **Grid survey pattern**: expand `waypoint_mission.py` from a single square to a lawnmower grid that covers the full study area, triggering a photo capture at each waypoint to feed into `rgb_health.py`
- **Multi-date NDVI change detection**: diff NDVI grids across seasons to track restoration progress over time
- **Ground-truth validation**: co-register drone RGB grid cells against satellite grid cells using GPS-tagged photos, to quantify how well the two sensors agree at the same physical location
