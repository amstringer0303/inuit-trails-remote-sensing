"""
Hay River (NWT) May 2022 river / ice-jam flooding — optical MNDWI + Sentinel-1 VV.

Pre-flood: before 2022-05-10 evacuation.
Post-flood: during peak surge window (SAR) and after drawdown (optical where clear).

See data/aoi/hay_river_floodplain_2022.geojson for citations.
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
from rasterio.enums import Resampling

from src.indices import mndwi_xu2006
from src.raster_utils import stamp_geo_like
from src.stac_s1 import load_s1_vv, pick_s1_pre_post, search_s1_grd_items, vv_to_db
from src.stac_s2 import (
    aoi_bbox_from_geojson,
    load_s2_bands,
    pick_lowest_cloud,
    scl_is_clear,
    search_s2_items,
)

DEFAULT_AOI = ROOT / "data" / "aoi" / "hay_river_floodplain_2022.geojson"
OUT = ROOT / "outputs" / "case_study_hay_river_flood_2022"


def _plot_array(arr: np.ndarray, max_side: int = 1800) -> np.ndarray:
    """Stride subsample so matplotlib does not allocate gigabytes on full S1/S2 grids."""
    a = np.squeeze(np.asarray(arr, dtype=float))
    if a.ndim != 2:
        return a
    h, w = a.shape
    step = max(1, max(h, w) // max_side)
    return a[::step, ::step]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hay River 2022 flood: MNDWI + S1 VV")
    p.add_argument("--aoi", type=Path, default=DEFAULT_AOI)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--s1-pre-start",
        default="2022-04-25",
        help="S1 pre window (before evacuation; widen if orbit gap)",
    )
    p.add_argument("--s1-pre-end", default="2022-05-09")
    p.add_argument(
        "--s1-post-start",
        default="2022-05-12",
        help="S1 post window (surge period)",
    )
    p.add_argument("--s1-post-end", default="2022-05-16")
    p.add_argument(
        "--s2-pre-start",
        default="2022-05-01",
        help="S2 pre (spring, some cloud risk)",
    )
    p.add_argument("--s2-pre-end", default="2022-05-09")
    p.add_argument(
        "--s2-post-start",
        default="2022-05-20",
        help="S2 post after peak when skies often clearer",
    )
    p.add_argument("--s2-post-end", default="2022-06-05")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    bbox = aoi_bbox_from_geojson(str(args.aoi))
    print(f"AOI bbox: {bbox}")

    s1_pre = search_s1_grd_items(bbox, args.s1_pre_start, args.s1_pre_end)
    s1_post = search_s1_grd_items(bbox, args.s1_post_start, args.s1_post_end)
    pre1, post1 = pick_s1_pre_post(s1_pre, s1_post)
    print(f"S1 pre candidates: {len(s1_pre)}, post: {len(s1_post)}")
    if pre1 and post1:
        print("S1 pre:", pre1.id, pre1.datetime, "orbit", pre1.properties.get("sat:relative_orbit"))
        print("S1 post:", post1.id, post1.datetime, "orbit", post1.properties.get("sat:relative_orbit"))

    s2_pre_i = pick_lowest_cloud(search_s2_items(bbox, args.s2_pre_start, args.s2_pre_end))
    s2_post_i = pick_lowest_cloud(search_s2_items(bbox, args.s2_post_start, args.s2_post_end))
    if s2_pre_i:
        print("S2 pre:", s2_pre_i.id, s2_pre_i.properties.get("eo:cloud_cover"), s2_pre_i.datetime)
    if s2_post_i:
        print("S2 post:", s2_post_i.id, s2_post_i.properties.get("eo:cloud_cover"), s2_post_i.datetime)

    if args.dry_run:
        return

    if pre1 is None or post1 is None:
        raise SystemExit("Missing Sentinel-1 GRD for one of the windows; widen dates.")

    OUT.mkdir(parents=True, exist_ok=True)

    vv0 = load_s1_vv(pre1, bbox)
    vv1 = load_s1_vv(post1, bbox)
    vv1m = vv1.rio.reproject_match(vv0, resampling=Resampling.bilinear)
    dvv_db = vv_to_db(vv1m) - vv_to_db(vv0)
    dvv_db.rio.to_raster(OUT / "s1_delta_vv_dB.tif")

    if s2_pre_i is None or s2_post_i is None:
        print("Warning: skipping S2 MNDWI — insufficient clear scenes in windows.")
        fig, ax = plt.subplots(1, 1, figsize=(6, 5))
        arr = _plot_array(dvv_db.values)
        v = np.nanpercentile(np.abs(arr), 98)
        v = max(v, 0.5)
        im = ax.imshow(arr, cmap="RdBu_r", vmin=-v, vmax=v)
        ax.set_title("Δ VV backscatter (dB, post − pre)\nSentinel-1 GRD — Hay River May 2022")
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        plt.tight_layout()
        fig.savefig(OUT / "flood_proxy_panel_s1_only.png", dpi=150)
        plt.close(fig)
        print(f"Wrote {OUT / 's1_delta_vv_dB.tif'} and S1-only figure.")
        return

    g0 = load_s2_bands(s2_pre_i, bbox, ["B03"])["B03"]
    s0 = load_s2_bands(s2_pre_i, bbox, ["B11"])["B11"].rio.reproject_match(g0)
    scl0 = load_s2_bands(s2_pre_i, bbox, ["SCL"])["SCL"].rio.reproject_match(g0, resampling=Resampling.nearest)

    g1 = load_s2_bands(s2_post_i, bbox, ["B03"])["B03"].rio.reproject_match(g0)
    s1b = load_s2_bands(s2_post_i, bbox, ["B11"])["B11"].rio.reproject_match(g0)
    scl1 = load_s2_bands(s2_post_i, bbox, ["SCL"])["SCL"].rio.reproject_match(g0, resampling=Resampling.nearest)

    m0 = mndwi_xu2006(g0, s0)
    m1 = mndwi_xu2006(g1, s1b)
    dm = m1 - m0
    valid = (scl_is_clear(scl0).astype("float32") > 0.5) & (scl_is_clear(scl1).astype("float32") > 0.5)
    dm_m = stamp_geo_like(g0, dm.where(valid))
    dm_m.rio.to_raster(OUT / "s2_delta_mndwi_masked.tif")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    arr_m = _plot_array(dm_m.values)
    vm = float(np.nanpercentile(np.abs(arr_m), 98)) if np.any(np.isfinite(arr_m)) else 0.1
    vm = max(vm, 0.05)
    im0 = axes[0].imshow(arr_m, cmap="RdBu_r", vmin=-vm, vmax=vm)
    axes[0].set_title("Δ MNDWI (Xu 2006)\nSentinel-2, SCL-masked")
    axes[0].axis("off")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    arr_v = _plot_array(dvv_db.values)
    vv_lim = float(np.nanpercentile(np.abs(arr_v), 98)) if np.any(np.isfinite(arr_v)) else 1.0
    vv_lim = max(vv_lim, 0.5)
    im1 = axes[1].imshow(arr_v, cmap="RdBu_r", vmin=-vv_lim, vmax=vv_lim)
    axes[1].set_title("Δ VV (dB)\nSentinel-1 GRD")
    axes[1].axis("off")
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    fig.suptitle("Hay River floodplain proxies — May 2022 (see GeoJSON for event refs)", fontsize=11)
    plt.tight_layout()
    fig.savefig(OUT / "flood_proxy_panel_mndwi_and_sar.png", dpi=150)
    plt.close(fig)

    report = OUT / "REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# Hay River (NWT) May 2022 — MNDWI + SAR case study",
                "",
                "## Event (desk references)",
                "",
                "- Public reporting of evacuation and ice-jam / surge impacts in **early–mid May 2022** (see `hay_river_floodplain_2022.geojson` for URLs).",
                "",
                "## Outputs",
                "",
                "| File | Content |",
                "|------|---------|",
                "| `s1_delta_vv_dB.tif` | **Post − pre** VV backscatter in **dB** (same relative orbit when possible). Flooded open water often appears as **lower** VV vs dry land, but ice, wind roughening, and urban structures break simple rules. |",
                "| `s2_delta_mndwi_masked.tif` | **Post − pre** **MNDWI** (Xu 2006, B03/B11), masked with **SCL** (cloud/shadow). **Higher** MNDWI can indicate more open water / wetness—**not** depth. |",
                "| `flood_proxy_panel_mndwi_and_sar.png` | Side-by-side quick look. |",
                "",
                "## Interpretation",
                "",
                "- **Use SAR where optical is cloudy** (common during break-up).",
                "- **Do not** equate pixels with inundation depth or trail closure.",
                "- Validate with **air photos, news, hydrology gauges**, or **local knowledge** where possible.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Wrote outputs under {OUT}")


if __name__ == "__main__":
    main()
