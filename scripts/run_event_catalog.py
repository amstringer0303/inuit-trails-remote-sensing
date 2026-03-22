"""
List documented events from data/events/event_catalog.json and optionally:
  - summarize July climate at the event point (Iqaluit example), or
  - run Sentinel-2 change detection when the catalog marks S2 as suitable.

This is the bridge between "research a past event" and "pull RS + climate data".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.climate_openmeteo import fetch_archive_daily


def load_catalog() -> dict:
    path = ROOT / "data" / "events" / "event_catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def july_2022_vs_baseline(lat: float, lon: float) -> None:
    print("Fetching daily archive (1991–2022, July only aggregation) …")
    df = fetch_archive_daily(lat, lon, "1991-01-01", "2022-07-31")
    df = df.copy()
    df = df.loc[df["time"].dt.month == 7]
    by_year = df.groupby(df["time"].dt.year)["tmean"].mean()
    baseline = by_year.loc[1991:2020]
    mu, sig = float(baseline.mean()), float(baseline.std(ddof=1))
    t22 = float(by_year.loc[2022])
    z = (t22 - mu) / sig if sig > 1e-6 else float("nan")
    print(f"  July mean 2 m temperature (point {lat:.4f}, {lon:.4f})")
    print(f"  1991–2020 July mean of monthly means: {mu:.3f} °C (std {sig:.3f})")
    print(f"  July 2022 mean: {t22:.3f} °C  (z vs baseline: {z:.2f})")
    print(
        "  Note: this is one reanalysis grid cell; July 2022 broke many records",
        "territory-wide (e.g. High Arctic stations) that may not appear at this point.",
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Event catalog → climate + optional S2")
    p.add_argument("--list", action="store_true", help="List event ids and titles")
    p.add_argument("--event", type=str, help="Event id from catalog")
    p.add_argument("--climate-only", action="store_true", help="Skip Sentinel-2 subprocess")
    p.add_argument("--dry-run", action="store_true", help="Pass through to S2 script")
    args = p.parse_args()

    cat = load_catalog()
    events = {e["id"]: e for e in cat["events"]}

    if args.list:
        for note in cat.get("notes", []):
            print(f"# {note}")
        print()
        for e in cat["events"]:
            s2 = e.get("sentinel2", {})
            ok = s2.get("recommended", False)
            print(f"{e['id']}: {e['title']}")
            print(f"  S2 suitable: {ok} — {s2.get('reason', '')}")
        return

    if not args.event:
        p.error("use --event ID or --list")

    ev = events.get(args.event)
    if ev is None:
        raise SystemExit(f"Unknown event {args.event!r}. Use --list.")

    print(f"=== {ev['title']} ===\n")
    for ref in ev.get("references", []):
        print(f"  ref: {ref}")
    print()

    pt = ev.get("climate_point")
    if pt and args.event == "iqaluit_july_2022_heat":
        july_2022_vs_baseline(pt["lat"], pt["lon"])
        print()

    if ev.get("run_command"):
        print(f"Run separately: {ev['run_command']}")
        return

    s2 = ev.get("sentinel2", {})
    if not s2.get("recommended"):
        print("Sentinel-2 not recommended for this event:")
        print(f"  {s2.get('reason', '')}")
        return

    if args.climate_only:
        print("--climate-only: not invoking S2 script.")
        return

    aoi_rel = ev.get("aoi_geojson")
    if not aoi_rel:
        raise SystemExit("Event has no aoi_geojson.")
    aoi = ROOT / aoi_rel
    if not aoi.is_file():
        raise SystemExit(f"Missing AOI file: {aoi}")

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "s2_change_detection.py"),
        "--aoi",
        str(aoi),
        "--pre-start",
        s2["pre_start"],
        "--pre-end",
        s2["pre_end"],
        "--post-start",
        s2["post_start"],
        "--post-end",
        s2["post_end"],
    ]
    if args.dry_run:
        cmd.append("--dry-run")

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(ROOT))


if __name__ == "__main__":
    main()
