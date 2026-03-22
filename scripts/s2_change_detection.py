"""
Sentinel-2 change experiment: NDVI / NDWI delta between two date windows.

Interpreting deltas as "trail impact" requires local knowledge and independent
event metadata; this script only demonstrates a reproducible RS workflow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import rioxarray  # noqa: F401
import xarray as xr

from src.indices import ndvi, ndwi_mcfeeters
from src.stac_s2 import (
    aoi_bbox_from_geojson,
    load_s2_band_pair,
    pick_lowest_cloud,
    search_s2_items,
)

DEFAULT_AOI = ROOT / "data" / "aoi" / "example_nunavut_bbox.geojson"
OUT_DIR = ROOT / "outputs"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="S2 NDVI/NDWI change between two periods")
    p.add_argument("--aoi", type=Path, default=DEFAULT_AOI, help="GeoJSON AOI path")
    p.add_argument("--pre-start", default="2023-06-01", help="Pre window start (ISO date)")
    p.add_argument("--pre-end", default="2023-06-15", help="Pre window end")
    p.add_argument("--post-start", default="2023-07-01", help="Post window start")
    p.add_argument("--post-end", default="2023-07-20", help="Post window end")
    p.add_argument("--dry-run", action="store_true", help="Only list STAC items; no download")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    bbox = aoi_bbox_from_geojson(str(args.aoi))
    print(f"AOI bbox (lon/lat): {bbox}")

    pre_items = search_s2_items(bbox, args.pre_start, args.pre_end)
    post_items = search_s2_items(bbox, args.post_start, args.post_end)
    print(f"Found {len(pre_items)} pre-window items, {len(post_items)} post-window items")

    pre_item = pick_lowest_cloud(pre_items)
    post_item = pick_lowest_cloud(post_items)
    if pre_item is None or post_item is None:
        raise SystemExit("Not enough scenes; widen date windows or AOI.")

    print(
        "Pre:",
        pre_item.id,
        "cloud_cover=",
        pre_item.properties.get("eo:cloud_cover"),
        pre_item.datetime,
    )
    print(
        "Post:",
        post_item.id,
        "cloud_cover=",
        post_item.properties.get("eo:cloud_cover"),
        post_item.datetime,
    )

    if args.dry_run:
        print("Dry run: skipping raster IO.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    r0, n0, g0 = load_s2_band_pair(pre_item, bbox)
    r1, n1, g1 = load_s2_band_pair(post_item, bbox)

    ndvi0 = ndvi(n0, r0)
    ndvi1 = ndvi(n1, r1)
    ndvi1m = ndvi1.rio.reproject_match(ndvi0)
    d_ndvi = ndvi1m - ndvi0

    nw0 = ndwi_mcfeeters(g0, n0)
    nw1 = ndwi_mcfeeters(g1, n1)
    nw1m = nw1.rio.reproject_match(nw0)
    d_ndwi = nw1m - nw0

    d_ndvi.rio.to_raster(OUT_DIR / "delta_ndvi.tif", driver="GTiff")
    d_ndwi.rio.to_raster(OUT_DIR / "delta_ndwi.tif", driver="GTiff")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, da, title in zip(
        axes,
        (d_ndvi, d_ndwi),
        ("Δ NDVI (post - pre)", "Δ NDWI (post - pre)"),
        strict=True,
    ):
        arr = np.asarray(da.values, dtype=float)
        vmax = np.nanpercentile(np.abs(arr), 98)
        vmax = max(vmax, 1e-3)
        im = ax.imshow(arr, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.set_title(title)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    plt.tight_layout()
    fig.savefig(OUT_DIR / "delta_indices.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT_DIR / 'delta_ndvi.tif'}, {OUT_DIR / 'delta_ndwi.tif'}, {OUT_DIR / 'delta_indices.png'}")


if __name__ == "__main__":
    main()
