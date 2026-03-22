"""Spectral indices as coarse surface-condition proxies."""

from __future__ import annotations

import numpy as np
import xarray as xr


def ndvi(nir: xr.DataArray, red: xr.DataArray) -> xr.DataArray:
    """Normalized difference vegetation index (NIR = B08, Red = B04 for Sentinel-2)."""
    num = nir.astype("float32") - red.astype("float32")
    den = nir.astype("float32") + red.astype("float32")
    out = xr.where(den != 0, num / den, np.nan)
    return out.assign_attrs(long_name="NDVI", grid_mapping=nir.attrs.get("grid_mapping"))


def ndsi(green: xr.DataArray, swir11: xr.DataArray) -> xr.DataArray:
    """Normalized difference snow index (Green = B03, SWIR = B11 for Sentinel-2)."""
    g = green.astype("float32")
    s = swir11.astype("float32")
    den = g + s
    out = xr.where(den != 0, (g - s) / den, np.nan)
    return out.assign_attrs(long_name="NDSI", grid_mapping=green.attrs.get("grid_mapping"))


def ndwi_mcfeeters(green: xr.DataArray, nir: xr.DataArray) -> xr.DataArray:
    """NDWI (McFeeters): water / wetness sensitivity using green and NIR."""
    g = green.astype("float32")
    n = nir.astype("float32")
    den = g + n
    out = xr.where(den != 0, (g - n) / den, np.nan)
    return out.assign_attrs(long_name="NDWI_McFeeters", grid_mapping=green.attrs.get("grid_mapping"))
