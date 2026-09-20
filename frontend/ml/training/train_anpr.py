"""Train the custom number-plate localization detector.

This trains plate localization only. PaddleOCR performs character recognition.
Run from any directory:
python frontend/ml/training/train_anpr.py --epochs 60 --batch 4 --device 0
"""
import argparse
from pathlib import Path
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
ML_ROOT = HERE.parent
DATA = ML_ROOT / "configs" / "anpr_plate.yaml"
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
        name="anpr_plate",
        exist_ok=True,
        workers=2,
    )
    best = Path(result.save_dir) / "weights" / "best.pt"
    WEIGHTS.mkdir(parents=True, exist_ok=True)
    target = WEIGHTS / "anpr_plate.pt"
    target.write_bytes(best.read_bytes())
    print(f"Saved ANPR plate detector candidate to {target}")
    print("Validate plate localization metrics and OCR end-to-end accuracy before production use.")

if __name__ == "__main__":
    main()
