"""Train the custom infrastructure detector.

Usage from repository root:
python frontend/ml/training/train_infrastructure.py --epochs 80 --device 0
"""
import argparse
from pathlib import Path
from ultralytics import YOLO

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATA=HERE/"infrastructure.yaml"
OUT=ROOT/"frontend"/"ml"/"weights"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--epochs",type=int,default=80)
    p.add_argument("--imgsz",type=int,default=640)
    p.add_argument("--batch",type=int,default=8)
    p.add_argument("--device",default="0")
    p.add_argument("--base",default="yolo11n.pt")
    a=p.parse_args()
    model=YOLO(a.base)
    result=model.train(data=str(DATA),epochs=a.epochs,imgsz=a.imgsz,batch=a.batch,device=a.device,
                       project=str(ROOT/"frontend"/"ml"/"runs"),name="infrastructure")
    best=Path(result.save_dir)/"weights"/"best.pt"
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/"infrastructure.pt"
    target.write_bytes(best.read_bytes())
    print(f"Saved validated training output candidate to {target}")
    print("Evaluate validation metrics and representative test video before marking production-ready.")

if __name__=="__main__":
    main()
