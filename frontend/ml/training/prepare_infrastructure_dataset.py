"""Prepare and convert infrastructure datasets into target 7-class YOLO format.

Taxonomy:
  0: waterlogging
  1: damaged_divider
  2: missing_divider
  3: damaged_zebra
  4: missing_zebra
  5: damaged_sign
  6: missing_sign

Note: Missing infrastructure (missing_divider, missing_zebra, missing_sign)
requires contextual annotations where expected assets are absent.
Damaged infrastructure can be sourced from road defect / traffic sign benchmarks.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets" / "_raw" / "infrastructure"
OUT = ROOT / "datasets" / "infrastructure"
IMPORT = Path(__file__).with_name("import_yolo_dataset.py")
VALIDATE = Path(__file__).with_name("validate_yolo_dataset.py")

DEFAULT_MAPPING = {
    "0": 0,  # waterlogging
    "1": 1,  # damaged_divider
    "2": 2,  # missing_divider
    "3": 3,  # damaged_zebra
    "4": 4,  # missing_zebra
    "5": 5,  # damaged_sign
    "6": 6,  # missing_sign
}


def main():
    parser = argparse.ArgumentParser(description="Prepare Infrastructure YOLO Dataset")
    parser.add_argument("--source", type=Path, default=RAW, help="Source directory with YOLO images and labels")
    parser.add_argument("--output", type=Path, default=OUT, help="Target infrastructure dataset directory")
    parser.add_argument("--mapping", default=json.dumps(DEFAULT_MAPPING), help="JSON mapping from source class id to target class id")
    parser.add_argument("--skip-validation", action="store_true", help="Skip fail-fast dataset validation")
    args = parser.parse_args()

    candidates = [
        p for p in args.source.rglob("*")
        if p.is_dir() and (p / "images").is_dir() and (p / "labels").is_dir()
    ]

    if not candidates:
        print(f"No YOLO dataset with images/ and labels/ found under {args.source}.")
        print(f"Scaffold structure is ready at {args.output}.")
        print("Please place the downloaded raw dataset in:")
        print(f"  {args.source}")
        print("Classes: waterlogging, damaged/missing dividers, damaged/missing zebra crossings, damaged/missing signs.")
        return

    src = min(candidates, key=lambda p: len(p.parts))
    print(f"Found dataset candidate at: {src}")

    # Run import
    subprocess.run(
        [
            sys.executable,
            str(IMPORT),
            str(src),
            "--output",
            str(args.output),
            "--mapping",
            args.mapping,
            "--prefix",
            "infra",
        ],
        check=True,
    )

    if not args.skip_validation:
        subprocess.run(
            [sys.executable, str(VALIDATE), str(args.output), "--classes", "7"],
            check=True,
        )

    print(f"Infrastructure dataset successfully prepared at: {args.output}")


if __name__ == "__main__":
    main()
