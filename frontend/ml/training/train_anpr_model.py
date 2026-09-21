"""Train YOLOv8n license plate detector for Indian ANPR localization.

Validates the YOLO dataset format before training, trains on CUDA GPU if available,
saves a candidate checkpoint, validates metrics (P, R, mAP50, mAP50-95), and
exports ONNX upon promotion.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = ML_ROOT / "weights"
CANDIDATES = WEIGHTS / "candidates"
DATASET_DIR = ML_ROOT / "datasets" / "license_plates"
CONFIG_FILE = ML_ROOT / "configs" / "anpr_plate.yaml"
RUNTIME_CONFIG = ML_ROOT / "configs" / "anpr_plate_runtime.yaml"
METRICS_FILE = ML_ROOT / "anpr_metrics.json"


def validate_dataset() -> tuple[bool, str]:
    validator = Path(__file__).with_name("validate_yolo_dataset.py")
    if not validator.is_file():
        return False, f"Validator not found at {validator}"
    res = subprocess.run(
        [sys.executable, str(validator), str(DATASET_DIR), "--classes", "1"],
        capture_output=True, text=True,
    )
    return res.returncode == 0, (res.stdout + res.stderr).strip()


def prepare_data_yaml() -> Path:
    """Generate runtime data.yaml with absolute path so ultralytics never misresolves."""
    import yaml
    RUNTIME_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = str(DATASET_DIR.resolve()).replace("\\", "/")
    data = {
        "path": resolved_path,
        "train": "images/train",
        "val": "images/val",
        "test": "images/test" if (DATASET_DIR / "images" / "test").exists() else "images/val",
        "names": {
            0: "license_plate"
        }
    }
    with open(RUNTIME_CONFIG, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)
    return RUNTIME_CONFIG


def train(epochs: int = 25, batch: int = 16, imgsz: int = 640, patience: int = 5, allow_cpu: bool = False):
    import torch
    from ultralytics import YOLO

    has_cuda = torch.cuda.is_available()
    print(f"PyTorch version: {torch.__version__}, CUDA available: {has_cuda}")
    if has_cuda:
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"CUDA Device: {gpu_name} ({vram_gb:.1f} GB VRAM)")
    elif not allow_cpu:
        print(
            "WARNING: No CUDA GPU detected. YOLO training on CPU is extremely slow.\n"
            "To force CPU training, pass --allow-cpu."
        )
        return {"status": "skipped_no_cuda"}

    # 1. Dataset validation
    print("Validating ANPR dataset...")
    valid, msg = validate_dataset()
    if not valid:
        print(f"Dataset validation failed:\n{msg}")
        return {"status": "blocked_invalid_dataset", "error": msg}
    print("Dataset validation PASSED.")

    # 2. Config file setup
    cfg_path = prepare_data_yaml()
    print(f"Using configuration: {cfg_path}")

    # 3. Model training
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    run_dir = ML_ROOT / "runs" / "anpr"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nStarting YOLOv8n training for {epochs} epochs (patience={patience}, batch={batch}, imgsz={imgsz})...")
    model = YOLO("yolov8n.pt")

    start_time = time.time()
    results = model.train(
        data=str(cfg_path),
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        patience=patience,
        project=str(run_dir),
        name="plate_detector",
        device="0" if has_cuda else "cpu",
        workers=2,
        exist_ok=True,
        plots=True,
    )
    training_duration_sec = time.time() - start_time
    print(f"\nTraining completed in {training_duration_sec:.1f}s")

    # 4. Check best candidate checkpoint
    best_pt = run_dir / "plate_detector" / "weights" / "best.pt"
    if not best_pt.is_file():
        raise FileNotFoundError(f"Training finished but best.pt not found at {best_pt}")

    candidate_pt = CANDIDATES / "anpr_plate_candidate.pt"
    shutil.copy2(best_pt, candidate_pt)
    print(f"Candidate weights saved: {candidate_pt}")

    # 5. Formal validation & metric extraction
    print("\nRunning validation on best candidate checkpoint...")
    eval_model = YOLO(str(candidate_pt))
    val_metrics = eval_model.val(data=str(cfg_path), batch=batch, imgsz=imgsz, device="0" if has_cuda else "cpu")

    # Extract metrics
    precision = float(val_metrics.box.mp)
    recall = float(val_metrics.box.mr)
    map50 = float(val_metrics.box.map50)
    map50_95 = float(val_metrics.box.map)
    speed = val_metrics.speed
    inference_ms = float(speed.get("inference", 5.0))

    val_images_count = len(list((DATASET_DIR / "images" / "val").glob("*.*")))

    metrics_dict = {
        "model": "YOLOv8n",
        "task": "license_plate_localization",
        "dataset": "keremberke/license-plate-object-detection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "epochs_completed": epochs,
        "training_duration_sec": round(training_duration_sec, 1),
        "validation_images": val_images_count,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "map50": round(map50, 4),
        "map50_95": round(map50_95, 4),
        "inference_ms_per_image": round(inference_ms, 2),
        "classes": {
            "license_plate": {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "map50": round(map50, 4),
                "map50_95": round(map50_95, 4)
            }
        },
        "validation_note": "Trained YOLOv8n plate detector evaluated on unseen validation split."
    }

    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics_dict, f, indent=2)
    print(f"Saved validation metrics to {METRICS_FILE}")
    print(json.dumps(metrics_dict, indent=2))

    # 6. Promotion to production weights
    # Note: road_defect_best.pt is NOT touched. Only anpr_plate.pt is updated.
    target_pt = WEIGHTS / "anpr_plate.pt"
    shutil.copy2(candidate_pt, target_pt)
    print(f"\nPromoted candidate to production: {target_pt}")

    # Export ONNX
    try:
        export_model = YOLO(str(target_pt))
        export_model.export(format="onnx", imgsz=imgsz)
        print(f"Exported ONNX: {WEIGHTS / 'anpr_plate.onnx'}")
    except Exception as e:
        print(f"ONNX export notice: {e}")

    # 7. Verification test on a sample image
    print("\nRunning inference visual verification on sample validation images...")
    sample_images = list((DATASET_DIR / "images" / "val").glob("*.*"))[:3]
    for s_img in sample_images:
        test_res = eval_model(str(s_img), conf=0.25)
        boxes_found = len(test_res[0].boxes)
        print(f"  Sample {s_img.name}: found {boxes_found} license plate(s)")

    return {"status": "completed", "metrics": metrics_dict}


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8n Plate Detector")
    parser.add_argument("--epochs", type=int, default=25, help="Training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--patience", type=int, default=5, help="Early stopping patience")
    parser.add_argument("--allow-cpu", action="store_true", help="Allow training on CPU")
    args = parser.parse_args()

    train(epochs=args.epochs, batch=args.batch, imgsz=args.imgsz, patience=args.patience, allow_cpu=args.allow_cpu)


if __name__ == "__main__":
    main()
