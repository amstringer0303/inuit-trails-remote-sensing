# Inuit trails — remote sensing experiments

Exploratory code for linking **satellite observations** to **possible indicators** of extreme-weather stress on **subsistence travel corridors** (sea ice, coastal/marine, and inland). This repository is a methods sandbox, not a finished assessment product.

## What this repo tries to do

1. **Search** cloud-friendly Sentinel-2 (and optionally Sentinel-1) scenes via STAC.
2. **Compare** a pre-event and post-event window using simple spectral indices (e.g. NDVI, NDWI) as *proxies* for conditions that might affect trails—not as ground truth.
3. **Buffer** vector trail segments (when you add them) to summarize zonal statistics.

**Important limitations**

- Satellite data cannot “see” cultural travel routes directly; it can only hint at surface conditions (snow/ice/water/vegetation/wetness) that may co-occur with trail usability.
- Extreme events must be defined with dates and locations you supply (community consultation, weather logs, news, or reanalysis).
- Respect **Indigenous data sovereignty** and any agreements governing trail spatial data. Do not publish sensitive locations without explicit permission.

## Quick start

```bash
cd inuit-trails-remote-sensing
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Dry run (no download—lists STAC items only):

```bash
python scripts/s2_change_detection.py --dry-run
```

Full run for the default example AOI and dates (downloads a small raster window; needs network):

```bash
python scripts/s2_change_detection.py
```

Outputs are written to `outputs/`.

## Repository layout

| Path | Purpose |
|------|--------|
| `data/aoi/` | Example area-of-interest GeoJSON (replace with your study region). |
| `data/trails/` | Place optional trail GeoJSON/GeoPackage files (gitignored if sensitive). |
| `src/` | Small Python modules (indices, buffering, STAC helpers). |
| `scripts/` | Runnable experiments. |

## Data sources

- [Microsoft Planetary Computer STAC API](https://planetarycomputer.microsoft.com/) — Sentinel-2 L2A, Sentinel-1 GRD, and more.
- For sea-ice–specific products, consider adding AMSR2/NSIDC or Copernicus Marine layers in a follow-up script (not included yet).

## Push to GitHub

After fixing GitHub CLI auth (`gh auth login -h github.com`):

```bash
gh repo create inuit-trails-remote-sensing --public --source=. --remote=origin --push
```

Or create an empty repo in the browser, then:

```bash
git remote add origin https://github.com/YOUR_USER/inuit-trails-remote-sensing.git
git push -u origin main
```

## License

Add a `LICENSE` file that matches your institution’s requirements. Default assumption: research code; trail geometries may need a separate data agreement.
