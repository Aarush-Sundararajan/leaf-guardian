# Development Log

## June 9, 2026
- Created GitHub repo leaf-guardian with initial folder structure
- Installed djitellopy, opencv-python, numpy, matplotlib via py -m pip
- Sent CA LEAF outreach email requesting domain expertise on plant stress indicators
- Ordered Tello Boost Combo (arrival TBD)
- Added .gitignore for large data files

## June 10, 2026
- Created Copernicus Data Space account
- Located Coyote Hills Regional Park (37.5579, -122.0656) as placeholder CA LEAF site
- Downloaded Sentinel-2 L2A scene for Coyote Hills Aug 12 2022
- Built sentinel_ndvi.py — reads B04 and B08 bands, computes NDVI, outputs color-coded PNG
- Generated first NDVI map: Mean NDVI = 0.123 for Coyote Hills Aug 2022
- Raw .jp2 files excluded from repo via .gitignore — only processed outputs committed
