# LEAF Guardian

Autonomous drone system for native plant health monitoring 
at ecological restoration sites.

## Problem
Manual plant survival monitoring doesn't scale. Restoration 
organizations managing dozens of sites have no practical way 
to track plant health continuously without costly, repeated 
field visits. Published research confirms 96% of restoration 
projects only monitor short-term changes.

## Approach
Combines autonomous navigation and camrea imaging for both RGB and NDVI color spectrums, providing accurate health analysis
by analyzing the seperate color channels and then merging the results and displaying the differnce between both

## Hardware
- DJI Tello — software development and indoor testing (arriving soon)
- DJI Mini 4K — outdoor field missions (Batch 2, late July)

## Data Sources
- Sentinel-2 L2A (Copernicus Data Space) — historical NDVI baseline
- CA Ecosystem Restoration Program ds209 — site locations
- Calscape — per-species health benchmarks

## Results So Far
- Sentinel-2 NDVI map generated for Coyote Hills Regional Park, Fremont CA
- August 2022 baseline: Mean NDVI = 0.123

## Software
- sentinel_ndvi.py — processes Sentinel-2 B04/B08 bands into color-coded NDVI maps

## Setup
1. Clone this repo
2. Install dependencies: py -m pip install numpy rasterio matplotlib
3. Download Sentinel-2 L2A scene from browser.dataspace.copernicus.eu
4. Place B04 and B08 .jp2 files in data/sentinel_data/[date]/
5. Run: py software/ndvi_pipeline/sentinel_ndvi.py

## Partner Organization
CA LEAF — California native plant restoration (outreach initiated June 2026)

## Competition Targets
- Regeneron STS — November 2026
- ISEF — Spring 2027
