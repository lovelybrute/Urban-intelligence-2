"""Train the custom India traffic/person detector.

Run from any directory:
python frontend/ml/training/train_traffic_detector.py --epochs 60 --batch 4 --device 0
"""
import argparse
from pathlib import Path
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
ML_ROOT = HERE.parent
DATA = ML_ROOT / "configs" / "yolo_traffic.yaml"
RUNS = ML_ROOT / "runs"
WEIGHTS = ML_ROOT / "weights"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="0")
    p.add_argument("--base", default="yolo11n.pt")
    args = p.parse_args()

    model = YOLO(args.base)
    result = model.train(
        data=str(DATA),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        project=str(RUNS),
        name="traffic_india",
        exist_ok=True,
        workers=2,
    )
    best = Path(result.save_dir) / "weights" / "best.pt"
    WEIGHTS.mkdir(parents=True, exist_ok=True)
    target = WEIGHTS / "traffic_india.pt"
    target.write_bytes(best.read_bytes())
    print(f"Saved traffic model candidate to {target}")
    print("Validate mAP/precision/recall before marking this custom model production-ready.")

if __name__ == "__main__":
    main()
