"""Train YOLOv8n license plate detector for Indian ANPR localization.

Validates the YOLO dataset format before training and checks for CUDA availability.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = ML_ROOT / "weights"
DATASET_DIR = ML_ROOT / "datasets" / "license_plates"
CONFIG_FILE = ML_ROOT / "configs" / "anpr_plate.yaml"


def validate_dataset() -> tuple[bool, str]:
    validator = Path(__file__).with_name("validate_yolo_dataset.py")
    if not validator.is_file():
        return False, f"Validator not found at {validator}"
    res = subprocess.run(
        [sys.executable, str(validator), str(DATASET_DIR), "--classes", "1"],
        capture_output=True, text=True,
    )
    return res.returncode == 0, (res.stdout + res.stderr).strip()


def train(epochs: int = 60, batch: int = 8, imgsz: int = 640, allow_cpu: bool = False):
    import torch
    from ultralytics import YOLO

    has_cuda = torch.cuda.is_available()
    print(f"PyTorch version: {torch.__version__}, CUDA available: {has_cuda}")
    if has_cuda:
        print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
    elif not allow_cpu:
        print(
            "WARNING: No CUDA GPU detected. YOLO training on CPU is extremely slow.\n"
            "To force CPU training, pass --allow-cpu.\n"
            "Pre-trained MIT-licensed plate weights are already deployed to frontend/ml/weights/anpr_plate.pt."
        )
        return {"status": "skipped_no_cuda"}

    valid, msg = validate_dataset()
    if not valid:
        print(f"Dataset validation failed:\n{msg}")
        return {"status": "blocked_invalid_dataset", "error": msg}

    print(f"Dataset validated successfully. Training YOLOv8n on {CONFIG_FILE}...")
    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(CONFIG_FILE),
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        project=str(ML_ROOT / "runs" / "anpr"),
        name="plate_detector",
        device="0" if has_cuda else "cpu",
        workers=2,
    )
    
    # Check best model output
    best_pt = ML_ROOT / "runs" / "anpr" / "plate_detector" / "weights" / "best.pt"
    if best_pt.is_file():
        target_pt = WEIGHTS / "anpr_plate.pt"
        import shutil
        shutil.copy2(best_pt, target_pt)
        print(f"Copied best model to {target_pt}")
        
        # Export ONNX
        best_model = YOLO(str(target_pt))
        best_model.export(format="onnx", imgsz=imgsz)
        print(f"Exported to ONNX: {WEIGHTS / 'anpr_plate.onnx'}")

    return {"status": "completed", "results": str(results)}


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8n Plate Detector")
    parser.add_argument("--epochs", type=int, default=60, help="Training epochs")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--allow-cpu", action="store_true", help="Allow training on CPU")
    args = parser.parse_args()

    train(epochs=args.epochs, batch=args.batch, imgsz=args.imgsz, allow_cpu=args.allow_cpu)


if __name__ == "__main__":
    main()
