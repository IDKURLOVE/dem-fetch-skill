# dem-fetch-skill

MiMo / Claude-style **skill** for fetching Digital Elevation Model (DEM) data around a latitude/longitude from free open sources (AWS Terrain Tiles, no API key).

**License: [MIT](LICENSE)**

## What it does

Input a WGS84 coordinate + radius → download Terrarium elevation tiles → decode → write:

| Output | Format | Use |
|---|---|---|
| `dem.asc` | ESRI ASCII Grid (EPSG:4326) | QGIS / ArcGIS / GDAL |
| `dem_samples.csv` | `lat,lon,elev_m` | pandas / Excel |
| `dem_preview.png` | 8-bit grayscale | quick look |

## Install (MiMo Desktop / Claude skills)

Copy the `dem-fetch/` folder into your skills directory:

```text
# global (all projects)
~/.config/mimocode/skills/dem-fetch/

# or project-level
<project>/.mimocode/skills/dem-fetch/
```

Then start a **new conversation** so the skill loads.

## CLI usage (no skill runtime required)

```bash
python dem-fetch/scripts/dem_fetch.py --lat 30.25 --lon 120.16 --radius-km 3 --zoom 12 --out dem_out
```

Requirements: Python 3.10+, `Pillow`, `numpy`, network access.

| Flag | Default | Meaning |
|---|---|---|
| `--lat` `--lon` | required | center, WGS84 decimal degrees |
| `--radius-km` | `5` | half-width of square extent |
| `--zoom` | `12` | 12≈30 m/px, 13≈15 m/px |
| `--out` | `dem_out` | output directory |
| `--csv-step` | `8` | CSV subsample factor |

## Example triggers (skill)

- 「输入经纬度找周围的 DEM」
- 「取这个站点附近的高程数据」
- "fetch DEM around this lat/lon"
- "elevation raster for my study area"

## Data attribution

Tiles from [AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) (Terrarium), derived from open global DEMs. Free to use; attribution appreciated.

## Repository layout

```text
LICENSE
README.md
dem-fetch/           <- install this folder as a skill
  SKILL.md
  scripts/dem_fetch.py
  references/data-sources.md
```

## License

MIT © 2026 IDKURLOVE
