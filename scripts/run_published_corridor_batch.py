"""
Run s2_change_detection.py for each AOI listed in data/published_corridors/corridor_metadata.json.

Produces per-corridor folders under outputs/published_corridors/<id>/ with delta_ndvi.tif,
delta_ndwi.tif, and delta_indices.png.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description="Batch S2 change for published corridor AOIs")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated corridor ids (default: all in metadata)",
    )
    args = p.parse_args()

    meta_path = ROOT / "data" / "published_corridors" / "corridor_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    w = meta["default_s2_windows"]

    only = {x.strip() for x in args.only.split(",")} if args.only else None

    for c in meta["corridors"]:
        cid = c["id"]
        if only is not None and cid not in only:
            continue
        aoi = ROOT / c["geojson"]
        if not aoi.is_file():
            print(f"Skip {cid}: missing {aoi}")
            continue
        out = ROOT / "outputs" / "published_corridors" / cid
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
        print("===", cid, "===", flush=True)
        subprocess.run(cmd, check=True, cwd=str(ROOT))


if __name__ == "__main__":
    main()
