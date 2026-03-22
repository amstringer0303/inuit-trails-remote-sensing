"""Fetch gridded reanalysis-style daily climate from Open-Meteo (ERA5-based archive)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


@dataclass
class MayJuneClimateSummary:
    """Aggregates for May–June at a point, one calendar year."""

    year: int
    mean_temperature_c: float
    total_precipitation_mm: float
    thaw_days_max_above_0: int


def fetch_archive_daily(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": [
            "temperature_2m_mean",
            "temperature_2m_max",
            "precipitation_sum",
        ],
    }
    # Open-Meteo expects comma-separated daily vars
    flat = {
        "latitude": params["latitude"],
        "longitude": params["longitude"],
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(params["daily"]),
    }
    url = f"{ARCHIVE_URL}?{urlencode(flat)}"
    with urlopen(url, timeout=120) as resp:
        payload = json.loads(resp.read().decode())

    if "daily" not in payload:
        raise RuntimeError(f"Unexpected API response: {payload.keys()}")

    d = payload["daily"]
    return pd.DataFrame(
        {
            "time": pd.to_datetime(d["time"]),
            "tmean": d["temperature_2m_mean"],
            "tmax": d["temperature_2m_max"],
            "precip": d["precipitation_sum"],
        }
    )


def may_june_annual_stats(df: pd.DataFrame) -> list[MayJuneClimateSummary]:
    """Split daily rows into May–June seasons per year."""
    m = df["time"].dt.month
    sub = df.loc[m.isin([5, 6])].copy()
    sub["year"] = sub["time"].dt.year
    out: list[MayJuneClimateSummary] = []
    for year, g in sub.groupby("year"):
        tmean = float(g["tmean"].mean())
        precip = float(g["precip"].sum())
        thaw = int((g["tmax"] > 0.0).sum())
        out.append(
            MayJuneClimateSummary(
                year=int(year),
                mean_temperature_c=tmean,
                total_precipitation_mm=precip,
                thaw_days_max_above_0=thaw,
            )
        )
    return sorted(out, key=lambda s: s.year)


def rank_year_vs_history(
    history: list[MayJuneClimateSummary],
    target_year: int,
) -> dict[str, Any]:
    """Percentile rank of target year in historical list (by mean May–June temperature)."""
    hist_years = [s for s in history if s.year != target_year]
    if not hist_years:
        raise ValueError("Need historical years")

    temps = sorted(s.mean_temperature_c for s in hist_years)
    target = next(s for s in history if s.year == target_year)

    # percentile rank: fraction of history strictly below target
    below = sum(1 for t in temps if t < target.mean_temperature_c)
    pct = 100.0 * below / len(temps)

    mu = float(sum(temps) / len(temps))
    var = float(sum((t - mu) ** 2 for t in temps) / max(len(temps) - 1, 1))
    std = var**0.5
    z = (target.mean_temperature_c - mu) / std if std > 1e-6 else float("nan")

    return {
        "target_year": target_year,
        "target_mean_t_c_may_june": target.mean_temperature_c,
        "target_precip_mm_may_june": target.total_precipitation_mm,
        "target_thaw_days_tmax_gt0": target.thaw_days_max_above_0,
        "baseline_years": len(temps),
        "baseline_mean_t_c": mu,
        "baseline_std_t_c": std,
        "percentile_rank_warmer_than_history": pct,
        "z_score_mean_t_vs_baseline": z,
    }
