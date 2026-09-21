"""One-command, fail-safe custom AI training pipeline for Urban Intelligence."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(args,required=True):
    print("\n>", " ".join(map(str,args)),flush=True)
    r=subprocess.run(list(map(str,args)))
    if required and r.returncode: raise SystemExit(r.returncode)
    return r.returncode

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--models",nargs="+",choices=["anpr","traffic","infrastructure"],default=["anpr"])
    ap.add_argument("--download-anpr",action="store_true")
    ap.add_argument("--batch",type=int,default=4);ap.add_argument("--imgsz",type=int,default=640);ap.add_argument("--workers",type=int,default=2)
    a=ap.parse_args()
    if "anpr" in a.models and a.download_anpr:
        run([sys.executable,HERE/"download_open_datasets.py","--datasets","indian_license_plates"])
        run([sys.executable,HERE/"prepare_anpr_dataset.py"])
    cmd=[sys.executable,HERE/"train_custom_models.py","--models",*a.models,"--batch",a.batch,"--imgsz",a.imgsz,"--workers",a.workers]
    run(cmd)
    print("\nTraining finished. Do not deploy new weights until held-out validation metrics are reviewed.")
if __name__=="__main__":main()
