# Development Log

## June 9, 2026
- Created GitHub repo `leaf-guardian` with initial folder structure
- Installed djitellopy, opencv-python, numpy, matplotlib via `py -m pip`
- Sent CA LEAF outreach email requesting domain expertise on plant stress 
  indicators, species survival rates, and seasonal monitoring priorities
- Ordered Camrise Tello Boost Combo (drone + 3 batteries + charging hub)
- Added `.gitignore` for large raw data files
- FAA registration completed

## June 10, 2026
- Created Copernicus Data Space account
- Located Coyote Hills Regional Park (37.5579, -122.0656) as placeholder 
  CA LEAF site for pipeline development
- Downloaded first Sentinel-2 L2A scene (Aug 12, 2022)
- Built `sentinel_ndvi.py` — reads B04 (red) and B08 (NIR) bands, computes 
  NDVI, outputs color-coded PNG
- Generated first NDVI map: Mean NDVI = 0.123 for Coyote Hills, Aug 2022
- Resolved Python environment issue (Windows `py` launcher vs `python3`)
- Wrote initial README
- Raw `.jp2` files excluded from repo via `.gitignore` — only processed 
  outputs committed

## June 12, 2026
- Pivoted project scope: replaced satellite-based time-series approach 
  with drone-based RGB + NDVI cross-validation (per revised project outline)
- Built `rgb_health_grid()` in `rgb_health.py`:
  - Splits image into NxN grid
  - Excludes sky (blue hue) and shadow (low brightness) pixels before scoring
  - Computes green/brown ratio per cell, output 0-1
  - Zero-score cells rendered black on output map
- Built `ndvi_health_grid()` in `sentinel_ndvi.py`:
  - Splits NDVI array into NxN grid
  - Normalizes mean NDVI per cell (clipped 0-0.8) to 0-1 scale
  - Zero-score cells rendered black on output map
- Both classifiers now share a common 0-1 scale and grid format — 
  groundwork for combined RGB+NDVI map
- Tested grid sizes 4x4, 6x6, and 10x10 on Coyote Hills NDVI data
- Established NDVI interpretation reference table (water/bare/stressed/
  healthy/dense vegetation ranges) for classifier thresholds

## June 13, 2026
- Set up Claude Code (native Windows install), connected to leaf-guardian repo
- Built `combine_maps.py`:
  - `combine_health_maps()` averages RGB and NDVI grid scores into a 
    combined health map
  - Computes discrepancy map (absolute difference between RGB and NDVI 
    scores per cell)
- Initial combine test (RGB from test plant photo + NDVI from full 
  Sentinel-2 tile) showed near-total discrepancy — confirmed this was due 
  to comparing unrelated locations, not a code issue
- Built `sentinel_rgb.py` — generates true-color image from B02/B03/B04 
  bands of the same Sentinel-2 scene used for NDVI
- Added cropping step (rasterio windowed read) to align RGB and NDVI to 
  the same ~2km area for direct comparison
- Re-centered crop coordinates to 37.5555, -122.0780 to better target 
  Coyote Hills park area (grassland/wetland) instead of adjacent 
  residential/industrial zone
- Ran full aligned pipeline (true color, NDVI, combined map, discrepancy) 
  on properly cropped Coyote Hills data — first meaningful same-location 
  RGB vs NDVI comparison
- **MAJOR INSSUE:** Highest discrepancy region corresponds to a dark green 
  water channel — RGB misclassifies it as healthy vegetation (green hue), 
  while NDVI correctly identifies it as non-vegetation (water). 
  Demonstrates a concrete case where NIR-based classification outperforms 
  visible-color classification — candidate finding for methodology writeup
