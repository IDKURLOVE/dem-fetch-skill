---
name: dem-fetch
description: Fetch Digital Elevation Model (DEM) raster data around a latitude/longitude from free open sources (AWS Terrain Tiles / Terrarium, no API key). Use when the user mentions DEM, digital elevation model, 高程, 海拔, elevation data, terrain tiles, SRTM, "经纬度找DEM", "周围DEM", GeoTIFF/ASC elevation output, or wants slope/aspect from elevation. Produces ESRI ASCII Grid, CSV samples, and a preview PNG. Not for Blender terrain art, 3D modeling, or general GIS analysis beyond DEM extraction.
version: 1.0.0
license: MIT
compatibility: Requires network access and Python 3.10+ with Pillow and numpy. Windows/macOS/Linux.
metadata:
  author: IDKURLOVE
  category: geospatial
  tags: [dem, elevation, gis, terrain, geotiff, srtm, aws-terrain-tiles]
---

# dem-fetch

Fetch DEM raster tiles around a coordinate from AWS Terrain Tiles (Terrarium encoding), decode elevations, and write GIS-friendly outputs. No API key required.

## When to use

| User says | Action |
|---|---|
| "给我这个经纬度周围的 DEM" / "找附近高程数据" | Run `scripts/dem_fetch.py` with center + radius |
| "取某点海拔" | Run with `--radius-km 0.1` or read center pixel from CSV |
| "要 slope / aspect" | Fetch DEM first, then derive with numpy (see references) |
| Blender terrain / 3D landscape | **Do not use this skill** — route to environment-artist |

## Instructions

### Step 1: Confirm parameters

If not provided, ask (or use defaults and state them):

- `lat`, `lon` (required) — WGS84 decimal degrees
- `--radius-km` (default 5) — half-width of the square extent
- `--zoom` (default 12) — 12 ≈ 30 m/px, 13 ≈ 15 m/px, 11 ≈ 60 m/px
- `--out` — output directory

Zoom guidance: do **not** go above 13 unless the user needs sub-15 m; tile count grows 4× per zoom level.

### Step 2: Run the fetch script

```bash
python scripts/dem_fetch.py --lat 30.25 --lon 120.16 --radius-km 3 --zoom 12 --out dem_out
```

Expected console output:

```
center=(30.25, 120.16) radius=3.0km zoom=12
zoom=12 tiles: x=3414..3415 (2), y=1686..1686 (1)
elev min=... max=... mean=... m  samples=...
wrote dem_out/dem.asc
wrote dem_out/dem_samples.csv
wrote dem_out/dem_preview.png
```

### Step 3: Verify results

Check that:

1. `elev min/max` are plausible for the region (city ≈ 0–100 m, plateau 2000 m+, ocean tiles near 0 m).
2. `dem.asc` exists and is non-empty.
3. If min is around −39 m with large flat areas, the tile may include water/no-data artifacts — still usable, but flag it.

### Step 4: Interpret for the user

Report: output paths, elevation range, mean, pixel size, and how to open `dem.asc` (QGIS / ArcGIS / `numpy` + simple header parse).

If the user needs slope/aspect or a specific GeoTIFF CRS, read `references/data-sources.md`.

## Examples

**Example 1 — surrounding DEM for a station**

User: "杭州站点 30.25N 120.16E，取 3 km 范围 DEM"

→ `python scripts/dem_fetch.py --lat 30.25 --lon 120.16 --radius-km 3 --zoom 12 --out dem_out_hangzhou`

→ Report elev range and files.

**Example 2 — single-point elevation**

User: "39.9, 116.4 海拔多少？"

→ `python scripts/dem_fetch.py --lat 39.9 --lon 116.4 --radius-km 0.2 --zoom 12 --out dem_point`

→ Read center row from `dem_samples.csv` or report mosaic mean of the small window.

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `URLError` / timeout | No network or S3 blocked | Retry; check proxy; tiles are on `s3.amazonaws.com` |
| `tile ... failed: HTTP Error 404` | Ocean/empty tile at high zoom | Normal; script fills 0. Ignore or lower zoom |
| All elevations ≈ 0 | Coordinate is offshore | Confirm lat/lon; shift inland |
| `PIL` / `numpy` missing | Env incomplete | `pip install Pillow numpy` |
| File huge | zoom too high + large radius | Lower zoom to 11–12, or raise `--csv-step` |

## Data source attribution

Tiles: [AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) (Terrarium), sourced from open global DEMs (SRTM, GMTED, NED, etc.). Free for use; attribution appreciated. See `references/data-sources.md` for encoding, zoom, and alternative sources (OpenTopography, Copernicus).

## License

MIT — see `LICENSE` in the repository root.
