"""Train every dataset-backed custom detector with RTX-2050-safe defaults.

The command stops before training when a labelled dataset is incomplete. Each
dataset must use YOLO image/label folders under frontend/ml/datasets.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[3]
ML_ROOT = SCRIPT.parents[1]
WEIGHTS = ML_ROOT / "weights"

JOBS = {
    "traffic": {
        "config": ML_ROOT / "configs" / "yolo_traffic.yaml",
        "dataset": ML_ROOT / "datasets" / "traffic",
        "base": "yolov8n.pt",
        "output": WEIGHTS / "traffic_india.pt",
        "epochs": 60,
    },
    "anpr": {
        "config": ML_ROOT / "configs" / "anpr_plate.yaml",
        "dataset": ML_ROOT / "datasets" / "license_plates",
        "base": "yolov8n.pt",
        "output": WEIGHTS / "anpr_plate.pt",
        "epochs": 60,
    },
    "infrastructure": {
        "config": ML_ROOT / "configs" / "yolo_infrastructure.yaml",
        "dataset": ML_ROOT / "datasets" / "infrastructure",
        "base": "yolov8s.pt",
        "output": WEIGHTS / "infrastructure.pt",
        "epochs": 70,
    },
}


def dataset_counts(root: Path) -> tuple[int, int, int, int]:
    suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    train_images = sum(1 for p in (root / "images" / "train").glob("**/*") if p.suffix.lower() in suffixes)
    val_images = sum(1 for p in (root / "images" / "val").glob("**/*") if p.suffix.lower() in suffixes)
    train_labels = sum(1 for _ in (root / "labels" / "train").glob("**/*.txt"))
    val_labels = sum(1 for _ in (root / "labels" / "val").glob("**/*.txt"))
    return train_images, val_images, train_labels, val_labels


def validate_dataset(name: str, job: dict) -> tuple[bool, str]:
    class_counts = {"traffic": 8, "anpr": 1, "infrastructure": 7}
    validator = SCRIPT.parent / "validate_yolo_dataset.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(job["dataset"]), "--classes", str(class_counts[name])],
        capture_output=True, text=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def train_job(name: str, job: dict, batch: int, imgsz: int, workers: int) -> dict:
    valid, validation_report = validate_dataset(name, job)
    if not valid:
        return {"status": "blocked_invalid_dataset", "validation": validation_report}
    counts = dataset_counts(job["dataset"])
    if not all(counts):
        return {
            "status": "blocked_missing_dataset",
            "dataset": str(job["dataset"].relative_to(REPO_ROOT)),
            "train_images": counts[0],
            "val_images": counts[1],
            "train_labels": counts[2],
            "val_labels": counts[3],
        }

    from ultralytics import YOLO
    import torch
    import yaml

    if not torch.cuda.is_available():
        return {"status": "blocked_no_cuda", "message": "A CUDA GPU is required for this training command."}

    project = ML_ROOT / "runs" / name
    project.mkdir(parents=True, exist_ok=True)
    with job["config"].open(encoding="utf-8") as stream:
        dataset_config = yaml.safe_load(stream)
    dataset_config["path"] = str(job["dataset"].resolve())
    resolved_config = project / "dataset.resolved.yaml"
    with resolved_config.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(dataset_config, stream, sort_keys=False)
    model = YOLO(job["base"])
    result = model.train(
        data=str(resolved_config),
        epochs=job["epochs"],
        imgsz=imgsz,
        batch=batch,
        workers=workers,
        device=0,
        project=str(project),
        name="train",
        exist_ok=True,
        patience=12,
        amp=True,
    )
    best = Path(result.save_dir) / "weights" / "best.pt"
    if not best.is_file():
        return {"status": "failed", "message": f"Training ended without {best}"}
    WEIGHTS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, job["output"])
    return {
        "status": "trained_unvalidated",
        "weights": str(job["output"].relative_to(REPO_ROOT)),
        "run": str(Path(result.save_dir).relative_to(REPO_ROOT)),
        "note": "Evaluate on an unseen test split before reporting accuracy.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", choices=sorted(JOBS), default=sorted(JOBS))
    parser.add_argument("--batch", type=int, default=4, help="RTX 2050 4 GB safe default")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    results = {
        name: train_job(name, JOBS[name], args.batch, args.imgsz, args.workers)
        for name in args.models
    }
    print(json.dumps(results, indent=2))
    return 0 if all(item["status"].startswith("trained") for item in results.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
