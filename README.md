# LEAF Guardian

LEAF Guardian is a vegetation health monitor for native plant restoration sites. The core idea is to fuse satellite multispectral data with drone RGB photography to get a per-plot health score you can track over time — without requiring weekly field visits. The satellite side pulls Sentinel-2 L2A imagery and computes NDVI from B04/B08 bands; the drone side flies a lawnmower pattern over the site, stitches the photos into a composite, and scores plant health through HSV color analysis. Both pipelines output a 0–1 score per grid cell, which `combine_health_maps()` blends into a combined map alongside a discrepancy layer that flags where the two sensors disagree. The current study area is Coyote Hills Regional Park, Fremont CA, using an August 2022 Sentinel-2 baseline and drone imagery from June 2026.

---

## Architecture

```
                    SATELLITE PIPELINE
  ┌────────────────────────────────────────────────────────┐
  │                                                        │
  │  Sentinel-2 B04 (Red) ─┐                              │
  │  Sentinel-2 B08 (NIR) ─┴──► sentinel_ndvi.py          │
  │                               └── NDVI scores         │
  │                                    (9×9 grid) ─────┐  │
  │  Sentinel-2 B04/B03/B02 ──► sentinel_rgb.py        │  │
  │                               └── ExG scores       │  │
  │                                    (9×9 grid) ─────┤  │
  └────────────────────────────────────────────────────┼──┘
                                                       ▼
                                            combine_health_maps()
                                          ┌───────────────────────┐
                                          │  combined_map.png     │
                                          │  (score + discrepancy)│
                                          └───────────────────────┘
                                                       ▲
  ┌────────────────────────────────────────────────────┤
  │                   DRONE PIPELINE                   │ (future)
  │                                                    │
  │  DJI Tello ──► waypoint_mission.py                 │
  │                 (lawnmower survey)                 │
  │                       │                            │
  │                       ▼                            │
  │              row.col.jpg photos                    │
  │                       │                            │
  │                       ▼                            │
  │              stitch_grid.py                        │
  │                       │                            │
  │           ┌───────────┴───────────┐                │
  │           ▼                       ▼                │
  │   composite_NxM.png      analyzed_NxM.png  ────────┘
  │   (raw stitch)           (HSV-scored overlay)
  └──────────────────────────────────────────────
```

The drone RGB scores currently feed a standalone analyzed composite. Eventually they'll replace the satellite ExG scores in the fusion step, giving a true satellite NDVI + ground-level drone RGB combined map.

---

## What you get per run

Every full analysis produces three deliverables:

| Output | Location | What it shows |
|---|---|---|
| **RGB health grid** | `data/sentinel_data/grid_analyses/sat_rgb_grid_<label>.png` | Excess Green score per cell from satellite bands |
| **NDVI health grid** | `data/sentinel_data/grid_analyses/ndvi_grid_<label>.png` | NIR-based vegetation density score per cell |
| **Combined map** | `data/sentinel_data/combined_maps/combined_map_<label>.png` | Fused score (left) and discrepancy between sensors (right) |

Drone runs also produce `composite_NxM.png` and `analyzed_NxM.png` in `data/drone_imagery/<label>/stitched_results/`.

---

## Pipeline status

| Component | Status |
|---|---|
| `sentinel_ndvi.py` — Sentinel-2 NDVI grid | Working |
| `sentinel_rgb.py` — True-color composite + ExG health grid | Working |
| `combine_maps.py` — Fuse RGB + NDVI into combined map | Working |
| `run_combined.py` — Full satellite pipeline in one command | Working |
| `rgb_health.py` — Single drone photo health grid | Working |
| `stitch_grid.py` — Grid stitcher + composite health analysis | Working |
| `waypoint_mission.py` (MockTello mode) | Mock-tested |
| `waypoint_mission.py` (--real, live Tello) | Pending hardware — June 26 |
| `capture_photo_real()` — Live frame grab from Tello stream | Pending hardware — June 26 |
| NoIR NDVI capture from drone | Planned |

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/Aarush-Sundararajan/leaf-guardian.git
cd leaf-guardian

# 2. Install dependencies
pip install numpy matplotlib rasterio opencv-python djitellopy

# 3. Get Sentinel-2 data
#    Download a Sentinel-2 L2A scene from browser.dataspace.copernicus.eu
#    Place B02, B03, B04, B08 .jp2 files in data/sentinel_data/2022_aug/

# 4. Run the full satellite pipeline (must be run from repo root)
python software/ndvi_pipeline/run_combined.py

# 5. Run a mock drone survey (no hardware required)
python software/tello_control/waypoint_mission.py

# 6. Stitch an existing folder of grid photos
python software/ndvi_pipeline/stitch_grid.py data/drone_imagery/grid_test

# 7. Live drone mission (connect to Tello Wi-Fi first)
python software/tello_control/waypoint_mission.py --real
```

All scripts must be run from the **repo root** — data paths are relative and will break if you run from inside a subdirectory.

---

## Hardware testing

First live flight is planned for **June 26, 2026**. See [docs/first_flight_plan.md](docs/first_flight_plan.md) for the pre-flight checklist covering stream initialization, capture timing, and JPEG quality verification against HSV scoring thresholds.

---

## Partner organization

CA LEAF — California native plant restoration. Outreach initiated June 2026.

## Competition targets

- Regeneron STS — November 2026
- ISEF — Spring 2027
