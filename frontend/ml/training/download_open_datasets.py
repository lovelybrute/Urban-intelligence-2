"""Download only explicitly open/licensed dataset candidates used by the SIH pipeline.

Large/gated datasets (RDD2022, BDD100K, UVH-26, UFPR-ALPR, Mapillary) remain manual
so this script never bypasses click-through terms or access controls.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"datasets"/"_raw"

HF={
 "indian_license_plates":"thundarstrom/indian-license-plate-detection",
 "indian_road_driving":"thirdeyelabs/indian-road-dataset",
}

def hf_download(repo:str,dest:Path):
    dest.mkdir(parents=True,exist_ok=True)
    cmd=[sys.executable,"-m","huggingface_hub.commands.huggingface_cli","download",repo,
         "--repo-type","dataset","--local-dir",str(dest)]
    print("Running:"," ".join(cmd)); subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--datasets",nargs="+",choices=sorted(HF),default=["indian_license_plates"])
    ap.add_argument("--dry-run",action="store_true")
    a=ap.parse_args(); RAW.mkdir(parents=True,exist_ok=True)
    if a.dry_run:
        print(json.dumps({k:{"repo":HF[k],"destination":str(RAW/k)} for k in a.datasets},indent=2));return
    try: import huggingface_hub  # noqa:F401
    except ImportError:
        raise SystemExit("Install downloader first: python -m pip install huggingface_hub")
    for key in a.datasets: hf_download(HF[key],RAW/key)

if __name__=="__main__":main()
