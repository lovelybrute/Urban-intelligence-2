"""Locate a downloaded YOLO-format Indian plate dataset and import it into ANPR training."""
from __future__ import annotations
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"datasets"/"_raw"/"indian_license_plates"
OUT=ROOT/"datasets"/"license_plates"
IMPORT=Path(__file__).with_name("import_yolo_dataset.py")
VALIDATE=Path(__file__).with_name("validate_yolo_dataset.py")

def main():
    candidates=[p for p in RAW.rglob("*") if p.is_dir() and (p/"images").is_dir() and (p/"labels").is_dir()]
    if not candidates: raise SystemExit(f"No YOLO dataset found under {RAW}. Run download_open_datasets.py first.")
    src=min(candidates,key=lambda p:len(p.parts))
    subprocess.run([sys.executable,str(IMPORT),str(src),"--output",str(OUT),"--mapping",'{"0":0}',"--prefix","indplate"],check=True)
    subprocess.run([sys.executable,str(VALIDATE),str(OUT),"--classes","1"],check=True)
    print(f"ANPR dataset ready: {OUT}")
if __name__=="__main__":main()
