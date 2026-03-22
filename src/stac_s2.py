"""Sentinel-2 L2A via Microsoft Planetary Computer STAC."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import geopandas as gpd
import planetary_computer
import pystac_client
import rioxarray  # noqa: F401 — registers .rio accessor
import xarray as xr
from pystac import Item

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
S2_COLLECTION = "sentinel-2-l2a"


@dataclass
class S2Window:
    """One cloud-filtered S2 acquisition over an AOI."""

    item: Item
    cloud_cover: float


def aoi_bbox_from_geojson(path: str) -> tuple[float, float, float, float]:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    else:
        gdf = gdf.to_crs(4326)
    minx, miny, maxx, maxy = gdf.total_bounds
    return float(minx), float(miny), float(maxx), float(maxy)


def search_s2_items(
    bbox: tuple[float, float, float, float],
    start: str,
    end: str,
    max_items: int = 50,
) -> list[Item]:
    catalog = pystac_client.Client.open(STAC_URL)
    search = catalog.search(
        collections=[S2_COLLECTION],
        bbox=list(bbox),
        datetime=f"{start}/{end}",
        max_items=max_items,
        query={"eo:cloud_cover": {"lt": 60}},
    )
    return list(search.items())


def pick_lowest_cloud(items: Iterable[Item]) -> Item | None:
    best: Item | None = None
    best_cc: float = 1e9
    for it in items:
        cc = float(it.properties.get("eo:cloud_cover", 999))
        if cc < best_cc:
            best_cc = cc
            best = it
    return best


def _open_band(item: Item, band: str, bbox_4326: tuple[float, float, float, float]) -> xr.DataArray:
    asset = item.assets.get(band)
    if asset is None:
        raise KeyError(f"Band {band} not found on item {item.id}")
    url = planetary_computer.sign(asset.href)
    da = xr.open_dataarray(url, engine="rasterio").squeeze(drop=True)
    if da.rio.crs is None:
        da = da.rio.write_crs("EPSG:4326")
    minx, miny, maxx, maxy = bbox_4326
    return da.rio.clip_box(
        minx=minx, miny=miny, maxx=maxx, maxy=maxy, crs="EPSG:4326"
    )


def load_s2_band_pair(
    item: Item,
    bbox_4326: tuple[float, float, float, float],
    red_band: str = "B04",
    nir_band: str = "B08",
    green_band: str = "B03",
) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    red = _open_band(item, red_band, bbox_4326)
    nir = _open_band(item, nir_band, bbox_4326)
    green = _open_band(item, green_band, bbox_4326)
    return red, nir, green
