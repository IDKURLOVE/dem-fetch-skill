# DEM data sources and formats

## Primary: AWS Terrain Tiles (used by this skill)

- Endpoint: `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`
- Encoding: **Terrarium**
  - `elevation = (R * 256 + G + B / 256) - 32768` (meters)
- Zoom levels (Web Mercator, approximate ground resolution at mid-latitudes):
  - z10 ≈ 120 m/px
  - z11 ≈ 60 m/px
  - z12 ≈ 30 m/px
  - z13 ≈ 15 m/px
- License: free to use; data derived from open global DEMs (SRTM, GMTED, NED, ETOPO1, …).
- Docs: https://registry.opendata.aws/terrain-tiles/

Tile count grows as 4× per zoom level. For a 5 km window at z12 expect 1–4 tiles; at z15 expect dozens.

## Alternative sources

| Source | Resolution | API key | Notes |
|---|---|---|---|
| AWS Terrain Tiles | 30 m global | No | Default for this skill |
| Copernicus DEM GLO-30 | 30 m global | Registration | Better water mask; GeoTIFF |
| NASADEM / SRTM 1-arc-sec | 30 m | Earthdata login | Classic research DEM |
| ALOS World 3D | 30 m / 5 m | Registration | AW3D30 / AW3D5 |
| OpenTopography | 1 m–30 m | API key | Airborne / lidar regional |
| USGS 3DEP | 1–10 m (US) | Free | US-only high res |

When the user needs sub-meter or national-coverage official DEMs, switch source and say so — AWS Terrarium is the fast default, not always the citation-grade product.

## Output formats produced

### `dem.asc` — ESRI ASCII Grid

Plain-text grid, opens in QGIS / ArcGIS / GDAL. Header fields:

```
ncols <width>
nrows <height>
xllcorner <west lon>
yllcorner <south lat>
cellsize <degrees>
NODATA_value -9999
```

CRS is **EPSG:4326** (geographic). Cell size is in **degrees**, not meters.

Convert to GeoTIFF if needed:

```bash
gdal_translate -of GTiff -a_srs EPSG:4326 dem.asc dem.tif
```

### `dem_samples.csv`

Columns: `row, col, lat, lon, elev_m`. Use `--csv-step` to subsample.

### `dem_preview.png`

8-bit grayscale hillshade-like stretch (2–98 percentile). For visualization only.

## Deriving slope / aspect (numpy)

With pixel size in meters (`ps = pixel_h_deg * 111320` approx):

```python
import numpy as np

# dem: 2D array, ps: pixel size in meters
gy, gx = np.gradient(dem, ps)
slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
aspect_deg = np.degrees(np.arctan2(-gy, gx)) % 360.0
```

For publication-quality slope/aspect use GDAL `gdaldem slope/aspect` on a projected CRS (UTM).

## Pitfalls

- **Web Mercator distortion**: high-latitude pixel size is not 30 m; check `cellsize` and reproject if area matters.
- **Ocean tiles**: Terrarium may encode ~0 or negative bathymetry-ish values; do not treat deep negatives as land DEM.
- **Cache**: tiles are cached under `out/_tiles/` — safe to delete to force re-download.
- **Rate limits**: AWS public bucket is generous but do not hammer z16+ over large areas; zoom down instead.
