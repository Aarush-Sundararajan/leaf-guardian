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

## June 15, 2026
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

 ## June 16, 2026

Spent today fixing yesterday's water problem and cleaning up the project structure.

The fix for the green water misclassification was simpler than expected — added a saturation check (s > 80) to the green mask in rgb_health.py. Turns out water and algae-tinted surfaces share the same hue range as healthy leaves (35-85), but they're washed out compared to actual foliage. The saturation filter catches that difference and it worked without breaking detection on real plants.

Also reorganized the data folder since things were getting messy — split sentinel_data into color_images, grid_analyses, and combined_maps subfolders instead of everything dumped in one place. Pulled the cropping logic that was duplicated between sentinel_ndvi.py and sentinel_rgb.py into one shared function (sentinel_utils.py) so both scripts crop the exact same area every time — no more wondering if NDVI and RGB are actually looking at the same patch of ground.

Re-centered the crop again (37.552707N, 122.092559W) but it's still picking up some bay water — mean NDVI came out to 0.122. Decided not to keep chasing a "clean" crop with zero water, since CA LEAF sites near wetlands probably look like this too. Better to deal with it honestly than pretend it away.

The actual useful output today was figuring out what the discrepancy map is telling us. Wrote it down as a simple rule of thumb:
- High NDVI but low RGB = dry grass (the NIR signal sticks around even after it stops looking green)
- High RGB but low NDVI = probably still some misclassification, or small shrubs not filling a whole satellite cell
- Both high = real healthy vegetation
- Both low = bare ground, pavement, or water

That gives the discrepancy layer an actual explanation instead of just being "two numbers that don't match."

Also wrote the Tello mission script today even without the drone in hand. It flies a basic 4-point square and logs battery levels to a JSON file. Since the drone doesn't arrive until the 26th, built a fake MockTello class that pretends to connect, take off, fly, and land so I could test the whole script logic now. When the real drone shows up it should just be a one-flag change (--real) to switch from mock to live.
