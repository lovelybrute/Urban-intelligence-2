"""Fail-fast validation for YOLO detection datasets before expensive training."""
from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path
EXT={".jpg",".jpeg",".png",".webp"}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("root",type=Path);ap.add_argument("--classes",type=int,required=True);a=ap.parse_args()
    report={}; bad=[]; counts=Counter()
    for split in ("train","val","test"):
        imgs={p.stem:p for p in (a.root/"images"/split).rglob("*") if p.suffix.lower() in EXT} if (a.root/"images"/split).exists() else {}
        labs={p.stem:p for p in (a.root/"labels"/split).rglob("*.txt")} if (a.root/"labels"/split).exists() else {}
        for stem,p in labs.items():
            if stem not in imgs: bad.append(f"orphan label: {p}")
            for n,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
                q=line.split()
                try:
                    cls=int(q[0]); vals=list(map(float,q[1:5]))
                    if len(q)<5 or not 0<=cls<a.classes or any(v<0 or v>1 for v in vals): raise ValueError
                    counts[cls]+=1
                except Exception: bad.append(f"invalid: {p}:{n}: {line}")
        report[split]={"images":len(imgs),"labels":len(labs),"images_without_label":sum(s not in labs for s in imgs)}
    report["boxes_per_class"]={str(k):v for k,v in sorted(counts.items())};report["errors"]=bad[:100]
    print(json.dumps(report,indent=2))
    raise SystemExit(2 if bad else 0)
if __name__=="__main__":main()
