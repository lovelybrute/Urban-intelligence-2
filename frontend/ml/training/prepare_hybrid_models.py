"""Prepare the honest hybrid AI stack used by the SIH prototype.

This does not pretend pretrained weights were custom-trained. It verifies the
trained road checkpoint, downloads Ultralytics' COCO traffic/person checkpoint,
checks OCR availability, and writes a machine-readable readiness manifest.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[3]
ML_ROOT = SCRIPT.parents[1]
WEIGHTS = ML_ROOT / "weights"
MANIFEST = ML_ROOT / "model_manifest.json"


def prepare_traffic(base_model: str) -> dict:
    custom = WEIGHTS / "traffic_india.pt"
    if custom.is_file():
        return {
            "status": "trained_unvalidated",
            "path": str(custom.relative_to(REPO_ROOT)),
            "scope": ["person", "car", "motorcycle", "bus", "truck", "bicycle", "auto_rickshaw", "emergency"],
            "note": "Custom checkpoint exists; evaluate on an unseen test split before reporting accuracy.",
        }
    target = WEIGHTS / "traffic_coco.pt"
    if target.is_file():
        return {
            "status": "ready_pretrained",
            "path": str(target.relative_to(REPO_ROOT)),
            "scope": ["person", "car", "motorcycle", "bus", "truck", "bicycle"],
            "note": "COCO-pretrained weights; Indian auto-rickshaw and emergency-vehicle accuracy is not validated.",
        }

    from ultralytics import YOLO

    model = YOLO(base_model)
    source = Path(model.ckpt_path).resolve()
    if not source.is_file():
        raise RuntimeError(f"Ultralytics did not provide checkpoint: {source}")
    shutil.copy2(source, target)
    return {
        "status": "ready_pretrained",
        "path": str(target.relative_to(REPO_ROOT)),
        "scope": ["person", "car", "motorcycle", "bus", "truck", "bicycle"],
        "note": "COCO-pretrained weights; Indian auto-rickshaw and emergency-vehicle accuracy is not validated.",
    }


def check_ocr() -> dict:
    try:
        import pytesseract
        version = str(pytesseract.get_tesseract_version())
        return {
            "status": "ready_pretrained_ocr",
            "engine": "Tesseract",
            "version": version,
            "note": "OCR is available; plate localization still needs a trained detector or a reviewed vehicle crop.",
        }
    except Exception as exc:
        return {
            "status": "blocked",
            "engine": "Tesseract",
            "reason": str(exc),
            "action": "Install the Tesseract Windows application and ensure tesseract.exe is on PATH.",
        }


def custom_checkpoint(filename: str, scope: list[str]) -> dict:
    path = WEIGHTS / filename
    return {
        "status": "trained_unvalidated" if path.is_file() else "blocked_missing_weights",
        "path": str(path.relative_to(REPO_ROOT)),
        "scope": scope,
        "note": "Evaluate on an unseen test split before reporting accuracy." if path.is_file() else "Run custom training after adding a labelled YOLO dataset.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traffic-base", default="yolov8n.pt")
    args = parser.parse_args()
    WEIGHTS.mkdir(parents=True, exist_ok=True)

    road = WEIGHTS / "road_defect_best.pt"
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "hybrid",
        "road_defect": {
            "status": "trained" if road.is_file() else "blocked",
            "path": str(road.relative_to(REPO_ROOT)),
            "metrics": str((ML_ROOT / "road_defect_metrics.json").relative_to(REPO_ROOT)),
            "note": "50-epoch RDD2022 checkpoint; field validation remains required.",
        },
        "traffic_and_people": prepare_traffic(args.traffic_base),
        "number_plate_localizer": custom_checkpoint("anpr_plate.pt", ["license_plate"]),
        "number_plate_ocr": check_ocr(),
        "infrastructure": custom_checkpoint(
            "infrastructure.pt",
            ["waterlogging", "damaged_divider", "missing_divider", "damaged_zebra", "missing_zebra", "damaged_sign", "missing_sign"],
        ),
        "incident_detection": {
            "status": "rule_based",
            "depends_on": ["traffic_and_people", "number_plate_ocr"],
            "note": "Wrong-way/rash-driving/hit-and-run are temporal tracking rules, not single-frame YOLO classes.",
        },
    }
    untrained = []
    if manifest["traffic_and_people"]["status"] != "trained_unvalidated":
        untrained.extend(["auto_rickshaw", "emergency_vehicle"])
    if manifest["infrastructure"]["status"] != "trained_unvalidated":
        untrained.extend(["waterlogging", "missing_divider", "missing_zebra", "damaged_or_missing_sign"])
    if manifest["number_plate_localizer"]["status"] != "trained_unvalidated":
        untrained.append("license_plate_localizer")
    manifest["untrained_custom_scopes"] = untrained
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if road.is_file() else 2


if __name__ == "__main__":
    raise SystemExit(main())
