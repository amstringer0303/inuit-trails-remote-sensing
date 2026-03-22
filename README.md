# Inuit trails — remote sensing experiments

Exploratory code for linking **satellite observations** to **possible indicators** of extreme-weather stress on **subsistence travel corridors** (sea ice, coastal/marine, and inland). This repository is a methods sandbox, not a finished assessment product.

## Case study (climate + Sentinel-2)

**Kugluktuk area, Coronation Gulf, spring 2023** — coastal tundra where **snow/ice melt timing** affects **overland** and **nearshore** travel conditions.

1. **Climate:** [Open-Meteo archive](https://open-meteo.com/en/docs/historical-weather-api) (ERA5-based) at a point near Kugluktuk. May–June **2023** is compared to a **1991–2020** baseline (mean temperature, precipitation, thaw-day counts).
2. **Remote sensing:** Sentinel-2 L2A from [Planetary Computer](https://planetarycomputer.microsoft.com/): **May 4** vs **June 25, 2023** (low-cloud scenes). Computes **ΔNDSI** (snow/ice), **ΔNDVI**, **ΔNDWI** with **SCL** cloud/shadow masking. All bands are resampled to the 10 m grid before indices.

Run:

```bash
python scripts/case_study_kugluktuk_spring2023.py
python scripts/case_study_kugluktuk_spring2023.py --dry-run   # climate + STAC metadata only
```

Outputs (local only; not committed): `outputs/case_study_kugluktuk_spring2023/` — `climate_summary.json`, `climate_may_june_kugluktuk.png`, `delta_*.tif`, `rs_change_panel.png`, `REPORT.md`.

*Interpretation:* Warmer-than-baseline spring conditions and negative ΔNDSI (snow loss) are **physically plausible** in 2023, but this is **not** proof of impacts on specific hunting trails without local evidence and appropriate data governance.

## Past events → climate + remote sensing

**What is possible**

- **Research:** Use news, community reports, and literature to pin down **what happened**, **where**, and **when**.
- **Climate context:** Pull gridded daily series (e.g. Open-Meteo / ERA5) at a point or small region and compare to a baseline window.
- **Remote sensing:** For **sunlit**, **cloud-free** periods, compare Sentinel-2 scenes before/after to get **proxies** (snow/NDSI, wetness/NDWI, vegetation/NDVI) over a **hunting or travel region** (buffered AOI)—not individual trail lines.

**What is not possible (with this stack)**

- **Seeing trails** in multispectral imagery; **proving** impacts on subsistence without local knowledge.
- **Optical** analysis during **polar night** or **persistent cloud** (many winter storms): use **reanalysis/SAR**/microwave instead (Sentinel-1 not wired here yet).

**Catalog**

`data/events/event_catalog.json` lists example events with references. List them and run a scripted assessment:

```bash
python scripts/run_event_catalog.py --list
python scripts/run_event_catalog.py --event iqaluit_july_2022_heat --dry-run
python scripts/run_event_catalog.py --event iqaluit_july_2022_heat
```

Entries explicitly flag when **Sentinel-2 is inappropriate** (e.g. December storm) vs when a **summer** window is reasonable.

## What this repo tries to do

1. **Search** cloud-friendly Sentinel-2 (and optionally Sentinel-1) scenes via STAC.
2. **Compare** a pre-event and post-event window using simple spectral indices (e.g. NDVI, NDWI, NDSI) as *proxies* for conditions that might affect trails—not as ground truth.
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
