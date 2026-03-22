"""Keep CRS/transform attached through xarray math."""

from __future__ import annotations

import rioxarray  # noqa: F401 — .rio accessor
import xarray as xr


def stamp_geo_like(ref: xr.DataArray, data: xr.DataArray) -> xr.DataArray:
    """Copy y/x coords and georeferencing from ref (e.g. a raw S2 band) onto derived arrays."""
    out = data.copy()
    if "y" in ref.coords and "x" in ref.coords:
        out = out.assign_coords(y=ref["y"], x=ref["x"])
    return out.rio.write_crs(ref.rio.crs).rio.write_transform(ref.rio.transform(recalc=True))
