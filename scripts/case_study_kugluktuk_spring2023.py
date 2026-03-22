"""
Case study: Kugluktuk area (Coronation Gulf), spring 2023.

Combines (1) ERA5-based daily climate at a community-centered point from
Open-Meteo archive with (2) Sentinel-2 surface change (NDSI / NDVI / NDWI) over
a coastal–tundra AOI where seasonal snow/ice melt affects travel conditions.

This is an assessment-style workflow for methods development, not a validated
community impact study. Interpret with local knowledge and appropriate data governance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.enums import Resampling

from src.climate_openmeteo import fetch_archive_daily, may_june_annual_stats
from src.indices import ndsi, ndvi, ndwi_mcfeeters
from src.raster_utils import stamp_geo_like
from src.stac_s2 import (
    aoi_bbox_from_geojson,
    load_s2_bands,
    pick_lowest_cloud,
    scl_is_clear,
    search_s2_items,
)

# Approximate hamlet centroid for climate time series (point-scale reanalysis).
KUGLUKTUK_LAT = 67.826
KUGLUKTUK_LON = -115.143

DEFAULT_AOI = ROOT / "data" / "aoi" / "kugluktuk_coronation_gulf.geojson"
OUT_DIR = ROOT / "outputs" / "case_study_kugluktuk_spring2023"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Kugluktuk spring 2023 climate + S2 case study")
    p.add_argument("--aoi", type=Path, default=DEFAULT_AOI)
    p.add_argument("--dry-run", action="store_true", help="Climate only; skip raster download")
    p.add_argument(
        "--pre-start",
        default="2023-05-01",
        help="Pre window (keep in May for snow-dominated surface where possible)",
    )
    p.add_argument("--pre-end", default="2023-05-31")
    p.add_argument(
        "--post-start",
        default="2023-06-10",
        help="Post window (peak melt season)",
    )
    p.add_argument("--post-end", default="2023-06-30")
    return p.parse_args()


def climate_panel(
    df: pd.DataFrame,
    baseline_years: tuple[int, int],
    out_path: Path,
) -> dict:
    stats = may_june_annual_stats(df)
    lo, hi = baseline_years
    baseline = [s for s in stats if lo <= s.year <= hi]
    t2023 = next((s for s in stats if s.year == 2023), None)
    if t2023 is None:
        raise SystemExit("No May–June 2023 rows in climate fetch.")

    temps = np.array([s.mean_temperature_c for s in baseline], dtype=float)
    mu, std = float(temps.mean()), float(temps.std(ddof=1))
    z = (t2023.mean_temperature_c - mu) / std if std > 1e-6 else float("nan")
    below = np.sum(temps < t2023.mean_temperature_c)
    pct = 100.0 * below / len(temps)

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), height_ratios=[1.1, 1.0])

    years = [s.year for s in baseline]
    axes[0].bar(years, [s.mean_temperature_c for s in baseline], color="#4a6fa5", alpha=0.85)
    axes[0].axhline(mu, color="gray", linestyle="--", linewidth=1, label=f"{lo}–{hi} mean")
    axes[0].axhline(
        t2023.mean_temperature_c,
        color="crimson",
        linewidth=2,
        label=f"2023 May–June mean ({t2023.mean_temperature_c:.2f} °C)",
    )
    axes[0].set_ylabel("Mean temperature (°C)")
    axes[0].set_title(
        f"May–June mean temperature at Kugluktuk point ({KUGLUKTUK_LAT}°N, {abs(KUGLUKTUK_LON)}°W)"
    )
    axes[0].legend(loc="upper left", fontsize=8)
    axes[0].grid(axis="y", alpha=0.3)

    sub = df.loc[df["time"].dt.year.eq(2023) & df["time"].dt.month.isin([5, 6])]
    axes[1].plot(sub["time"], sub["tmean"], color="crimson", label="2023 daily mean T")
    axes[1].set_ylabel("°C")
    axes[1].set_xlabel("Date")
    axes[1].set_title("Daily mean 2 m temperature (May–June 2023)")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    summary = {
        "climate_point_lat": KUGLUKTUK_LAT,
        "climate_point_lon": KUGLUKTUK_LON,
        "baseline_period_years": [lo, hi],
        "baseline_n_years": len(baseline),
        "baseline_mean_may_june_t_c": mu,
        "baseline_std_may_june_t_c": std,
        "year_2023_mean_may_june_t_c": t2023.mean_temperature_c,
        "year_2023_total_precip_mm_may_june": t2023.total_precipitation_mm,
        "year_2023_thaw_days_tmax_gt0_may_june": t2023.thaw_days_max_above_0,
        "z_score_2023_mean_t_vs_baseline": z,
        "percentile_warmer_than_baseline_years": pct,
    }
    return summary


def write_report(path: Path, climate: dict, rs_meta: dict) -> None:
    lines = [
        "# Case study: Kugluktuk area, spring 2023",
        "",
        "## Setting",
        "",
        "- **Area:** Coastal tundra / Coronation Gulf near Kugluktuk, Nunavut (see `data/aoi/kugluktuk_coronation_gulf.geojson`).",
        "- **Why this matters:** Earlier snowmelt and warmer springs alter surface conditions relevant to **overland travel** and access along **shore-fast / nearshore ice** (satellites do not map culturally defined trails).",
        "",
        "## Climate context (reanalysis / gridded archive)",
        "",
        f"- Point: {climate['climate_point_lat']}°N, {abs(climate['climate_point_lon'])}°W (Open-Meteo ERA5-based archive).",
        f"- Baseline: May–June mean temperature, **{climate['baseline_period_years'][0]}–{climate['baseline_period_years'][1]}**, *n* = {climate['baseline_n_years']} years.",
        f"- **2023 May–June mean 2 m temperature:** {climate['year_2023_mean_may_june_t_c']:.2f} °C (baseline mean {climate['baseline_mean_may_june_t_c']:.2f} °C, *z* ≈ {climate['z_score_2023_mean_t_vs_baseline']:.2f}).",
        f"- **Warmer than** ~{climate['percentile_warmer_than_baseline_years']:.0f}% of baseline May–June seasons by mean temperature.",
        f"- **2023 May–June total precipitation (grid cell):** {climate['year_2023_total_precip_mm_may_june']:.1f} mm.",
        f"- **Days with Tmax > 0 °C (May–June 2023):** {climate['year_2023_thaw_days_tmax_gt0_may_june']}.",
        "",
        "## Remote sensing",
        "",
        f"- **Pre scene:** `{rs_meta.get('pre_id', 'n/a')}` (cloud ~{float(rs_meta.get('pre_cloud') or 0):.2f}%).",
        f"- **Post scene:** `{rs_meta.get('post_id', 'n/a')}` (cloud ~{float(rs_meta.get('post_cloud') or 0):.2f}%).",
        "- **Indices:** ΔNDSI (snow/ice proxy), ΔNDVI, ΔNDWI; masked where SCL indicates cloud/shadow/cirrus in either date.",
        "- **Files:** GeoTIFFs and `rs_change_panel.png` in this output folder.",
        "",
        "## Caveats",
        "",
        "- Climate is **one grid point**, not a full trail network assessment.",
        "- Optical imagery is **weather-limited**; SCL masking removes clouds but not all errors.",
        "- Linking pixels to **hunting or travel impacts** requires community evidence and field context.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching climate (1991–2023 through June) …")
    df = fetch_archive_daily(KUGLUKTUK_LAT, KUGLUKTUK_LON, "1991-01-01", "2023-06-30")
    climate_summary = climate_panel(df, (1991, 2020), OUT_DIR / "climate_may_june_kugluktuk.png")
    (OUT_DIR / "climate_summary.json").write_text(
        json.dumps(climate_summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(climate_summary, indent=2))

    bbox = aoi_bbox_from_geojson(str(args.aoi))
    print(f"AOI bbox: {bbox}")

    pre_items = search_s2_items(bbox, args.pre_start, args.pre_end)
    post_items = search_s2_items(bbox, args.post_start, args.post_end)
    pre_item = pick_lowest_cloud(pre_items)
    post_item = pick_lowest_cloud(post_items)
    if pre_item is None or post_item is None:
        raise SystemExit("Insufficient Sentinel-2 coverage; widen date windows.")

    rs_meta = {
        "pre_id": pre_item.id,
        "pre_cloud": pre_item.properties.get("eo:cloud_cover"),
        "pre_datetime": str(pre_item.datetime),
        "post_id": post_item.id,
        "post_cloud": post_item.properties.get("eo:cloud_cover"),
        "post_datetime": str(post_item.datetime),
    }
    print(rs_meta)

    if args.dry_run:
        write_report(OUT_DIR / "REPORT.md", climate_summary, rs_meta)
        print(f"Dry run: wrote {OUT_DIR / 'REPORT.md'} (remote sensing figures skipped).")
        return

    bands = ["B03", "B04", "B08", "B11", "SCL"]
    pre = load_s2_bands(pre_item, bbox, bands)
    post = load_s2_bands(post_item, bbox, bands)

    g0 = pre["B03"]
    # B11 and SCL are 20 m native; align every band to the 10 m green grid.
    r0 = pre["B04"].rio.reproject_match(g0)
    n0 = pre["B08"].rio.reproject_match(g0)
    s0 = pre["B11"].rio.reproject_match(g0)
    scl0 = pre["SCL"].rio.reproject_match(g0, resampling=Resampling.nearest)
    r1 = post["B04"].rio.reproject_match(r0)
    n1 = post["B08"].rio.reproject_match(n0)
    g1 = post["B03"].rio.reproject_match(g0)
    s1 = post["B11"].rio.reproject_match(s0)
    scl1 = post["SCL"].rio.reproject_match(g0, resampling=Resampling.nearest)

    ndsi0 = ndsi(g0, s0)
    ndsi1 = ndsi(g1, s1)
    d_ndsi = ndsi1 - ndsi0

    ndvi0 = ndvi(n0, r0)
    ndvi1 = ndvi(n1, r1)
    d_ndvi = ndvi1 - ndvi0

    nw0 = ndwi_mcfeeters(g0, n0)
    nw1 = ndwi_mcfeeters(g1, n1)
    d_ndwi = nw1 - nw0

    c0 = scl_is_clear(scl0).astype("float32")
    c1 = scl_is_clear(scl1).astype("float32")
    valid = (c0 > 0.5) & (c1 > 0.5)

    d_ndsi_m = stamp_geo_like(g0, d_ndsi.where(valid))
    d_ndvi_m = stamp_geo_like(g0, d_ndvi.where(valid))
    d_ndwi_m = stamp_geo_like(g0, d_ndwi.where(valid))

    d_ndsi_m.rio.to_raster(OUT_DIR / "delta_ndsi_masked.tif")
    d_ndvi_m.rio.to_raster(OUT_DIR / "delta_ndvi_masked.tif")
    d_ndwi_m.rio.to_raster(OUT_DIR / "delta_ndwi_masked.tif")

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, da, title in zip(
        axes,
        (d_ndsi_m, d_ndvi_m, d_ndwi_m),
        ("Δ NDSI (post − pre)", "Δ NDVI (post − pre)", "Δ NDWI (post − pre)"),
        strict=True,
    ):
        arr = np.asarray(da.values, dtype=float)
        vmax = np.nanpercentile(np.abs(arr), 98)
        vmax = max(vmax, 1e-3)
        im = ax.imshow(arr, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.set_title(title)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Sentinel-2 change (SCL-masked): late spring melt window 2023", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "rs_change_panel.png", dpi=150)
    plt.close(fig)

    write_report(OUT_DIR / "REPORT.md", climate_summary, rs_meta)
    print(f"Wrote outputs under {OUT_DIR}")


if __name__ == "__main__":
    main()
