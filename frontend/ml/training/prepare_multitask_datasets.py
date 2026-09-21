"""Prepare a reproducible multi-dataset workspace for Urban Intelligence AI.

This script intentionally does not scrape arbitrary web images. It records approved
sources, verifies manually downloaded archives, and creates the normalized workspace
used by the road/infrastructure/traffic/ANPR training jobs.

Large or click-through licensed datasets are kept out of git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[3]
ML_ROOT = SCRIPT.parents[1]
DATASETS = ML_ROOT / "datasets"
RAW = DATASETS / "_raw"
MANIFEST = DATASETS / "dataset_sources.json"

SOURCES = {
    "rdd2022": {
        "tasks": ["pothole", "longitudinal_crack", "transverse_crack", "alligator_crack", "road_damage"],
        "format": "pascal_voc",
        "access": "public_download",
        "homepage": "https://figshare.com/articles/dataset/21431547",
        "notes": "Primary road-damage source; includes India plus five other countries.",
    },
    "bdd100k": {
        "tasks": ["person", "car", "bus", "truck", "motorcycle", "bicycle", "traffic_sign", "tracking", "drivable_area"],
        "format": "bdd100k_json",
        "access": "manual_official_download",
        "homepage": "https://www.bdd100k.com/",
        "notes": "Use detection + MOT labels. Keep original license/terms with local copy.",
    },
    "mapillary_traffic_signs": {
        "tasks": ["traffic_sign"],
        "format": "mapillary",
        "access": "manual_license_gated",
        "homepage": "https://www.mapillary.com/dataset/trafficsign",
        "notes": "Use only under applicable Mapillary dataset terms; do not commit images.",
    },
    "ufpr_alpr": {
        "tasks": ["license_plate"],
        "format": "ufpr_txt",
        "access": "request_required_academic_noncommercial",
        "homepage": "https://web.inf.ufpr.br/vri/databases/ufpr-alpr/",
        "notes": "Requires author request; redistribution/modification/commercial use restricted.",
    },
}

TARGETS = {
    "road": ["pothole", "longitudinal_crack", "transverse_crack", "alligator_crack", "other_road_damage"],
    "infrastructure": ["waterlogging", "damaged_divider", "missing_divider", "damaged_zebra", "missing_zebra", "damaged_sign", "missing_sign"],
    "traffic": ["person", "car", "motorcycle", "bus", "truck", "bicycle", "auto_rickshaw", "emergency_vehicle"],
    "anpr": ["license_plate"],
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", action="store_true", help="Print local raw files and hashes")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    for name in TARGETS:
        root = DATASETS / name
        for split in ("train", "val", "test"):
            (root / "images" / split).mkdir(parents=True, exist_ok=True)
            (root / "labels" / split).mkdir(parents=True, exist_ok=True)

    manifest = {"sources": SOURCES, "target_taxonomy": TARGETS}
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.inventory:
        files = [{"path": str(p.relative_to(REPO_ROOT)), "bytes": p.stat().st_size, "sha256": sha256(p)}
                 for p in RAW.rglob("*") if p.is_file()]
        print(json.dumps({"raw_files": files}, indent=2))
    else:
        print(json.dumps(manifest, indent=2))
    print("\nDataset workspace prepared. Put licensed/downloaded archives under:", RAW)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
