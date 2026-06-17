import rasterio
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window


def crop_band(path, lat, lon, half_m=1000):
    """Windowed-read a single-band raster cropped to a square centred on (lat, lon).

    half_m: half the side length in metres (1000 → 2 km × 2 km crop).
    Returns a float64 array with DN scaled to surface reflectance (DN / 10000).
    """
    with rasterio.open(path) as f:
        xs, ys = warp_transform('EPSG:4326', f.crs, [lon], [lat])
        cx, cy = xs[0], ys[0]
        t = f.transform
        px_x, px_y = t.a, abs(t.e)

        col_center = (cx - t.c) / px_x
        row_center = (t.f - cy) / px_y

        half_cols = int(half_m / px_x)
        half_rows = int(half_m / px_y)

        col_off = max(0, int(col_center - half_cols))
        row_off = max(0, int(row_center - half_rows))
        width  = min(2 * half_cols, f.width  - col_off)
        height = min(2 * half_rows, f.height - row_off)

        return f.read(1, window=Window(col_off, row_off, width, height)).astype(float) / 10000.0
