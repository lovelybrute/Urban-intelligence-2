"""Prepare and convert Indian traffic datasets into target 8-class YOLO format.

Taxonomy:
  0: car
  1: bus
  2: truck
  3: motorcycle
  4: auto_rickshaw
  5: bicycle
  6: emergency
  7: pedestrian

Supports importing from raw datasets (e.g. IDD / Indian Driving Dataset,
Indian Road Driving Dataset, UVH-26, or Roboflow exports).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets" / "_raw" / "indian_traffic"
OUT = ROOT / "datasets" / "traffic"
IMPORT = Path(__file__).with_name("import_yolo_dataset.py")
VALIDATE = Path(__file__).with_name("validate_yolo_dataset.py")

# Standard taxonomy mapping for common Indian driving dataset conventions
# e.g., IDD Detection dataset class indices -> target class indices
IDD_TO_TARGET = {
    # car -> 0
    "0": 0,
    # bus -> 1
    "1": 1,
    # truck -> 2
    "2": 2,
    # motorcycle / two-wheeler -> 3
    "3": 3,
    # auto_rickshaw -> 4
    "4": 4,
    # bicycle -> 5
    "5": 5,
    # ambulance / fire / police / emergency -> 6
    "6": 6,
    # pedestrian / person -> 7
    "7": 7,
}


def main():
    parser = argparse.ArgumentParser(description="Prepare Indian Traffic YOLO Dataset")
    parser.add_argument("--source", type=Path, default=RAW, help="Source directory with YOLO images and labels")
    parser.add_argument("--output", type=Path, default=OUT, help="Target traffic dataset directory")
    parser.add_argument("--mapping", default=json.dumps(IDD_TO_TARGET), help="JSON mapping from source class id to target class id")
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
        print("Supported sources: IDD (Indian Driving Dataset), UVH-26, or Indian Road Driving Dataset.")
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
            "traffic_in",
        ],
        check=True,
    )

    if not args.skip_validation:
        subprocess.run(
            [sys.executable, str(VALIDATE), str(args.output), "--classes", "8"],
            check=True,
        )

    print(f"Indian traffic dataset successfully prepared at: {args.output}")


if __name__ == "__main__":
    main()
