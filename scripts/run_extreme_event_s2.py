"""
For an entry in data/published_corridors/extreme_event_profiles.json with
sentinel2_recommended=true, run s2_change_detection.py for each related AOI.

Outputs: outputs/extreme_events/<event_id>/<corridor_id>/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def corridor_path_by_id(meta: dict, cid: str) -> Path | None:
    for c in meta["corridors"]:
        if c["id"] == cid:
            p = ROOT / c["geojson"]
            return p if p.is_file() else None
    return None


def main() -> None:
    p = argparse.ArgumentParser(description="S2 change for extreme-event AOIs")
    p.add_argument("--event", required=True, help="Event id from extreme_event_profiles.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    ev_path = ROOT / "data" / "published_corridors" / "extreme_event_profiles.json"
    meta_path = ROOT / "data" / "published_corridors" / "corridor_metadata.json"
    ev_doc = json.loads(ev_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    event = next((e for e in ev_doc["events"] if e["id"] == args.event), None)
    if event is None:
        raise SystemExit(f"Unknown event {args.event!r}. Keys: {[e['id'] for e in ev_doc['events']]}")

    if not event.get("sentinel2_recommended"):
        print(f"Event {args.event}: Sentinel-2 not recommended.")
        print(event.get("interpretation_note", ""))
        return

    w = event["s2_windows"]
    for cid in event["related_corridor_ids"]:
        aoi = corridor_path_by_id(meta, cid)
        if aoi is None:
            print(f"Skip {cid}: AOI file missing or unknown id")
            continue
        out = ROOT / "outputs" / "extreme_events" / args.event / cid
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "s2_change_detection.py"),
            "--aoi",
            str(aoi),
            "--out-dir",
            str(out),
            "--pre-start",
            w["pre_start"],
            "--pre-end",
            w["pre_end"],
            "--post-start",
            w["post_start"],
            "--post-end",
            w["post_end"],
        ]
        if args.dry_run:
            cmd.append("--dry-run")
        print("===", args.event, "/", cid, "===", flush=True)
        subprocess.run(cmd, check=True, cwd=str(ROOT))


if __name__ == "__main__":
    main()
