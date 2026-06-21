# CLAUDE.md

LEAF Guardian monitors native plant health at restoration sites by combining Sentinel-2 satellite imagery with DJI Tello drone photos. The satellite pipeline computes NDVI and ExG-based green scores on a 9×9 grid over a 2 km crop of the target site; the drone pipeline flies a lawnmower survey, stitches the photos, and scores plant health via HSV classification. Both pipelines produce a 0–1 score per grid cell that feeds into `combine_health_maps()`.

---

## Scripts

All scripts must be run from the **repo root** — data paths are relative.

| Script | What it does |
|---|---|
| `software/ndvi_pipeline/run_combined.py` | Orchestrator: runs sentinel_rgb → sentinel_ndvi → combine in one shot |
| `software/ndvi_pipeline/sentinel_ndvi.py` | Reads Sentinel-2 B04/B08, computes NDVI, saves full-res map + scored grid |
| `software/ndvi_pipeline/sentinel_rgb.py` | Reads Sentinel-2 B04/B03/B02, computes ExG health grid + true-color composite |
| `software/ndvi_pipeline/combine_maps.py` | Averages RGB + NDVI scores cell-by-cell; adds discrepancy layer |
| `software/ndvi_pipeline/rgb_health.py` | Standalone: scores a single drone JPEG using HSV green/brown ratios |
| `software/ndvi_pipeline/stitch_grid.py` | Stitches a folder of row.col.jpg tiles into a composite and runs health analysis |
| `software/ndvi_pipeline/sentinel_utils.py` | Shared utility: `crop_band()` for windowed Sentinel-2 reads (used by ndvi + rgb) |
| `software/ndvi_pipeline/compare_saturation_filter.py` | One-off: before/after comparison of the saturation filter on rgb_health |
| `software/tello_control/waypoint_mission.py` | Lawnmower drone survey (MockTello by default, `--real` for live hardware); auto-stitches after landing |

---

## Naming conventions

- **Drone photos**: `<row>.<col>.jpg` with 1-based indexing — top-left tile is `1.1.jpg`, bottom-right of a 3×3 is `3.3.jpg`. `stitch_grid.py` auto-detects grid dimensions from the highest row/col it finds.
- **Labels**: short strings passed to each pipeline function (e.g., `2022-Aug-CoyoteHills`) that appear verbatim in output filenames — `ndvi_grid_2022-Aug-CoyoteHills.png`, `combined_map_2022-Aug-CoyoteHills.png`, etc.
- **Flight logs**: `flight_<YYYYMMDDTHHMMSS>.json` written to `data/flight_logs/` after each mission.

---

## Hardware dependencies

Two parts of the codebase require physical hardware and cannot be exercised otherwise:

1. **`capture_photo_real()`** in `waypoint_mission.py` — grabs a live BGR frame from the Tello video stream via `tello.get_frame_read().frame`; requires `tello.streamon()` to have been called before takeoff and the laptop to be on the Tello Wi-Fi network.
2. **NoIR NDVI capture** — planned feature: a Pi NoIR camera mounted on the drone for in-flight near-infrared imaging without relying on Sentinel-2. Not yet implemented.

Everything else runs without hardware. The MockTello in `waypoint_mission.py` simulates connect, takeoff, moves, and landing, and writes real JPEG placeholders so the full stitch pipeline can be tested end-to-end.

---

## June 26 hardware test

First live flight with the real Tello. Key things to verify before trusting `capture_photo_real()` in production:

- Give `streamon()` 1–2 s to stabilise before the first move command
- Move commands are blocking but the drone may still be decelerating when `get_frame_read()` is called — add a short sleep if captures are blurry
- Check JPEG saturation fidelity against HSV scoring thresholds (green H 35–85, S > 80)

See [docs/first_flight_plan.md](docs/first_flight_plan.md) for the full checklist.

---

## Data layout

```
data/
├── sentinel_data/
│   ├── 2022_aug/          # Raw .jp2 band files (B02, B03, B04, B08)
│   ├── color_images/      # Full-scene NDVI map and true-color composite PNGs
│   ├── grid_analyses/     # Scored grid PNGs (NDVI grid + satellite RGB grid)
│   └── combined_maps/     # Fused combined score + discrepancy PNGs
├── drone_imagery/
│   ├── test/              # Single test photos for rgb_health.py
│   ├── grid_test/         # 2×2 real photo grid + stitched_results/
│   └── survey/            # 3×3 mock mission output + stitched_results/
└── flight_logs/           # JSON flight logs written by waypoint_mission.py
```

Large `.tif` files are gitignored.
