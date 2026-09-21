"""Import a reviewed YOLO dataset into an Urban Intelligence target dataset.

Designed for infrastructure and ANPR datasets whose licenses/download mechanisms
vary. Class remapping is explicit so incompatible labels are never silently merged.
"""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path

EXT={".jpg",".jpeg",".png",".webp"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--mapping",required=True,help='JSON source-id to target-id, e.g. {"0":0,"3":6}')
    ap.add_argument("--prefix",default="import")
    args=ap.parse_args(); mapping={int(k):int(v) for k,v in json.loads(args.mapping).items()}
    totals={"images":0,"boxes":0,"skipped_boxes":0}
    for split in ("train","val","test"):
        si=args.source/"images"/split; sl=args.source/"labels"/split
        oi=args.output/"images"/split; ol=args.output/"labels"/split
        oi.mkdir(parents=True,exist_ok=True); ol.mkdir(parents=True,exist_ok=True)
        if not si.exists(): continue
        for img in (p for p in si.rglob("*") if p.suffix.lower() in EXT):
            rel=img.relative_to(si); src_label=(sl/rel).with_suffix(".txt")
            name=f"{args.prefix}_{'_'.join(rel.with_suffix('').parts)}"
            rows=[]
            if src_label.is_file():
                for line in src_label.read_text(encoding="utf-8").splitlines():
                    parts=line.split()
                    if len(parts)<5: continue
                    source_id=int(parts[0])
                    if source_id not in mapping:
                        totals["skipped_boxes"]+=1; continue
                    parts[0]=str(mapping[source_id]); rows.append(" ".join(parts)); totals["boxes"]+=1
            shutil.copy2(img,oi/f"{name}{img.suffix.lower()}")
            (ol/f"{name}.txt").write_text("\n".join(rows)+("\n" if rows else ""),encoding="utf-8")
            totals["images"]+=1
    print(json.dumps(totals,indent=2))
if __name__=="__main__": main()
