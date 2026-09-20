"""Train the custom road-defect detector.

Run from any directory:
python frontend/ml/training/train_defect_detector.py --epochs 50 --batch 4 --device 0
"""
import argparse
from pathlib import Path
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
ML_ROOT = HERE.parent
DATA = ML_ROOT / "configs" / "yolo_road_defect.yaml"
RUNS = ML_ROOT / "runs"
WEIGHTS = ML_ROOT / "weights"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="0")
    p.add_argument("--base", default="yolov8s.pt")
    args = p.parse_args()

    model = YOLO(args.base)
    result = model.train(
        data=str(DATA),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        project=str(RUNS),
        name="road_defect",
        exist_ok=True,
        workers=2,
        mosaic=1.0,
        mixup=0.1,
        fliplr=0.5,
    )
    best = Path(result.save_dir) / "weights" / "best.pt"
    WEIGHTS.mkdir(parents=True, exist_ok=True)
    target = WEIGHTS / "road_defect_best.pt"
    target.write_bytes(best.read_bytes())
    print(f"Saved road model candidate to {target}")
    print("Validate held-out metrics before replacing the deployed model.")

if __name__ == "__main__":
    main()
