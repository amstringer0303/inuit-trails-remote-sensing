"""Sentinel-1 GRD (VV) via Microsoft Planetary Computer STAC."""

from __future__ import annotations

import numpy as np
import planetary_computer
from shapely.geometry import box
import pystac_client
import rioxarray  # noqa: F401
import xarray as xr
from pystac import Item

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
S1_COLLECTION = "sentinel-1-grd"


def search_s1_grd_items(
    bbox: tuple[float, float, float, float],
    start: str,
    end: str,
    max_items: int = 100,
) -> list[Item]:
    catalog = pystac_client.Client.open(STAC_URL)
    search = catalog.search(
        collections=[S1_COLLECTION],
        bbox=list(bbox),
        datetime=f"{start}/{end}",
        max_items=max_items,
    )
    return list(search.items())


def pick_s1_pre_post(
    pre_items: list[Item],
    post_items: list[Item],
) -> tuple[Item | None, Item | None]:
    """Latest pre-flood acquisition; earliest post-flood with matching relative orbit if possible."""
    if not pre_items or not post_items:
        return None, None
    pre = sorted(pre_items, key=lambda x: x.datetime)[-1]
    ro = pre.properties.get("sat:relative_orbit")
    post_orbit = [i for i in post_items if i.properties.get("sat:relative_orbit") == ro]
    pool = post_orbit if post_orbit else post_items
    post = sorted(pool, key=lambda x: x.datetime)[0]
    return pre, post


def load_s1_vv(item: Item, bbox_4326: tuple[float, float, float, float]) -> xr.DataArray:
    asset = item.assets.get("vv")
    if asset is None:
        raise KeyError(f"No vv asset on {item.id}")
    url = planetary_computer.sign(asset.href)
    da = xr.open_dataarray(url, engine="rasterio").squeeze(drop=True)
    minx, miny, maxx, maxy = bbox_4326
    aoi = box(minx, miny, maxx, maxy)
    # Polygon clip in WGS84 is reliable across S1 GRD projected CRSs
    return da.rio.clip([aoi], crs="EPSG:4326", drop=False)


def vv_to_db(vv: xr.DataArray) -> xr.DataArray:
    """GRD linear power/intensity to dB (approximate)."""
    v = vv.astype("float32").clip(min=1e-8, max=1e6)
    db = 10.0 * np.log10(v)
    return db.assign_attrs(long_name="VV_dB", units="dB")
