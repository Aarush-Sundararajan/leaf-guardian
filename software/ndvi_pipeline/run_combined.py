import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sentinel_rgb import compute_sentinel_rgb
from sentinel_ndvi import compute_ndvi
from combine_maps import combine_health_maps

_BAND_DIR = 'data/sentinel_data/2022_aug'
_PREFIX   = 'T10SEG_20220812T184931'
_LAT, _LON, _HALF_M = 37.552707, -122.092559, 1000
GRID_SIZE = 9
LABEL     = '2022-Aug-CoyoteHills'

sat_rgb_scores = compute_sentinel_rgb(
    f'{_BAND_DIR}/{_PREFIX}_B04_10m.jp2',
    f'{_BAND_DIR}/{_PREFIX}_B03_10m.jp2',
    f'{_BAND_DIR}/{_PREFIX}_B02_10m.jp2',
    lat=_LAT, lon=_LON, half_m=_HALF_M,
    label=LABEL, grid_size=GRID_SIZE,
)

ndvi_scores = compute_ndvi(
    f'{_BAND_DIR}/{_PREFIX}_B04_10m.jp2',
    f'{_BAND_DIR}/{_PREFIX}_B08_10m.jp2',
    label=LABEL, grid_size=GRID_SIZE,
    lat=_LAT, lon=_LON, half_m=_HALF_M,
)

combine_health_maps(sat_rgb_scores, ndvi_scores, label=LABEL)
