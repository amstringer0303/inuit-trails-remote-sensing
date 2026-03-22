# Case study: Kugluktuk area, spring 2023

## Setting

- **Area:** Coastal tundra / Coronation Gulf near Kugluktuk, Nunavut (see `data/aoi/kugluktuk_coronation_gulf.geojson`).
- **Why this matters:** Earlier snowmelt and warmer springs alter surface conditions relevant to **overland travel** and access along **shore-fast / nearshore ice** (satellites do not map culturally defined trails).

## Climate context (reanalysis / gridded archive)

- Point: 67.826°N, 115.143°W (Open-Meteo ERA5-based archive).
- Baseline: May–June mean temperature, **1991–2020**, *n* = 30 years.
- **2023 May–June mean 2 m temperature:** 5.44 °C (baseline mean 1.58 °C, *z* ≈ 2.87).
- **Warmer than** ~100% of baseline May–June seasons by mean temperature.
- **2023 May–June total precipitation (grid cell):** 51.9 mm.
- **Days with Tmax > 0 °C (May–June 2023):** 58.

## Remote sensing

- **Pre scene:** `S2A_MSIL2A_20230504T193901_R042_T11WNR_20230505T025941` (cloud ~0.16%).
- **Post scene:** `S2B_MSIL2A_20230625T192909_R142_T11WNR_20240926T075624` (cloud ~0.00%).
- **Indices:** ΔNDSI (snow/ice proxy), ΔNDVI, ΔNDWI; masked where SCL indicates cloud/shadow/cirrus in either date.
- **Files:** GeoTIFFs and `rs_change_panel.png` in this output folder.

## Caveats

- Climate is **one grid point**, not a full trail network assessment.
- Optical imagery is **weather-limited**; SCL masking removes clouds but not all errors.
- Linking pixels to **hunting or travel impacts** requires community evidence and field context.
