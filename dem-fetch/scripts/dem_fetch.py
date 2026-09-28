"""Fetch DEM tiles around a lat/lon from AWS Terrain Tiles (Terrarium) and write ASC + CSV + preview PNG.

Usage:
  python dem_fetch.py --lat 39.9 --lon 116.4 --radius-km 5 --out out_dir
  python dem_fetch.py --lat 30.25 --lon 120.16 --radius-km 2 --zoom 12 --out out_dir
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
USER_AGENT = "dem-fetch/1.0 (https://github.com/IDKURLOVE/dem-fetch-skill)"


def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> tuple[float, float]:
    lat_rad = math.radians(lat_deg)
    n = 2.0**zoom
    x = (lon_deg + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def num2deg(x: float, y: float, zoom: int) -> tuple[float, float]:
    n = 2.0**zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    return math.degrees(lat_rad), lon_deg


def fetch_tile(z: int, x: int, y: int, cache_dir: Path) -> np.ndarray:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{z}_{x}_{y}.png"
    if cache_path.exists():
        img = Image.open(cache_path)
    else:
        url = TILE_URL.format(z=z, x=x, y=y)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        cache_path.write_bytes(data)
        img = Image.open(cache_path)
    rgb = np.asarray(img.convert("RGB"), dtype=np.int32)
    # Terrarium: elevation = (R*256 + G + B/256) - 32768
    elev = (rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256.0) - 32768.0
    return elev


def build_mosaic(
    lat: float, lon: float, radius_km: float, zoom: int, cache_dir: Path
) -> tuple[np.ndarray, dict]:
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
    dlat = radius_km * 1000.0 / m_per_deg_lat
    dlon = radius_km * 1000.0 / m_per_deg_lon

    north, south = lat + dlat, lat - dlat
    east, west = lon + dlon, lon - dlon

    x0f, y0f = deg2num(north, west, zoom)
    x1f, y1f = deg2num(south, east, zoom)

    x0, x1 = int(math.floor(x0f)), int(math.floor(x1f))
    y0, y1 = int(math.floor(y0f)), int(math.floor(y1f))

    tiles_x = x1 - x0 + 1
    tiles_y = y1 - y0 + 1
    print(f"zoom={zoom} tiles: x={x0}..{x1} ({tiles_x}), y={y0}..{y1} ({tiles_y})")

    mosaic = np.full((tiles_y * 256, tiles_x * 256), np.nan, dtype=np.float64)
    for iy, ty in enumerate(range(y0, y1 + 1)):
        for ix, tx in enumerate(range(x0, x1 + 1)):
            try:
                tile = fetch_tile(zoom, tx, ty, cache_dir)
            except Exception as exc:  # noqa: BLE001
                print(f"  tile {zoom}/{tx}/{ty} failed: {exc}", file=sys.stderr)
                tile = np.zeros((256, 256), dtype=np.float64)
            mosaic[iy * 256 : (iy + 1) * 256, ix * 256 : (ix + 1) * 256] = tile

    top_lat, left_lon = num2deg(x0, y0, zoom)
    _, left_lon_next = num2deg(x0 + 1, y0, zoom)
    top_lat_next, _ = num2deg(x0, y0 + 1, zoom)
    pixel_w = abs(left_lon_next - left_lon) / 256.0
    pixel_h = abs(top_lat - top_lat_next) / 256.0

    meta = {
        "north": top_lat,
        "west": left_lon,
        "pixel_w_deg": pixel_w,
        "pixel_h_deg": pixel_h,
        "width": mosaic.shape[1],
        "height": mosaic.shape[0],
        "zoom": zoom,
        "lat_center": lat,
        "lon_center": lon,
        "radius_km": radius_km,
    }
    return mosaic, meta


def write_asc(path: Path, dem: np.ndarray, meta: dict) -> None:
    # ESRI ASCII Grid, geographic CRS, cell size in degrees
    lines = [
        f"ncols {meta['width']}",
        f"nrows {meta['height']}",
        f"xllcorner {meta['west']:.10f}",
        f"yllcorner {meta['north'] - meta['height'] * meta['pixel_h_deg']:.10f}",
        f"cellsize {meta['pixel_w_deg']:.10f}",
        "NODATA_value -9999",
    ]
    data = np.where(np.isnan(dem), -9999.0, dem)
    fmt = np.vectorize(lambda v: f"{v:.2f}" if v != -9999.0 else "-9999")
    body = "\n".join(" ".join(row) for row in fmt(data))
    path.write_text("\n".join(lines) + "\n" + body + "\n", encoding="utf-8")


def write_csv(path: Path, dem: np.ndarray, meta: dict, step: int = 1) -> None:
    h, w = dem.shape
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["row", "col", "lat", "lon", "elev_m"])
        for r in range(0, h, step):
            for c in range(0, w, step):
                v = dem[r, c]
                if np.isnan(v):
                    continue
                lat = meta["north"] - (r + 0.5) * meta["pixel_h_deg"]
                lon = meta["west"] + (c + 0.5) * meta["pixel_w_deg"]
                writer.writerow([r, c, f"{lat:.6f}", f"{lon:.6f}", f"{v:.2f}"])


def write_preview_png(path: Path, dem: np.ndarray) -> None:
    valid = dem[~np.isnan(dem)]
    if valid.size == 0:
        return
    lo, hi = np.percentile(valid, [2, 98])
    if hi <= lo:
        hi = lo + 1.0
    norm = np.clip((dem - lo) / (hi - lo), 0, 1)
    norm = np.where(np.isnan(dem), 0.0, norm)
    img = (norm * 255).astype(np.uint8)
    Image.fromarray(img, mode="L").save(path)


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch DEM around a coordinate")
    p.add_argument("--lat", type=float, required=True, help="center latitude, WGS84")
    p.add_argument("--lon", type=float, required=True, help="center longitude, WGS84")
    p.add_argument("--radius-km", type=float, default=5.0, help="half-width of square extent")
    p.add_argument("--zoom", type=int, default=12, help="12≈30m/px, 13≈15m/px, 11≈60m/px")
    p.add_argument("--out", type=str, default="dem_out")
    p.add_argument("--csv-step", type=int, default=8, help="subsample CSV by this factor")
    args = p.parse_args()

    if not (-90.0 <= args.lat <= 90.0 and -180.0 <= args.lon <= 180.0):
        print("ERROR: lat/lon out of range", file=sys.stderr)
        return 2
    if args.radius_km <= 0:
        print("ERROR: radius-km must be positive", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "_tiles"

    print(f"center=({args.lat}, {args.lon}) radius={args.radius_km}km zoom={args.zoom}")
    dem, meta = build_mosaic(args.lat, args.lon, args.radius_km, args.zoom, cache)

    valid = dem[~np.isnan(dem)]
    if valid.size == 0:
        print("ERROR: no valid elevation samples", file=sys.stderr)
        return 1

    print(
        f"elev min={valid.min():.1f} max={valid.max():.1f} "
        f"mean={valid.mean():.1f} m  samples={valid.size}"
    )

    write_asc(out / "dem.asc", dem, meta)
    write_csv(out / "dem_samples.csv", dem, meta, step=max(1, args.csv_step))
    write_preview_png(out / "dem_preview.png", dem)

    print(f"wrote {out / 'dem.asc'}")
    print(f"wrote {out / 'dem_samples.csv'}")
    print(f"wrote {out / 'dem_preview.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
